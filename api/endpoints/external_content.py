from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class ExternalContentEndpoint:
    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        resp = self.client.post("/content", json=payload)
        expect_status(resp, (200, 201))
        return resp.json()["data"]

    def activate(self, content_id: int, payload: dict) -> Dict:
        """Активация контента."""
        resp = self.client.put(f"/content/{content_id}", json=payload)
        expect_status(resp, 200)
        return resp.json()["data"]

    def delete(self, content_id: int) -> bool:
        resp = self.client.delete(f"/content/{content_id}")
        return resp.status_code in (200, 204)

    def assign_to_module(self, program_id: int, stream_id: int, module_id: int, content_ids: list) -> bool:
        """Назначение контента в модуль."""
        payload = {
            "data": {
                "attributes": {
                    "content_ids": content_ids,
                    "stream_module_id": module_id
                }
            }
        }
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/mass-addition",
            json=payload
        )
        success = resp.status_code in (200, 201)
        if success:
            logger.info(f"Content assigned to module {module_id}: {content_ids}")
        else:
            logger.warning(f"Content assign failed: {resp.status_code}")
        return success