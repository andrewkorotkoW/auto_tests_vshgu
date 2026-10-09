from typing import Dict

import requests

from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class QrCodeEndpoint:
    """Методы для работы с персональным QR-кодом пользователя.

    QR генерируется для текущего авторизованного пользователя из токена сессии,
    явного user_id нет (docs/qr_code_ratings_recon.md, раздел «QR-код»)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def generate_qr_code(self) -> requests.Response:
        """GET /qr-code/generate → 200, Content-Type: image/png, Content-Disposition:
        attachment; filename="my-qr-code.png" — бинарный PNG персонального QR текущего
        пользователя. Возвращает resp целиком (тело не JSON, см. resp.content/headers)."""
        resp = self.client.get("/qr-code/generate")
        expect_status(resp, 200)
        logger.info(f"QR code generated: Content-Type={resp.headers.get('Content-Type')}")
        return resp

    def download_qr_code(self) -> requests.Response:
        """GET /qr-code/download → 200, Content-Type: application/pdf, Content-Disposition:
        attachment; filename="my-qr-code.pdf" — PDF-версия того же персонального QR, не иной
        набор данных (docs/qr_code_ratings_recon.md, раздел «QR-код»)."""
        resp = self.client.get("/qr-code/download")
        expect_status(resp, 200)
        logger.info(f"QR code downloaded: Content-Type={resp.headers.get('Content-Type')}")
        return resp

    def parse_qr_token(self, token: str) -> Dict:
        """POST /qr-code/parse-token, конверт {"data": {"attributes": {"token": token}}} —
        подтверждён разведкой только по форме ошибки 422 при отсутствии поля; успешный ответ
        с реальным токеном не проверен (docs/qr_code_ratings_recon.md, п. «Не проверено»),
        поэтому формат успешного тела возвращается как есть, без предположения про ["data"]."""
        payload = {"data": {"attributes": {"token": token}}}
        resp = self.client.post("/qr-code/parse-token", json=payload)
        expect_status(resp, 200)
        data = resp.json()
        logger.info("QR token parsed")
        return data
