"""Плагин pytest для раннера test_hub: разметка вывода по тестам/шагам и кадры UI-шагов.

Активируется только когда заданы все три env: TH_URL, TH_RUN_ID, TH_RUN_TOKEN — их передаёт
раннер test_hub при запуске прогона. Без них модуль не делает ничего (никаких print, сетевых
вызовов и патча allure.step), обычные локальные/стендовые прогоны не меняются.
"""
import os
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

MAX_FRAMES_PER_TEST = 40
FRAME_MAX_WIDTH = 1280
FRAME_HTTP_TIMEOUT = 3

PAGE_FIXTURE_NAMES = ("page", "admin_page", "user_page")

# Состояние текущего теста (один процесс = один тест выполняется в один момент времени,
# в т.ч. под pytest-xdist — там на процесс-воркер приходится свой импорт этого модуля).
_state = {
    "item": None,
    "step_count": 0,
    "frame_count": 0,
    "frame_limit_logged": False,
    "end_emitted": False,
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


def _on_step_start(title):
    item = _state.get("item")
    nodeid = item.nodeid if item is not None else "<unknown>"
    _state["step_count"] += 1
    step_no = _state["step_count"]
    print(f"[TH] step {nodeid} {step_no} {title}", flush=True)
    if item is not None:
        _maybe_capture_frame(item, nodeid, step_no)


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
    try:
        yield
    finally:
        _state["item"] = None


def pytest_runtest_logstart(nodeid, location):
    if not ENABLED:
        return
    print(f"[TH] start {nodeid}", flush=True)


def pytest_runtest_logreport(report):
    if not ENABLED:
        return
    if _state["end_emitted"]:
        return
    outcome = _classify_report(report)
    if outcome is None:
        return
    _state["end_emitted"] = True
    print(f"[TH] end {report.nodeid} {outcome}", flush=True)
