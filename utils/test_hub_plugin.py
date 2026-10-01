"""Плагин pytest для раннера test_hub: разметка вывода по тестам/шагам и кадры UI-шагов.

Активируется только когда заданы все три env: TH_URL, TH_RUN_ID, TH_RUN_TOKEN — их передаёт
раннер test_hub при запуске прогона. Без них модуль не делает ничего (никаких print, сетевых
вызовов и патча allure.step), обычные локальные/стендовые прогоны не меняются.
"""
import base64
import os
import sys
import threading
import time
from functools import wraps

import allure
import pytest
import requests
from allure_commons._allure import StepContext as _AllureStepContext
from allure_commons.utils import func_parameters, represent

from utils.logger import logger

TH_URL = os.environ.get("TH_URL")
TH_RUN_ID = os.environ.get("TH_RUN_ID")
TH_RUN_TOKEN = os.environ.get("TH_RUN_TOKEN")

ENABLED = bool(TH_URL and TH_RUN_ID and TH_RUN_TOKEN)


def _env_flag(name, default):
    """Булев env-флаг с default при отсутствии/пустой переменной: "0"/"false"/"no"
    (без учёта регистра) — явное выключение, всё остальное — включение."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() not in ("0", "false", "no")


def _env_int(name, default):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


MAX_FRAMES_PER_TEST = 40
FRAME_MAX_WIDTH = 1280
FRAME_HTTP_TIMEOUT = 3

PAGE_FIXTURE_NAMES = ("page", "admin_page", "user_page")

# Живая трансляция (screencast) по умолчанию выключена: раннер test_hub явно включает её
# через TH_LIVE=1 только для прогонов с флагом «Эфир» (разметка [TH] и кадры шагов работают
# независимо от неё в любом случае).
LIVE_ENABLED = ENABLED and _env_flag("TH_LIVE", False)
TH_LIVE_FPS = _env_int("TH_LIVE_FPS", 3)

MAX_LIVE_ERRORS = 20
LIVE_HTTP_TIMEOUT = 2
LIVE_MAX_WIDTH = 960
LIVE_MAX_HEIGHT = 600

# Состояние текущего теста (один процесс = один тест выполняется в один момент времени,
# в т.ч. под pytest-xdist — там на процесс-воркер приходится свой импорт этого модуля).
_state = {
    "item": None,
    "step_count": 0,
    "frame_count": 0,
    "frame_limit_logged": False,
    "end_emitted": False,
    "live": None,
    "live_current_step": "",
    "live_error_count": 0,
    "live_disabled": False,
}

_original_step = allure.step
_step_patched = False


class _InstrumentedStepContext:
    """Прозрачная обёртка над allure_commons.StepContext: делегирует ей весь реальный
    allure-функционал (тело шага, исключения, репортинг), дополнительно печатая
    `[TH] step ...` и снимая кадр UI-страницы в момент входа в шаг."""

    def __init__(self, title, params):
        self.title = title
        self.params = params
        self._inner = _AllureStepContext(title, params)

    def __enter__(self):
        result = self._inner.__enter__()
        _on_step_start(self.title)
        return result

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._inner.__exit__(exc_type, exc_val, exc_tb)

    def __call__(self, func):
        @wraps(func)
        def impl(*args, **kwargs):
            __tracebackhide__ = True
            params = func_parameters(func, *args, **kwargs)
            call_args = [represent(x) for x in args]
            with _InstrumentedStepContext(self.title.format(*call_args, **params), params):
                return func(*args, **kwargs)

        return impl


def _instrumented_step(title):
    """Замена allure.step — тот же контракт (context manager и декоратор), см. allure_commons._allure.step."""
    if callable(title):
        return _InstrumentedStepContext(title.__name__, {})(title)
    return _InstrumentedStepContext(title, {})


def _patch_allure_step():
    global _step_patched
    if not _step_patched:
        allure.step = _instrumented_step
        _step_patched = True


def _unpatch_allure_step():
    global _step_patched
    if _step_patched:
        allure.step = _original_step
        _step_patched = False


def _th_print(line):
    """Печатает служебную строку мимо capture pytest (иначе она склеивается с выводом
    pytest -v в одну строку или вовсе теряется внутри перехваченного stdout теста).
    Ведущий перевод строки отделяет её от того, что уже написано в sys.__stdout__."""
    sys.__stdout__.write(f"\n{line}\n")
    sys.__stdout__.flush()


def _on_step_start(title):
    item = _state.get("item")
    nodeid = item.nodeid if item is not None else "<unknown>"
    _state["step_count"] += 1
    step_no = _state["step_count"]
    _th_print(f"[TH] step {nodeid} {step_no} {title}")
    if item is not None:
        _maybe_capture_frame(item, nodeid, step_no)
        if LIVE_ENABLED:
            _state["live_current_step"] = title
            _sync_live_session(item)


def _find_active_page(item):
    funcargs = getattr(item, "funcargs", None) or {}
    for name in PAGE_FIXTURE_NAMES:
        page = funcargs.get(name)
        if page is not None:
            return page
    return None


def _screenshot(page):
    try:
        if page.is_closed():
            return None
    except Exception:  # noqa: BLE001 — страница могла быть в непредсказуемом состоянии
        return None

    try:
        viewport = page.viewport_size or {"width": FRAME_MAX_WIDTH, "height": 720}
        width = min(FRAME_MAX_WIDTH, viewport["width"] or FRAME_MAX_WIDTH)
        height = viewport["height"] or 720
        return page.screenshot(type="png", clip={"x": 0, "y": 0, "width": width, "height": height})
    except Exception as exc:  # noqa: BLE001 — кадр не должен ронять тест
        logger.info(f"[test_hub] не удалось сделать скриншот шага: {exc}")
        return None


def _send_frame(nodeid, step_no, png_bytes):
    try:
        requests.post(
            f"{TH_URL}/api/runs/{TH_RUN_ID}/frames",
            data={"nodeid": nodeid, "step": step_no},
            files={"file": (f"step_{step_no}.png", png_bytes, "image/png")},
            headers={"Authorization": f"Bearer {TH_RUN_TOKEN}"},
            timeout=FRAME_HTTP_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001 — сетевая ошибка не должна ронять тест
        logger.info(f"[test_hub] не удалось отправить кадр {nodeid} шаг {step_no}: {exc}")


def _maybe_capture_frame(item, nodeid, step_no):
    if _state["frame_count"] >= MAX_FRAMES_PER_TEST:
        if not _state["frame_limit_logged"]:
            logger.info(
                f"[test_hub] лимит кадров ({MAX_FRAMES_PER_TEST}) достигнут для {nodeid}, "
                "дальнейшие кадры пропущены"
            )
            _state["frame_limit_logged"] = True
        return

    page = _find_active_page(item)
    if page is None:
        return

    png_bytes = _screenshot(page)
    if png_bytes is None:
        return

    _state["frame_count"] += 1
    try:
        allure.attach(png_bytes, name=f"step {step_no}", attachment_type=allure.attachment_type.PNG)
    except Exception as exc:  # noqa: BLE001 — приложение к отчёту не должно ронять тест
        logger.info(f"[test_hub] не удалось приложить кадр к allure: {exc}")

    _send_frame(nodeid, step_no, png_bytes)


def _sync_live_session(item):
    """Вызывается на каждый _on_step_start: открывает screencast на активной странице,
    если его ещё нет, и переоткрывает его, если активная страница сменилась (новый
    контекст для гостя/попап). Ничего не делает, если трансляция уже отключена для
    этого теста после серии сетевых ошибок (см. _live_sender_loop)."""
    if _state.get("live_disabled"):
        return
    try:
        page = _find_active_page(item)
        if page is None:
            return

        current = _state.get("live")
        if current is not None:
            if current.get("page") is page:
                return
            _stop_live_session(current)
            _state["live"] = None

        _state["live"] = _start_live_session(item.nodeid, page)
    except Exception as exc:  # noqa: BLE001 — трансляция не должна ронять тест
        logger.info(f"[test_hub] ошибка синхронизации трансляции: {exc}")


def _start_live_session(nodeid, page):
    try:
        if page.is_closed():
            return None
    except Exception:  # noqa: BLE001 — страница могла быть в непредсказуемом состоянии
        return None

    try:
        session = page.context.new_cdp_session(page)
    except Exception as exc:  # noqa: BLE001 — страница могла закрыться/не поддержать CDP
        logger.info(f"[test_hub] не удалось открыть CDP-сессию трансляции для {nodeid}: {exc}")
        return None

    slot = {"frame": None, "lock": threading.Lock()}

    def _on_frame(params):
        try:
            session.send("Page.screencastFrameAck", {"sessionId": params.get("sessionId")})
        except Exception:  # noqa: BLE001 — без ack поток встанет, но тест падать не должен
            pass
        try:
            data = params.get("data")
            if data:
                frame_bytes = base64.b64decode(data)
                with slot["lock"]:
                    slot["frame"] = frame_bytes
        except Exception as exc:  # noqa: BLE001
            logger.info(f"[test_hub] ошибка обработки кадра трансляции для {nodeid}: {exc}")

    try:
        session.on("Page.screencastFrame", _on_frame)
        session.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": 50,
                "maxWidth": LIVE_MAX_WIDTH,
                "maxHeight": LIVE_MAX_HEIGHT,
                "everyNthFrame": 2,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.info(f"[test_hub] не удалось запустить screencast для {nodeid}: {exc}")
        try:
            session.detach()
        except Exception:  # noqa: BLE001
            pass
        return None

    stop_event = threading.Event()
    thread = threading.Thread(target=_live_sender_loop, args=(nodeid, slot, stop_event), daemon=True)
    thread.start()

    return {"page": page, "session": session, "slot": slot, "stop_event": stop_event, "thread": thread}


def _live_sender_loop(nodeid, slot, stop_event):
    interval = 1.0 / TH_LIVE_FPS if TH_LIVE_FPS > 0 else 0.0
    last_sent = None
    while not stop_event.is_set():
        loop_start = time.time()
        with slot["lock"]:
            frame = slot["frame"]

        if frame is not None and frame is not last_sent:
            last_sent = frame
            step_title = _state.get("live_current_step") or ""
            if _send_live_frame(nodeid, step_title, frame):
                _state["live_error_count"] = 0
            else:
                _state["live_error_count"] = _state.get("live_error_count", 0) + 1
                if _state["live_error_count"] >= MAX_LIVE_ERRORS:
                    logger.info(
                        f"[test_hub] трансляция для {nodeid} отключена после "
                        f"{_state['live_error_count']} сетевых ошибок подряд"
                    )
                    _state["live_disabled"] = True
                    stop_event.set()
                    break

        elapsed = time.time() - loop_start
        stop_event.wait(max(0.0, interval - elapsed) if interval else 0.05)


def _send_live_frame(nodeid, step_title, jpeg_bytes):
    try:
        requests.post(
            f"{TH_URL}/api/runs/{TH_RUN_ID}/live",
            data={"nodeid": nodeid, "ts": time.time(), "step": step_title},
            files={"file": ("live.jpg", jpeg_bytes, "image/jpeg")},
            headers={"Authorization": f"Bearer {TH_RUN_TOKEN}"},
            timeout=LIVE_HTTP_TIMEOUT,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — сетевая ошибка не должна ронять тест
        logger.info(f"[test_hub] не удалось отправить живой кадр {nodeid}: {exc}")
        return False


def _stop_live_session(session_state):
    if not session_state:
        return

    try:
        session_state["stop_event"].set()
    except Exception:  # noqa: BLE001
        pass

    thread = session_state.get("thread")
    if thread is not None:
        try:
            thread.join(timeout=2)
        except Exception:  # noqa: BLE001
            pass

    session = session_state.get("session")
    if session is not None:
        try:
            session.send("Page.stopScreencast")
        except Exception:  # noqa: BLE001
            pass
        try:
            session.detach()
        except Exception:  # noqa: BLE001
            pass


def _classify_report(report):
    """passed|failed|skipped|xfailed для текущей фазы отчёта, либо None, если по этой фазе
    итог теста ещё не определён (например, setup прошёл успешно — ждём фазу call)."""
    wasxfail = hasattr(report, "wasxfail")

    if report.when == "setup":
        if report.failed:
            return "failed"
        if report.skipped:
            return "xfailed" if wasxfail else "skipped"
        return None

    if report.when == "call":
        if report.failed:
            return "failed"
        if report.skipped:
            return "xfailed" if wasxfail else "skipped"
        if report.passed:
            return "passed"
        return None

    if report.when == "teardown":
        return "failed" if report.failed else None

    return None


def pytest_configure(config):
    if not ENABLED:
        return
    _patch_allure_step()
    config.add_cleanup(_unpatch_allure_step)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if not ENABLED:
        yield
        return

    _state["item"] = item
    _state["step_count"] = 0
    _state["frame_count"] = 0
    _state["frame_limit_logged"] = False
    _state["end_emitted"] = False
    _state["live"] = None
    _state["live_current_step"] = ""
    _state["live_error_count"] = 0
    _state["live_disabled"] = False
    try:
        yield
    finally:
        _stop_live_session(_state.get("live"))
        _state["live"] = None
        _state["item"] = None


def pytest_runtest_logstart(nodeid, location):
    if not ENABLED:
        return
    _th_print(f"[TH] start {nodeid}")


def pytest_runtest_logreport(report):
    if not ENABLED:
        return
    if _state["end_emitted"]:
        return
    outcome = _classify_report(report)
    if outcome is None:
        return
    _state["end_emitted"] = True
    _th_print(f"[TH] end {report.nodeid} {outcome}")
