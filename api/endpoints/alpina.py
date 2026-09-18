from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class AlpinaEndpoint:
    def __init__(self, client: ApiClient):
        self.client = client

    def set_status(self, user_ids: list, status: bool = True) -> Dict:
        """Открыть/закрыть доступ к Альпине."""
        payload = {"user_ids": user_ids, "status": status}
        resp = self.client.post("/alpina/setUserAlpinaStatus", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()
        logger.info(f"Alpina status set: users={user_ids}, status={status}")
        return data