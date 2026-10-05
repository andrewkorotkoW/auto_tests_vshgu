from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class HomeworkEndpoint:
    """Методы для работы с практическими заданиями (homework)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание практического задания."""
        resp = self.client.post("/content", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Homework created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def delete(self, content_id: int) -> bool:
        """Удаление одного задания."""
        return self.mass_delete([content_id])

    def mass_delete(self, content_ids: list) -> bool:
        """Массовое удаление заданий."""
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
            logger.info(f"Homeworks deleted: {content_ids}")
        else:
            logger.warning(f"Homeworks delete failed: {resp.status_code}")
        return success

    def examine(self, homework_id: int, answer_id: int, grade: str = "5",
                status="accepted", teacher_comment: str = "Это итоговая оценка",
                deadline: str = "") -> Dict:
        """Проверка домашнего задания преподавателем.

        status — строковый код API ("accepted" или "sent_back"), числовой enum
        (0-5) устарел и API его больше не принимает (422 «Статус ошибочно»).
        Legacy-значение 2 (историческое «принято») транслируется в "accepted"
        для обратной совместимости вызовов. Для status="sent_back" API требует
        непустой deadline.
        """
        if status == 2:
            status = "accepted"
        url = f"{self.client.base_url}/homework/{homework_id}/answers/{answer_id}/examination"
        payload = {
            "data": {
                "attributes": {
                    "grade": grade,
                    "status": status,
                    "deadline": deadline,
                    "teacher_comment": teacher_comment
                }
            }
        }
        resp = self.client.session.post(url, json=payload)
        expect_status(resp, 200)
        logger.info(f"Homework {homework_id} answer {answer_id} examined: status={status}")
        return resp.json()

    def get_status(self, homework_id: int, user_id: int) -> str:
        """Получить статус домашнего задания для пользователя."""
        resp = self.client.get(f"/homework/{homework_id}/status/{user_id}")
        expect_status(resp, 200)
        data = resp.json().get("data", {})
        status = data.get("attributes", {}).get("status") or data.get("status")
        logger.info(f"Homework {homework_id} status for user {user_id}: {status}")
        return status