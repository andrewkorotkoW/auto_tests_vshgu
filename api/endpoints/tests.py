from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class TestsEndpoint:
    """Методы для работы с тестами (type=test)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание теста. Возвращает данные созданного теста."""
        resp = self.client.post("/tests", json=payload)
        assert resp.status_code in (200, 201), (
            f"Test create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        data["id"] = data["content_id"]
        logger.info(f"Test created: ID={data['id']}, name={data.get('name')}")
        return data

    def get(self, test_id: int) -> Dict:
        """Получение теста по ID."""
        resp = self.client.get(f"/tests/{test_id}")
        assert resp.status_code == 200, f"Get test failed: {resp.status_code}"
        return resp.json()["data"]

    def update(self, test_id: int, payload: dict) -> Dict:
        """Обновление теста (PUT). Возвращает обновлённые данные."""
        resp = self.client.put(f"/tests/{test_id}", json=payload)
        assert resp.status_code in (200, 201), (
            f"Test update failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        data["id"] = data.get("content_id", test_id)
        logger.info(f"Test updated: ID={data['id']}, name={data.get('name')}")
        return data

    def delete(self, test_id: int) -> bool:
        """Удаление одного теста по content_id."""
        return self.mass_delete([test_id])

    def mass_delete(self, content_ids: list) -> bool:
        """Массовое удаление тестов через DELETE /tests."""
        payload = {"contents_ids": content_ids}
        resp = self.client.delete("/tests", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Tests deleted: {content_ids}")
        else:
            logger.warning(f"Tests delete failed: {resp.status_code} {resp.text[:200]}")
        return success

    def create_question(self, content_id: int, question: dict) -> Dict:
        """Создание вопроса для теста (PUT)."""
        payload = {
            "content_id": content_id,
            "question": question
        }
        resp = self.client.put("/tests/questions/store", json=payload)
        assert resp.status_code in (200, 201), (
            f"Question create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()
        logger.info(f"Question created for test {content_id}")
        return data