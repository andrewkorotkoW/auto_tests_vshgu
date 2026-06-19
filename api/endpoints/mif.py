from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class MifEndpoint:
    def __init__(self, client: ApiClient):
        self.client = client

    def set_access(self, user_ids: list, access: bool = True) -> Dict:
        """Открыть/закрыть доступ к MIF."""
        payload = {"user_ids": user_ids, "access": access}
        resp = self.client.patch("/mif/access", json=payload)
        assert resp.status_code in (200, 204), (
            f"MIF set access failed: {resp.status_code} {resp.text}"
        )
        data = resp.json() if resp.text else {"status": "success"}
        logger.info(f"MIF access set: users={user_ids}, access={access}")
        return data