from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class AlpinaEndpoint:
    def __init__(self, client: ApiClient):
        self.client = client

    def set_status(self, user_ids: list, status: bool = True) -> Dict:
        """Открыть/закрыть доступ к Альпине."""
        payload = {"user_ids": user_ids, "status": status}
        resp = self.client.post("/alpina/setUserAlpinaStatus", json=payload)
        assert resp.status_code in (200, 201), (
            f"Alpina set status failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()
        logger.info(f"Alpina status set: users={user_ids}, status={status}")
        return data