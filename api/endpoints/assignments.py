from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class AssignmentsEndpoint:
    """Методы для работы с назначениями пользователей в поток."""

    def __init__(self, client: ApiClient):
        self.client = client

    def assign(self, program_id: int, stream_id: int, user_ids: list) -> Dict:
        """Назначение пользователей в поток."""
        payload = {
            "data": {
                "attributes": {
                    "users_ids": user_ids
                }
            }
        }
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/assignments",
            json=payload
        )
        expect_status(resp, (200, 201))
        data = resp.json()
        logger.info(f"Users assigned: {user_ids} to stream {stream_id}")
        return data

    def assign_content_to_module(self, program_id: int, stream_id: int, module_id: int, content_ids: list) -> bool:
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
            logger.info(f"Content {content_ids} assigned to module {module_id}")
        else:
            logger.warning(f"Content assign failed: {resp.status_code} {resp.text[:200]}")
        return success

    def assign_to_individual(self, content_ids: list, user_ids: list) -> bool:
        """Назначение активностей пользователям (инд. трек)."""
        payload = {
            "data": {
                "attributes": {
                    "content_ids": content_ids,
                    "user_ids": user_ids
                }
            }
        }
        resp = self.client.post("/users/content/distant/assign-activities", json=payload)
        success = resp.status_code in (200, 201)
        if success:
            logger.info(f"Activities {content_ids} assigned to users {user_ids}")
        else:
            logger.warning(f"Assign activities failed: {resp.status_code} {resp.text[:200]}")
        return success

    def detach_from_individual(self, content_ids: list, user_ids: list) -> bool:
        """Снятие назначения (инд. трек)."""
        payload = {
            "data": {
                "attributes": {
                    "content_ids": content_ids,
                    "user_ids": user_ids
                }
            }
        }
        resp = self.client.post("/users/content/distant/detach-activities", json=payload)
        success = resp.status_code in (200, 201)
        if success:
            logger.info(f"Activities {content_ids} detached from users {user_ids}")
        else:
            logger.warning(f"Detach activities failed: {resp.status_code} {resp.text[:200]}")
        return success