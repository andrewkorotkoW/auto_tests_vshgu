from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class LpdEndpoint:
    """Методы для работы с LPD."""

    def __init__(self, client: ApiClient):
        self.client = client

    def validate_id(self, lpd_id: str) -> bool:
        """Валидация ID LPD."""
        resp = self.client.get(f"/lpd/validate-id?lpd_id={lpd_id}")
        success = resp.status_code == 200
        if success:
            logger.info(f"LPD ID validated: {lpd_id}")
        else:
            logger.warning(f"LPD validate failed: {resp.status_code}")
        return success

    def create(self, payload: dict) -> Dict:
        logger.info(f"LPD create payload lpd_id: {payload['data']['attributes'].get('lpd_id')}")
        resp = self.client.post("/content", json=payload)
        logger.info(f"LPD RAW RESPONSE: {resp.text[:500]}")
        assert resp.status_code in (200, 201), (
            f"LPD create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        logger.info(f"LPD created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def get(self, content_id: int) -> Dict:
        """Получение контента по ID."""
        resp = self.client.get(f"/content/{content_id}")
        assert resp.status_code == 200, f"Get content failed: {resp.status_code}"
        return resp.json()["data"]

    def delete(self, content_id: int) -> bool:
        """Удаление контента."""
        resp = self.client.delete(f"/content/{content_id}")
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Content deleted: ID={content_id}")
        else:
            logger.warning(f"Content delete failed: ID={content_id}, status={resp.status_code}")
        return success

    def assign_to_module(self, program_id: int, stream_id: int, module_id: int, content_ids: list) -> bool:
        """Назначение LPD в модуль."""
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
            logger.info(f"LPD assigned to module {module_id}: {content_ids}")
        else:
            logger.warning(f"LPD assign failed: {resp.status_code}")
        return success

    def assign_users(self, module_id: int, content_id: int, stream_id: int, user_ids: list) -> bool:
        """Назначение пользователей на LPD."""
        resp = self.client.post(
            f"/modules/{module_id}/contents/{content_id}/lpd/assignment?stream={stream_id}",
            json={"users": user_ids}
        )
        success = resp.status_code in (200, 201)
        if success:
            logger.info(f"Users {user_ids} assigned to LPD {content_id}")
        else:
            logger.warning(f"LPD user assign failed: {resp.status_code}")
        return success

    def mass_delete(self, content_ids: list) -> bool:
        """Массовое удаление активностей."""
        payload = {
            "data": {
                "attributes": {
                    "content_ids": content_ids
                }
            }
        }
        resp = self.client.delete("/activities/mass-delete", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Activities mass deleted: {content_ids}")
        else:
            logger.warning(f"Mass delete failed: {resp.status_code}")
        return success

    def assign_activities(self, content_ids: list, user_ids: list) -> bool:
        """Назначение активностей пользователям."""
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
            logger.warning(f"Assign activities failed: {resp.status_code} - {resp.text[:200]}")
        return success

    def detach_activities(self, content_ids: list, user_ids: list) -> bool:
        """Открепление активностей от пользователей."""
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
            logger.warning(f"Detach activities failed: {resp.status_code}")
        return success

    def detach_users(self, module_id: int, content_id: int, stream_id: int, user_ids: list) -> bool:
        """Открепление пользователей от LPD в модуле."""
        resp = self.client.delete(
            f"/modules/{module_id}/contents/{content_id}/lpd/assignment?stream={stream_id}",
            json={"users": user_ids}
        )
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Users {user_ids} detached from LPD {content_id}")
        else:
            logger.warning(f"Detach users failed: {resp.status_code}")
        return success


