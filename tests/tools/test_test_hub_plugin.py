"""Юнит-тесты utils/test_hub_plugin.py: без стенда, без сети наружу и без --env.

Модуль вычисляет TH_URL/TH_RUN_ID/TH_RUN_TOKEN/ENABLED один раз при импорте, поэтому
здесь используется importlib.reload после monkeypatch.setenv/delenv — так же, как это
сделал бы раннер test_hub, выставив переменные окружения до старта pytest.

conftest.py уже подключает этот же модуль как реальный плагин текущей pytest-сессии
(pytest_plugins = ["utils.test_hub_plugin"]) — то есть module.__dict__ здесь тот же
объект, на который смотрят реальные хуки pytest для этого самого тестового файла. Если
оставить ENABLED=True до конца тела теста, реальный pytest_runtest_logreport увидит
ENABLED=True при обработке "call"-отчёта уже НАШЕГО теста и напечатает лишний "[TH] end"
в реальный вывод сессии (безобидно, но шумно). Поэтому plugin_env — контекстный менеджер:
он гарантированно выключает плагин (env + reload) до того, как тело теста вернёт
управление pytest, а не только в отложенном teardown фикстуры.
"""
import base64
import contextlib
import email
import importlib
import io
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import allure
import pytest

import utils.test_hub_plugin as th_plugin

pytestmark = pytest.mark.tools

# 1x1 прозрачный PNG — минимальные, но валидные PNG-байты (RFC 2083 сигнатура + IHDR/IDAT/IEND).
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


# ---------- инфраструктура: reload плагина под нужный TH_* env ----------

@pytest.fixture
def th_stdout(monkeypatch):
    """Служебные строки [TH] плагин пишет напрямую в sys.__stdout__ мимо capsys (см.
    _th_print) — здесь sys.__stdout__ подменяется на StringIO, чтобы их перехватить."""
    buf = io.StringIO()
    monkeypatch.setattr(sys, "__stdout__", buf)
    return buf


def _th_lines(buf, prefix="[TH]"):
    """Строки плагина из буфера th_stdout без пустых строк, оставшихся от ведущих \n."""
    return [line for line in buf.getvalue().splitlines() if line.startswith(prefix)]


@pytest.fixture
def plugin_env(monkeypatch):
    """Контекстный менеджер `with plugin_env(url=..., run_id=..., run_token=...) as module:`.

    На входе выставляет TH_URL/TH_RUN_ID/TH_RUN_TOKEN (или удаляет, если аргумент не
    передан) и перезагружает utils.test_hub_plugin, чтобы ENABLED и сами константы в
    модуле пересчитались под новые значения. На выходе — откатывает патч allure.step
    (если тест его наложил и не снял сам) и перезагружает модуль уже без TH_* env,
    возвращая процесс в «выключенное» состояние до того, как тело теста завершится."""

    def _unpatch_if_needed():
        if th_plugin._step_patched:
            th_plugin._unpatch_allure_step()

    def _apply(url, run_id, run_token):
        for name, value in (("TH_URL", url), ("TH_RUN_ID", run_id), ("TH_RUN_TOKEN", run_token)):
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)
        return importlib.reload(th_plugin)

    @contextlib.contextmanager
    def _cm(url=None, run_id=None, run_token=None):
        _unpatch_if_needed()
        module = _apply(url, run_id, run_token)
        try:
            yield module
        finally:
            _unpatch_if_needed()
            _apply(None, None, None)

    yield _cm

    # Страховка на случай теста, который не использовал `with` (например, упал раньше).
    _unpatch_if_needed()
    _apply(None, None, None)


class FakeConfig:
    """Минимальный дублёр pytest.Config: плагину нужен только add_cleanup."""

    def __init__(self):
        self.cleanups = []

    def add_cleanup(self, fn):
        self.cleanups.append(fn)


class FakeItem:
    def __init__(self, nodeid, funcargs=None):
        self.nodeid = nodeid
        self.funcargs = funcargs or {}


class FakeReport:
    """Дублёр pytest.TestReport — только то, что реально читает _classify_report."""

    def __init__(self, nodeid, when, outcome, wasxfail=False):
        self.nodeid = nodeid
        self.when = when
        self.failed = outcome == "failed"
        self.skipped = outcome == "skipped"
        self.passed = outcome == "passed"
        if wasxfail:
            self.wasxfail = ""


class FakePage:
    """Дублёр страницы Playwright: screenshot() отдаёт валидный PNG, без реального браузера."""

    def __init__(self, png_bytes=_PNG_BYTES, viewport=None, closed=False):
        self._png_bytes = png_bytes
        self._viewport = viewport or {"width": 800, "height": 600}
        self._closed = closed
        self.screenshot_calls = []

    def is_closed(self):
        return self._closed

    @property
    def viewport_size(self):
        return self._viewport

    def set_viewport_size(self, size):
        self._viewport = size

    def screenshot(self, **kwargs):
        self.screenshot_calls.append(kwargs)
        return self._png_bytes


# ---------- 1. выключенное состояние без TH_* env ----------

def test_disabled_without_th_env(plugin_env, th_stdout):
    with plugin_env() as module:
        assert module.ENABLED is False
        module.pytest_runtest_logstart("tests/test_x.py::test_a", None)
        module.pytest_runtest_logreport(FakeReport("tests/test_x.py::test_a", "call", "passed"))

    assert th_stdout.getvalue() == ""


def test_disabled_pytest_configure_does_not_patch_allure_step(plugin_env):
    with plugin_env() as module:
        original_step = allure.step
        config = FakeConfig()

        module.pytest_configure(config)

        assert allure.step is original_step
        assert module._step_patched is False
        assert config.cleanups == []


def test_disabled_even_with_partial_th_env(plugin_env):
    """Раннер передаёт все три переменные разом — если хотя бы одной не хватает,
    плагин должен оставаться выключенным (см. ENABLED = bool(TH_URL and TH_RUN_ID and TH_RUN_TOKEN))."""
    with plugin_env(url="http://x", run_id="1", run_token=None) as module:
        assert module.ENABLED is False


# ---------- 2. разметка start/end по исходам ----------

def test_logstart_prints_th_start(plugin_env, th_stdout):
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        assert module.ENABLED is True
        module.pytest_runtest_logstart("tests/test_x.py::test_a", None)

    assert th_stdout.getvalue() == "\n[TH] start tests/test_x.py::test_a\n"


def test_logreport_end_passed(plugin_env, th_stdout):
    nodeid = "tests/test_x.py::test_a"
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        module.pytest_runtest_logreport(FakeReport(nodeid, "setup", "passed"))
        module.pytest_runtest_logreport(FakeReport(nodeid, "call", "passed"))
        module.pytest_runtest_logreport(FakeReport(nodeid, "teardown", "passed"))

    assert _th_lines(th_stdout) == [f"[TH] end {nodeid} passed"]


def test_logreport_end_failed(plugin_env, th_stdout):
    nodeid = "tests/test_x.py::test_a"
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        module.pytest_runtest_logreport(FakeReport(nodeid, "setup", "passed"))
        module.pytest_runtest_logreport(FakeReport(nodeid, "call", "failed"))
        module.pytest_runtest_logreport(FakeReport(nodeid, "teardown", "passed"))

    assert _th_lines(th_stdout) == [f"[TH] end {nodeid} failed"]


def test_logreport_end_skipped(plugin_env, th_stdout):
    nodeid = "tests/test_x.py::test_a"
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        module.pytest_runtest_logreport(FakeReport(nodeid, "setup", "skipped"))
        module.pytest_runtest_logreport(FakeReport(nodeid, "teardown", "passed"))

    assert _th_lines(th_stdout) == [f"[TH] end {nodeid} skipped"]


def test_logreport_end_xfailed(plugin_env, th_stdout):
    nodeid = "tests/test_x.py::test_a"
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        module.pytest_runtest_logreport(FakeReport(nodeid, "setup", "passed"))
        module.pytest_runtest_logreport(FakeReport(nodeid, "call", "skipped", wasxfail=True))
        module.pytest_runtest_logreport(FakeReport(nodeid, "teardown", "passed"))

    assert _th_lines(th_stdout) == [f"[TH] end {nodeid} xfailed"]


def test_logreport_end_emitted_only_once(plugin_env, th_stdout):
    """Даже если по какой-то причине call и teardown оба дадут классифицируемый исход
    (например, тест падает в teardown после успешного call), в лог должна уйти только
    первая строка end — раннер не должен увидеть два конфликтующих исхода одного теста."""
    nodeid = "tests/test_x.py::test_a"
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        module.pytest_runtest_logreport(FakeReport(nodeid, "call", "passed"))
        module.pytest_runtest_logreport(FakeReport(nodeid, "teardown", "failed"))

    assert _th_lines(th_stdout) == [f"[TH] end {nodeid} passed"]


# ---------- 3. шаги: нумерация, контекст-менеджер и декоратор ----------

def test_steps_numbered_sequentially_as_context_manager(plugin_env, th_stdout):
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        item = FakeItem("tests/test_x.py::test_a")
        module._state["item"] = item
        module._patch_allure_step()

        with allure.step("first"):
            pass
        with allure.step("second"):
            pass
        with allure.step("third"):
            pass

    assert _th_lines(th_stdout, "[TH] step") == [
        f"[TH] step {item.nodeid} 1 first",
        f"[TH] step {item.nodeid} 2 second",
        f"[TH] step {item.nodeid} 3 third",
    ]


def test_step_as_decorator_prints_and_preserves_return_value(plugin_env, th_stdout):
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        item = FakeItem("tests/test_x.py::test_a")
        module._state["item"] = item
        module._patch_allure_step()

        @allure.step("do work")
        def do_work(x):
            return x * 2

        result = do_work(21)

    assert result == 42
    assert _th_lines(th_stdout, "[TH] step") == [f"[TH] step {item.nodeid} 1 do work"]


def test_step_context_manager_and_decorator_share_numbering(plugin_env, th_stdout):
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        item = FakeItem("tests/test_x.py::test_a")
        module._state["item"] = item
        module._patch_allure_step()

        @allure.step("decorated")
        def decorated():
            return "ok"

        with allure.step("first"):
            pass
        decorated()
        with allure.step("third"):
            pass

    assert _th_lines(th_stdout, "[TH] step") == [
        f"[TH] step {item.nodeid} 1 first",
        f"[TH] step {item.nodeid} 2 decorated",
        f"[TH] step {item.nodeid} 3 third",
    ]


def test_step_context_manager_reraises_exception(plugin_env, th_stdout):
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        item = FakeItem("tests/test_x.py::test_a")
        module._state["item"] = item
        module._patch_allure_step()

        with pytest.raises(ValueError, match="boom"):
            with allure.step("boom"):
                raise ValueError("boom")

    assert _th_lines(th_stdout, "[TH] step") == [f"[TH] step {item.nodeid} 1 boom"]


def test_step_decorator_reraises_exception(plugin_env):
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        module._state["item"] = FakeItem("tests/test_x.py::test_a")
        module._patch_allure_step()

        @allure.step("risky")
        def risky():
            raise RuntimeError("kaboom")

        with pytest.raises(RuntimeError, match="kaboom"):
            risky()


def test_allure_attach_inside_step_still_works(plugin_env, th_stdout):
    """Патч allure.step не должен ломать allure.attach внутри тела шага —
    это отдельный путь (allure_commons.plugin_manager), который плагин не трогает."""
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        module._state["item"] = FakeItem("tests/test_x.py::test_a")
        module._patch_allure_step()

        with allure.step("attach something"):
            allure.attach(b"payload", name="note", attachment_type=allure.attachment_type.TEXT)

    assert "[TH] step" in th_stdout.getvalue()


def test_pytest_configure_patches_and_cleanup_unpatches(plugin_env):
    with plugin_env(url="http://x", run_id="1", run_token="tok") as module:
        original_step = allure.step
        config = FakeConfig()

        module.pytest_configure(config)
        assert allure.step is not original_step
        assert module._step_patched is True
        assert len(config.cleanups) == 1

        config.cleanups[0]()
        assert allure.step is original_step
        assert module._step_patched is False


# ---------- 4-7. кадры: мок HTTP-сервер ----------

class _FrameHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        header = ("Content-Type: " + content_type + "\r\nMIME-Version: 1.0\r\n\r\n").encode()
        msg = email.message_from_bytes(header + body)
        record = {"path": self.path, "authorization": self.headers.get("Authorization")}
        for part in msg.get_payload() or []:
            name = part.get_param("name", header="Content-Disposition")
            filename = part.get_param("filename", header="Content-Disposition")
            payload = part.get_payload(decode=True)
            if filename:
                record[name] = {"filename": filename, "content": payload}
            else:
                record[name] = payload.decode() if isinstance(payload, bytes) else payload
        self.server.received.append(record)
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A002 — сигнатура BaseHTTPRequestHandler
        pass


@pytest.fixture
def frame_server():
    """ThreadingHTTPServer на localhost:0 (свободный порт), принимающий multipart POST
    и сохраняющий разобранные поля (nodeid/step/file/Authorization) в server.received."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FrameHandler)
    server.received = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _base_url(server):
    host, port = server.server_address
    return f"http://{host}:{port}"


def test_frame_sent_to_mock_server_with_multipart_and_bearer_token(plugin_env, frame_server, th_stdout):
    with plugin_env(url=_base_url(frame_server), run_id="run42", run_token="sekret-token") as module:
        item = FakeItem("tests/test_ui.py::test_login", funcargs={"page": FakePage()})
        module._state["item"] = item
        module._patch_allure_step()

        with allure.step("open login page"):
            pass

    assert len(frame_server.received) == 1
    record = frame_server.received[0]
    assert record["path"] == "/api/runs/run42/frames"
    assert record["authorization"] == "Bearer sekret-token"
    assert record["nodeid"] == item.nodeid
    assert record["step"] == "1"
    assert record["file"]["filename"] == "step_1.png"
    assert record["file"]["content"][:8] == _PNG_BYTES[:8]

    assert f"[TH] step {item.nodeid} 1 open login page" in th_stdout.getvalue()


def test_frame_captured_for_each_step_with_active_page(plugin_env, frame_server):
    with plugin_env(url=_base_url(frame_server), run_id="run1", run_token="tok") as module:
        item = FakeItem("tests/test_ui.py::test_flow", funcargs={"page": FakePage()})
        module._state["item"] = item
        module._patch_allure_step()

        with allure.step("step one"):
            pass
        with allure.step("step two"):
            pass

    assert len(frame_server.received) == 2
    assert [r["step"] for r in frame_server.received] == ["1", "2"]


def test_admin_and_user_page_fixtures_are_also_detected(plugin_env, frame_server):
    """Плагин ищет активную страницу по нескольким именам funcargs, не только "page"."""
    with plugin_env(url=_base_url(frame_server), run_id="run1", run_token="tok") as module:
        item = FakeItem("tests/test_ui.py::test_admin_flow", funcargs={"admin_page": FakePage()})
        module._state["item"] = item
        module._patch_allure_step()

        with allure.step("do admin thing"):
            pass

    assert len(frame_server.received) == 1


# ---------- 5. сетевая ошибка не должна ронять тест ----------

def test_frame_network_error_does_not_raise(plugin_env, th_stdout):
    """TH_URL указывает на заведомо закрытый локальный порт — POST не пройдёт,
    но шаг должен допечататься, а исключение наружу не выйти (см. _send_frame try/except)."""
    closed_port_server = ThreadingHTTPServer(("127.0.0.1", 0), _FrameHandler)
    dead_url = _base_url(closed_port_server)
    closed_port_server.server_close()  # закрываем сокет сразу — порт свободен, но никто не слушает

    with plugin_env(url=dead_url, run_id="run1", run_token="tok") as module:
        item = FakeItem("tests/test_ui.py::test_flaky_network", funcargs={"page": FakePage()})
        module._state["item"] = item
        module._patch_allure_step()

        with allure.step("do something"):
            pass  # не должно бросить исключение, несмотря на недоступный TH_URL

    assert f"[TH] step {item.nodeid} 1 do something" in th_stdout.getvalue()


# ---------- 6. лимит кадров на тест ----------

def test_frame_limit_stops_sending_but_steps_keep_logging(plugin_env, frame_server, th_stdout):
    with plugin_env(url=_base_url(frame_server), run_id="run1", run_token="tok") as module:
        limit = module.MAX_FRAMES_PER_TEST
        total_steps = limit + 10
        item = FakeItem("tests/test_ui.py::test_many_steps", funcargs={"page": FakePage()})
        module._state["item"] = item
        module._patch_allure_step()

        for i in range(total_steps):
            with allure.step(f"step {i}"):
                pass

    assert len(frame_server.received) == limit

    step_lines = _th_lines(th_stdout, "[TH] step")
    assert len(step_lines) == total_steps
    assert step_lines[-1] == f"[TH] step {item.nodeid} {total_steps} step {total_steps - 1}"


# ---------- 7. API-тесты (без активной страницы) не создают кадров ----------

def test_api_test_without_page_creates_no_frames(plugin_env, frame_server, th_stdout):
    with plugin_env(url=_base_url(frame_server), run_id="run1", run_token="tok") as module:
        item = FakeItem("tests/test_api.py::test_create_user", funcargs={"api_client": object()})
        module._state["item"] = item
        module._patch_allure_step()

        with allure.step("create user via api"):
            pass
        with allure.step("check response"):
            pass

    assert frame_server.received == []
    assert _th_lines(th_stdout, "[TH] step") == [
        f"[TH] step {item.nodeid} 1 create user via api",
        f"[TH] step {item.nodeid} 2 check response",
    ]
