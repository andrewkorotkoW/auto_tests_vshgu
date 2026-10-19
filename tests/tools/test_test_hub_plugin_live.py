"""Юнит-тесты живой трансляции (screencast) и видео теста из utils/test_hub_plugin.py
(раздел 1 и 2 docs/missions/2026-10-01_live_stream_plugin.md) — без стенда, без реальной
сети и без CDP/браузера: собственный мок-сервер по образцу frame_server/_FrameHandler из
tests/tools/test_test_hub_plugin.py, фоновый цикл трансляции (_live_sender_loop) гоняется
напрямую с управляемой "очередью последнего кадра" вместо настоящего CDP-потока.

Этот файл не редактирует tests/tools/test_test_hub_plugin.py и не дублирует его имена —
см. комментарий там же про importlib.reload(th_plugin) и plugin_env.
"""
import base64
import contextlib
import email
import importlib
import io
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

import allure
import pytest

import conftest as th_conftest
import utils.test_hub_plugin as th_plugin

pytestmark = pytest.mark.tools

_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


# ---------- инфраструктура: reload плагина под нужный TH_* env (+ TH_LIVE/TH_LIVE_FPS) ----------

@pytest.fixture
def th_stdout(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "__stdout__", buf)
    return buf


def _th_lines(buf, prefix="[TH]"):
    return [line for line in buf.getvalue().splitlines() if line.startswith(prefix)]


@pytest.fixture
def plugin_env(monkeypatch):
    """Как plugin_env в test_test_hub_plugin.py, но дополнительно управляет TH_LIVE/TH_LIVE_FPS —
    этот модуль пересчитывает LIVE_ENABLED/TH_LIVE_FPS при импорте так же, как ENABLED."""

    def _unpatch_if_needed():
        if th_plugin._step_patched:
            th_plugin._unpatch_allure_step()

    def _apply(url, run_id, run_token, live, live_fps):
        for name, value in (
            ("TH_URL", url),
            ("TH_RUN_ID", run_id),
            ("TH_RUN_TOKEN", run_token),
            ("TH_LIVE", live),
            ("TH_LIVE_FPS", live_fps),
        ):
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, str(value))
        return importlib.reload(th_plugin)

    @contextlib.contextmanager
    def _cm(url=None, run_id=None, run_token=None, live=None, live_fps=None):
        _unpatch_if_needed()
        module = _apply(url, run_id, run_token, live, live_fps)
        try:
            yield module
        finally:
            _unpatch_if_needed()
            _apply(None, None, None, None, None)

    yield _cm

    _unpatch_if_needed()
    _apply(None, None, None, None, None)


class FakeItem:
    def __init__(self, nodeid, funcargs=None):
        self.nodeid = nodeid
        self.funcargs = funcargs or {}


class FakeCdpSession:
    """Дублёр page.context.new_cdp_session(page): запоминает send()/on(), emit_frame()
    эмулирует событие Page.screencastFrame от CDP."""

    def __init__(self):
        self.handlers = {}
        self.sent = []
        self.detached = False

    def on(self, event, callback):
        self.handlers[event] = callback

    def send(self, method, params=None):
        self.sent.append((method, params))

    def detach(self):
        self.detached = True

    def emit_frame(self, jpeg_bytes, session_id="s1"):
        handler = self.handlers.get("Page.screencastFrame")
        assert handler is not None, "Page.startScreencast ещё не вызван"
        handler({"sessionId": session_id, "data": base64.b64encode(jpeg_bytes).decode()})


class FakeContext:
    def __init__(self):
        self.cdp_sessions = []

    def new_cdp_session(self, page):
        session = FakeCdpSession()
        self.cdp_sessions.append(session)
        return session


class FakeLivePage:
    """Дублёр страницы Playwright: screenshot() для кадров по шагам + context.new_cdp_session
    для трансляции — без реального браузера."""

    def __init__(self, png_bytes=_PNG_BYTES, viewport=None, closed=False):
        self._png_bytes = png_bytes
        self._viewport = viewport or {"width": 800, "height": 600}
        self._closed = closed
        self.context = FakeContext()

    def is_closed(self):
        return self._closed

    @property
    def viewport_size(self):
        return self._viewport

    def screenshot(self, **kwargs):
        return self._png_bytes


# ---------- мок-сервер: принимает POST на любой путь (/live, /frames, /video) ----------

class _LiveHandler(BaseHTTPRequestHandler):
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
                record[name] = {
                    "filename": filename,
                    "content": payload,
                    "content_type": part.get_content_type(),
                }
            else:
                record[name] = payload.decode() if isinstance(payload, bytes) else payload
        self.server.received.append(record)
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A002 — сигнатура BaseHTTPRequestHandler
        pass


@pytest.fixture
def live_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _LiveHandler)
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


# ---------- 1. троттлинг отправки живых кадров не чаще TH_LIVE_FPS ----------

def test_live_sender_loop_throttles_to_th_live_fps(plugin_env, live_server):
    """Очередь «последнего кадра» обновляется гораздо чаще, чем TH_LIVE_FPS (как при
    реальном screencast) — фоновый цикл всё равно должен слать не чаще настроенного fps."""
    fps = 5
    duration = 1.0
    with plugin_env(url=_base_url(live_server), run_id="run1", run_token="tok", live="1", live_fps=fps) as module:
        assert module.TH_LIVE_FPS == fps
        slot = {"frame": None, "lock": threading.Lock()}
        stop_event = threading.Event()

        def _feed():
            counter = 0
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                with slot["lock"]:
                    slot["frame"] = counter.to_bytes(8, "big")
                counter += 1
                time.sleep(0.005)
            stop_event.set()

        feeder = threading.Thread(target=_feed, daemon=True)
        feeder.start()
        module._live_sender_loop("tests/test_ui.py::test_x", slot, stop_event)
        feeder.join(timeout=2)

    received = len(live_server.received)
    max_expected = int(duration * fps) + 3  # запас на немедленный первый кадр и джиттер таймера
    assert 1 < received <= max_expected, received


# ---------- 2. отключение трансляции после 20 ошибок подряд, тест не падает ----------

def test_live_disabled_after_20_consecutive_send_errors(plugin_env):
    closed_port_server = ThreadingHTTPServer(("127.0.0.1", 0), _LiveHandler)
    dead_url = _base_url(closed_port_server)
    closed_port_server.server_close()  # порт свободен, но никто не слушает

    with plugin_env(url=dead_url, run_id="run1", run_token="tok", live="1", live_fps=1000) as module:
        slot = {"frame": None, "lock": threading.Lock()}
        stop_event = threading.Event()

        def _feed():
            counter = 0
            while not stop_event.is_set() and counter < 2000:
                with slot["lock"]:
                    slot["frame"] = counter.to_bytes(8, "big")
                counter += 1
                time.sleep(0.002)

        feeder = threading.Thread(target=_feed, daemon=True)
        feeder.start()

        module._live_sender_loop("tests/test_ui.py::test_x", slot, stop_event)  # не должен бросить исключение
        feeder.join(timeout=5)

        assert module._state["live_error_count"] == module.MAX_LIVE_ERRORS
        assert module._state["live_disabled"] is True

    assert stop_event.is_set() is True


# ---------- 3. TH_LIVE=0 — трансляция не стартует вообще ----------

def test_th_live_zero_disables_live_entirely(plugin_env, live_server):
    with plugin_env(url=_base_url(live_server), run_id="run1", run_token="tok", live="0") as module:
        assert module.LIVE_ENABLED is False

        page = FakeLivePage()
        item = FakeItem("tests/test_ui.py::test_x", funcargs={"page": page})
        module._state["item"] = item
        module._patch_allure_step()

        with allure.step("one"):
            pass
        with allure.step("two"):
            pass

    assert page.context.cdp_sessions == []
    assert [r for r in live_server.received if "/live" in r["path"]] == []


# ---------- 4. без TH_URL (ENABLED=False) — никакой активности по трансляции и видео ----------

def test_disabled_without_th_url_no_live_or_video_activity(plugin_env, live_server, tmp_path):
    with plugin_env(live="1") as module:
        assert module.ENABLED is False
        assert module.LIVE_ENABLED is False

        page = FakeLivePage()
        item = FakeItem("tests/test_ui.py::test_x", funcargs={"page": page})

        gen = module.pytest_runtest_protocol(item, None)
        next(gen)
        with pytest.raises(StopIteration):
            next(gen)

        video_path = tmp_path / "video.webm"
        video_path.write_bytes(b"fake webm data")
        thread = module.handle_test_video(item.nodeid, str(video_path), 1500)

    assert thread is None
    assert video_path.exists()
    assert page.context.cdp_sessions == []
    assert live_server.received == []


# ---------- 5. отправка видео: multipart-поля, Authorization, путь ----------

def test_video_sent_with_correct_multipart_fields_and_path(plugin_env, live_server, tmp_path):
    video_path = tmp_path / "rec.webm"
    video_path.write_bytes(b"webm-binary-content")
    nodeid = "tests/ui/test_flow.py::test_submit"

    with plugin_env(url=_base_url(live_server), run_id="run9", run_token="secret9") as module:
        thread = module.handle_test_video(nodeid, str(video_path), 3300)
        thread.join(timeout=5)

    assert len(live_server.received) == 1
    record = live_server.received[0]
    assert unquote(record["path"]) == f"/api/runs/run9/tests/{nodeid}/video"
    assert record["authorization"] == "Bearer secret9"
    assert record["duration_ms"] == "3300"
    assert record["file"]["content"] == b"webm-binary-content"
    assert record["file"]["content_type"] == "video/webm"
    assert record["file"]["filename"].endswith(".webm")


# ---------- 6. удаление файла после успеха; файл остаётся при сетевой ошибке ----------

def test_video_file_removed_from_disk_after_successful_send(plugin_env, live_server, tmp_path):
    video_path = tmp_path / "rec.webm"
    video_path.write_bytes(b"data")

    with plugin_env(url=_base_url(live_server), run_id="run1", run_token="tok") as module:
        thread = module.handle_test_video("tests/test_ui.py::test_x", str(video_path), 1000)
        thread.join(timeout=5)

    assert not video_path.exists()


def test_video_file_kept_on_disk_after_network_error(plugin_env, tmp_path):
    closed_port_server = ThreadingHTTPServer(("127.0.0.1", 0), _LiveHandler)
    dead_url = _base_url(closed_port_server)
    closed_port_server.server_close()

    video_path = tmp_path / "rec.webm"
    video_path.write_bytes(b"data")

    with plugin_env(url=dead_url, run_id="run1", run_token="tok") as module:
        thread = module.handle_test_video("tests/test_ui.py::test_x", str(video_path), 1000)
        thread.join(timeout=5)

    assert video_path.exists()


# ---------- 7. видео прикладывается в allure только для упавших тестов ----------
# conftest.py (_finalize_test_video) уже реализует это правило — точка входа тестируется
# напрямую, без полного прогона pytest (та же идея, что и у plugin_env выше).

class _FakeVideo:
    def __init__(self, path):
        self._path = path

    def path(self):
        return self._path


class _FakeVideoPage:
    def __init__(self, video_path):
        self.video = _FakeVideo(video_path)


class _FakeReportResult:
    def __init__(self, failed):
        self.failed = failed


class _FakeNode:
    def __init__(self, nodeid, rep_call=None, funcargs=None):
        self.nodeid = nodeid
        self.funcargs = funcargs or {}
        if rep_call is not None:
            self.rep_call = rep_call


class _FakeRequest:
    def __init__(self, node):
        self.node = node


def test_finalize_test_video_attaches_to_allure_only_for_failed_tests(monkeypatch, tmp_path):
    attached = []
    monkeypatch.setattr(allure.attach, "file", lambda *a, **k: attached.append((a, k)))

    video_path = tmp_path / "failed.webm"
    video_path.write_bytes(b"data")
    node = _FakeNode("tests/test_ui.py::test_x", rep_call=_FakeReportResult(failed=True))
    request = _FakeRequest(node)
    page = _FakeVideoPage(str(video_path))

    th_conftest._finalize_test_video(request, "page", page, time.monotonic())

    assert len(attached) == 1
    assert attached[0][0][0] == str(video_path)


def test_finalize_test_video_does_not_attach_to_allure_for_passed_tests(monkeypatch, tmp_path):
    attached = []
    monkeypatch.setattr(allure.attach, "file", lambda *a, **k: attached.append((a, k)))

    video_path = tmp_path / "passed.webm"
    video_path.write_bytes(b"data")
    node = _FakeNode("tests/test_ui.py::test_x", rep_call=_FakeReportResult(failed=False))
    request = _FakeRequest(node)
    page = _FakeVideoPage(str(video_path))

    th_conftest._finalize_test_video(request, "page", page, time.monotonic())

    assert attached == []


# ---------- обрезка кадра трансляции до viewport (_crop_live_frame) ----------
# Page.screencastFrame отдаёт видимую область окна: в headed-режиме окно шире
# мобильного viewport 412×839, и справа в кадр попадала белая полоса — в рамке
# Pixel 7 в test_hub кадр не заполнял экран (19.10.2026).

def _jpeg(width, height):
    import cv2
    import numpy as np

    img = np.full((height, width, 3), 255, dtype=np.uint8)
    img[:, : width // 2] = (0, 0, 255)  # левая половина красная — проверяем, что режем справа
    ok, out = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    assert ok
    return out.tobytes()


def _jpeg_size(data):
    import cv2
    import numpy as np

    img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    return img.shape[1], img.shape[0]


def test_crop_live_frame_cuts_window_area_outside_viewport():
    # окно 500×839 DIP при viewport 412×839 → кадр 600×1007 режется до 412/500 ширины
    frame = _jpeg(600, 1007)
    cropped = th_plugin._crop_live_frame(frame, {"deviceWidth": 500, "deviceHeight": 839}, {"width": 412, "height": 839})
    assert _jpeg_size(cropped) == (494, 1007)


def test_crop_live_frame_noop_when_window_matches_viewport():
    frame = _jpeg(412, 839)
    same = th_plugin._crop_live_frame(frame, {"deviceWidth": 412, "deviceHeight": 839}, {"width": 412, "height": 839})
    assert same is frame
    # headless: окно даже меньше viewport не бывает, но и тут ничего не режем
    smaller = th_plugin._crop_live_frame(frame, {"deviceWidth": 400, "deviceHeight": 800}, {"width": 412, "height": 839})
    assert smaller is frame


def test_crop_live_frame_noop_without_metadata_or_viewport_or_on_bad_jpeg():
    frame = _jpeg(100, 60)
    assert th_plugin._crop_live_frame(frame, {}, {"width": 50, "height": 60}) is frame
    assert th_plugin._crop_live_frame(frame, None, None) is frame
    assert th_plugin._crop_live_frame(frame, {"deviceWidth": 100, "deviceHeight": 60}, {}) is frame
    garbage = b"not a jpeg"
    assert th_plugin._crop_live_frame(garbage, {"deviceWidth": 100, "deviceHeight": 60}, {"width": 50, "height": 60}) is garbage
