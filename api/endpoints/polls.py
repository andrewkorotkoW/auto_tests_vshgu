from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class PollsEndpoint:
    """Методы для работы с опросами (type=poll)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание опроса. Возвращает данные созданного опроса."""
        resp = self.client.post("/tests", json=payload)
        assert resp.status_code in (200, 201), (
            f"Poll create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        data["id"] = data["content_id"]
        logger.info(f"Poll created: ID={data['id']}, name={data.get('name')}")
        return data

    def get(self, poll_id: int) -> Dict:
        """Получение опроса по ID."""
        resp = self.client.get(f"/tests/{poll_id}")
        assert resp.status_code == 200, f"Get poll failed: {resp.status_code}"
        return resp.json()["data"]

    def update(self, poll_id: int, payload: dict) -> Dict:
        """Обновление опроса (PUT)."""
        resp = self.client.put(f"/tests/{poll_id}", json=payload)
        assert resp.status_code in (200, 201), (
            f"Poll update failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        data["id"] = data.get("content_id", poll_id)
        logger.info(f"Poll updated: ID={data['id']}, name={data.get('name')}")
        return data

    def delete(self, poll_id: int) -> bool:
        """Удаление опроса."""
        return self.mass_delete([poll_id])

    def mass_delete(self, content_ids: list) -> bool:
        """Массовое удаление опросов."""
        payload = {"contents_ids": content_ids}
        resp = self.client.delete("/tests", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Polls deleted: {content_ids}")
        else:
            logger.warning(f"Polls delete failed: {resp.status_code} {resp.text[:200]}")
        return success

    def create_question(self, content_id: int, question: dict) -> Dict:
        """Создание вопроса для опроса."""
        payload = {
            "content_id": content_id,
            "question": question
        }
        resp = self.client.put("/tests/questions/store", json=payload)
        assert resp.status_code in (200, 201), (
            f"Question create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()
        logger.info(f"Question created for poll {content_id}")
        return data

    def get_assignment_uuid(self, content_id: int) -> str:
        """Получить assignment_uuid для контента (опрос/тест) через инд. трек."""
        resp = self.client.get(f"/my-personal-training/distant/{content_id}")
        assert resp.status_code == 200, f"Get assignment_uuid failed: {resp.status_code} {resp.text}"
        data = resp.json()["data"]["attributes"]
        assignment_uuid = data["assignment_uuid"]
        logger.info(f"Assignment UUID: {assignment_uuid} for content {content_id}")
        return assignment_uuid

    def launch(self, assignment_id: str, content_id: int) -> Dict:
        """Запуск опроса."""
        resp = self.client.post(f"/assignments/{assignment_id}/contents/{content_id}/launch")
        assert resp.status_code in (200, 201), f"Launch poll failed: {resp.status_code} {resp.text}"
        logger.info(f"Poll launched: assignment={assignment_id}, content={content_id}")
        return resp.json()

    def get_current_try(self, content_id: int, assignment_id: str) -> Dict:
        """Получить текущую попытку опроса."""
        resp = self.client.get(f"/tests/current/try/{content_id}/{assignment_id}")
        assert resp.status_code == 200, f"Get current try failed: {resp.status_code}"
        return resp.json()

    def assign_activities(self, content_ids: list, user_ids: list) -> bool:
        """Назначение активностей (опросов) пользователям (инд. трек)."""
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

    def delete(self, poll_id: int) -> bool:
        return self.mass_delete([poll_id])

