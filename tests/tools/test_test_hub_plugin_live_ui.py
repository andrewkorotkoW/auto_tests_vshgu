"""Локальный UI-тест живой трансляции и видео теста (раздел 3 ТЗ
docs/missions/2026-10-01_live_stream_plugin.md): реальный headless Chromium (Playwright)
на мок-странице file://tests/tools/fixtures/live_timer.html (таймер меняет текст/цвет —
кадры screencast отличаются друг от друга) + мок HTTP-сервер вместо test_hub.

Маркер tools, без --env и без стенда — так же, как tests/tools/test_test_hub_plugin.py
и tests/tools/test_test_hub_plugin_live.py (этот файл их не редактирует и не пересекается
с ними по именам).
"""
import importlib
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

import utils.test_hub_plugin as th_plugin

pytestmark = pytest.mark.tools

FIXTURE_HTML = Path(__file__).resolve().parent / "fixtures" / "live_timer.html"


class _MockHandler(BaseHTTPRequestHandler):
    """Принимает POST на любой путь (используется и для /live, и для /video) — для этого
    теста важен только факт запроса и его путь, не разбор multipart-полей (это уже
    проверено в test_test_hub_plugin_live.py на мок-сервере с разбором содержимого)."""

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self.server.received.append(self.path)
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A002 — сигнатура BaseHTTPRequestHandler
        pass


@pytest.fixture
def mock_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MockHandler)
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


@pytest.fixture(scope="module")
def chromium():
    """Отдельный от conftest.py запуск браузера — только для этого файла, всегда headless
    (стенд/дисплей не нужны), независимо от HEADLESS env реальной сессии pytest."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


class _UiItem:
    def __init__(self, nodeid, page):
        self.nodeid = nodeid
        self.funcargs = {"page": page}


def test_live_frames_and_video_on_real_browser_with_file_url(monkeypatch, mock_server, chromium, tmp_path):
    """За 2 секунды page.wait_for_timeout на реальной CDP-трансляции приходит ≥3 живых
    кадра, а после остановки трансляции и закрытия контекста — ровно одно видео теста."""
    monkeypatch.setenv("TH_URL", _base_url(mock_server))
    monkeypatch.setenv("TH_RUN_ID", "run-ui")
    monkeypatch.setenv("TH_RUN_TOKEN", "tok-ui")
    monkeypatch.setenv("TH_LIVE", "1")
    monkeypatch.setenv("TH_LIVE_FPS", "10")
    module = importlib.reload(th_plugin)
    assert module.ENABLED is True
    assert module.LIVE_ENABLED is True

    video_dir = tmp_path / "video"
    video_dir.mkdir()
    context = chromium.new_context(
        viewport={"width": 400, "height": 300},
        record_video_dir=str(video_dir),
        record_video_size={"width": 400, "height": 300},
    )
    page = context.new_page()
    page.goto(f"file://{FIXTURE_HTML}")

    nodeid = "tests/ui/test_fixture.py::test_timer"
    item = _UiItem(nodeid, page)
    module._state["item"] = item
    started_at = time.monotonic()
    video_path = None

    try:
        module._sync_live_session(item)
        assert module._state["live"] is not None, "трансляция не стартовала на реальной странице"

        page.wait_for_timeout(2000)

        live_requests = [p for p in mock_server.received if p == "/api/runs/run-ui/live"]
        assert len(live_requests) >= 3, mock_server.received
    finally:
        module._stop_live_session(module._state.get("live"))
        module._state["live"] = None
        module._state["item"] = None

        duration_ms = int((time.monotonic() - started_at) * 1000)
        context.close()
        video_path = page.video.path()

        thread = module.handle_test_video(nodeid, video_path, duration_ms)
        thread.join(timeout=10)

        for name in ("TH_URL", "TH_RUN_ID", "TH_RUN_TOKEN", "TH_LIVE", "TH_LIVE_FPS"):
            monkeypatch.delenv(name, raising=False)
        importlib.reload(th_plugin)

    video_requests = [p for p in mock_server.received if p.startswith("/api/runs/run-ui/tests/")]
    assert len(video_requests) == 1, mock_server.received
    assert not os.path.exists(video_path)
