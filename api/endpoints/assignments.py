from typing import Dict
from urllib.parse import urlencode

from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status

# Статусы прохождения контента потока (change-state), для дашбордов статистики.
CONTENT_STATE_NOT_STARTED = 0
CONTENT_STATE_LAUNCHED = 1
CONTENT_STATE_PASSED = 2


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

    def list_for_stream(self, program_id: int, stream_id: int, stream_content_ids: list) -> list:
        """Назначения потока, отфильтрованные по stream_content_id — чтобы найти
        assignment_id конкретного пользователя для конкретного контента (нужно
        для смены статуса прохождения change_state)."""
        params = [("per-page", 50), ("page", 1)]
        for stream_content_id in stream_content_ids:
            params.append(("filters[stream_contents][]", stream_content_id))
        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/assignments?{urlencode(params)}"
        )
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def change_state(self, user_id: int, assignment_id: int, stream_content_id: int, state: int) -> Dict:
        """Смена статуса прохождения контента потока пользователем (0/1/2 —
        не начат/запущен/пройден) — влияет на статистику дашборда курсов."""
        resp = self.client.put(
            f"/users/{user_id}/assignments/{assignment_id}/stream_contents/{stream_content_id}/change-state",
            json={"state": state}
        )
        expect_status(resp, (200, 201))
        logger.info(
            f"Content state changed: user={user_id}, assignment={assignment_id}, "
            f"stream_content={stream_content_id}, state={state}"
        )
        return resp.json()

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