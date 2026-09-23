from typing import Dict, List, Optional
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class TestsEndpoint:
    """Методы для работы с тестами (type=test)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание теста. Возвращает данные созданного теста."""
        resp = self.client.post("/tests", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        data["id"] = data["content_id"]
        logger.info(f"Test created: ID={data['id']}, name={data.get('name')}")
        return data

    def get(self, test_id: int) -> Dict:
        """Получение теста по ID."""
        resp = self.client.get(f"/tests/{test_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def update(self, test_id: int, payload: dict) -> Dict:
        """Обновление теста (PUT). Возвращает обновлённые данные."""
        resp = self.client.put(f"/tests/{test_id}", json=payload)
        expect_status(resp, (200, 201))
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
        expect_status(resp, (200, 201))
        data = resp.json()
        logger.info(f"Question created for test {content_id}")
        return data

    def get_questions(self, content_id: int) -> List[Dict]:
        """Список вопросов теста (для конструктора: найти дефолтный вопрос/группу
        перед добавлением доп. вопросов или вопроса из банка)."""
        resp = self.client.get(f"/tests/questions/{content_id}")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def list(self, name_filter: str = "", per_page: int = 25, page: int = 1) -> List[Dict]:
        """Список тестов/опросов конструктора (GET /tests). Поиск по имени в UI таблицы
        конструктора не работает (известный баг стенда) — искать тест по ID или через
        этот метод/find_by_name."""
        endpoint = f"/tests?per-page={per_page}&page={page}"
        if name_filter:
            endpoint += f"&filters[name]={name_filter}"
        resp = self.client.get(endpoint)
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def find_by_name(self, name: str) -> Optional[Dict]:
        """Поиск теста/опроса по точному совпадению имени среди отфильтрованного списка."""
        for item in self.list(name_filter=name):
            if item.get("name") == name:
                return item
        return None

    def set_extra_questions_active(self, test_data: dict, is_active: bool) -> Dict:
        """Включение/выключение дополнительных вопросов (settings.extra_questions.is_active)
        через PUT /tests/{id} — принимает «сырые» данные теста (TestsEndpoint.create/get:
        content_id, type, name, name_client, topic, cover_uuid, description, settings)."""
        settings = dict(test_data.get("settings") or {})
        settings["extra_questions"] = {"is_active": is_active}
        if is_active:
            settings["shuffle_questions"] = {"is_active": False}
        content_id = test_data.get("content_id", test_data.get("id"))
        payload = {
            "content_id": content_id,
            "type": test_data.get("type", "test"),
            "name": test_data["name"],
            "name_client": test_data.get("name_client", test_data["name"]),
            "topic": test_data.get("topic") or "",
            "cover_uuid": test_data.get("cover_uuid"),
            "description": test_data.get("description") or "",
            "settings": settings,
        }
        return self.update(content_id, payload)