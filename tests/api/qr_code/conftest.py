"""Фикстуры для tests/api/qr_code (docs/qr_code_ratings_recon.md, раздел «QR-код»).

decode_qr_png — единственный способ в этом репозитории получить реальный токен,
закодированный в PNG/PDF ответах generate/download: разведка не нашла его открытым
текстом ни в одном JSON-поле. pyzbar недоступен (требует системную либу zbar), но
opencv-python-headless (добавлен в requirements.txt этой задачей) содержит собственный
QRCodeDetector без внешних системных зависимостей и декодирует QR из generate/download
живым прогоном на develop (подтверждено при подготовке задачи)."""
import requests
import pytest

from api.client import ApiClient


@pytest.fixture
def anon_api_client(env):
    """Клиент без авторизации — для проверки 401 у персональных ручек QR-кода."""
    session = requests.Session()
    return ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name)


@pytest.fixture
def decode_qr_png():
    """Возвращает функцию: сырые байты PNG -> строка токена, распознанная из QR."""
    import cv2
    import numpy as np

    def _decode(png_bytes: bytes) -> str:
        arr = np.frombuffer(png_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        assert img is not None, "Не удалось декодировать PNG в изображение"
        detector = cv2.QRCodeDetector()
        data, _points, _straight = detector.detectAndDecode(img)
        assert data, "QRCodeDetector не нашёл/не распознал QR-код на изображении"
        return data

    return _decode
