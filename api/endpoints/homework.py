from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class HomeworkEndpoint:
    """Методы для работы с практическими заданиями (homework)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание практического задания."""
        resp = self.client.post("/content", json=payload)
        assert resp.status_code in (200, 201), (
            f"Homework create failed: {resp.status_code} {resp.text}"
        )
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
                status: int = 2, teacher_comment: str = "Это итоговая оценка") -> Dict:
        """Проверка домашнего задания преподавателем."""
        url = f"{self.client.base_url}/homework/{homework_id}/answers/{answer_id}/examination"
        payload = {
            "data": {
                "attributes": {
                    "grade": grade,
                    "status": status,  # число, не строка
                    "deadline": "",
                    "teacher_comment": teacher_comment
                }
            }
        }
        resp = self.client.session.post(url, json=payload)
        assert resp.status_code == 200, f"Examination failed: {resp.status_code} {resp.text}"
        logger.info(f"Homework {homework_id} answer {answer_id} examined: status={status}")
        return resp.json()