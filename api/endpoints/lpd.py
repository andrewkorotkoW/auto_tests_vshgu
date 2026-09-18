from typing import Dict
from urllib.parse import quote

from api.client import ApiClient
from utils.logger import logger
from utils.retry import retry_until_success
from api.helpers.expectations import expect_status


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
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"LPD created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def get(self, content_id: int) -> Dict:
        """Получение контента по ID."""
        resp = self.client.get(f"/content/{content_id}")
        expect_status(resp, 200)
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

    def assign_users_with_retry(self, module_id: int, content_id: int, stream_id: int, user_ids: list):
        """Назначение пользователей на LPD с повтором, пока бэкенд не проиндексирует
        только что добавленный в модуль контент (см. utils.retry.retry_until_success).
        Возвращает сырой Response — вызывающий код сам решает, что делать со статусом."""
        resp = retry_until_success(lambda: self.client.post(
            f"/modules/{module_id}/contents/{content_id}/lpd/assignment?stream={stream_id}",
            json={"users": user_ids}
        ))
        expect_status(resp, (200, 201))
        logger.info(f"Users {user_ids} activated on LPD {content_id} in module {module_id}")
        return resp

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

    def get_result(self, content_id: int, user_id: int) -> Dict:
        """Получение результата прохождения LPD (invite_id и т.п.)."""
        resp = self.client.get(f"/lpd/result?content_id={content_id}&user_id={user_id}")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    def store_state(self, user_id: int, invite_id: str, state_id: int, jwt_token: str):
        """Принудительно меняет состояние прохождения LPD (используется для сброса прогресса)."""
        resp = self.client.get(
            f"/lpd/result/store-state?userId={user_id}&inviteId={quote(invite_id)}&stateId={state_id}",
            headers={"Authorization": jwt_token, "Accept": "application/json"},
        )
        expect_status(resp, 200)
        logger.info(f"LPD store-state: user={user_id}, invite={invite_id}, state={state_id}")
        return resp

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


