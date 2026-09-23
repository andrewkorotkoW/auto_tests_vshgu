from typing import Dict, List, Optional
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class QuestionBankEndpoint:
    """Методы конструктора тестов/опросов: темы вопросов (каталог dictionaries,
    type=tag) и банк вопросов. Логически отдельны от тестов/опросов самих по себе
    (api/endpoints/tests.py, api/endpoints/polls.py), поэтому вынесены сюда."""

    def __init__(self, client: ApiClient):
        self.client = client

    # ── Темы вопросов (каталог) ─────────────────────────────────────────

    def create_theme(self, name: str) -> Dict:
        """Создание темы вопроса в каталоге."""
        resp = self.client.post("/dictionaries", json={"name": name, "type": "tag"})
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Question theme created: ID={data.get('id')}, name={data.get('name')}")
        return data

    def list_themes(self, name: str = "", per_page: int = 25, page: int = 1) -> List[Dict]:
        """Список тем вопросов, опционально отфильтрованный по имени."""
        endpoint = f"/dictionaries?per-page={per_page}&page={page}&filters[type]=tag"
        if name:
            endpoint += f"&filters[name]={name}"
        resp = self.client.get(endpoint)
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def find_theme_by_name(self, name: str) -> Optional[Dict]:
        """Поиск темы вопроса по точному совпадению имени."""
        for theme in self.list_themes(name=name):
            if theme.get("name") == name:
                return theme
        return None

    def delete_theme(self, theme_id: int) -> bool:
        """Удаление темы вопроса по ID."""
        resp = self.client.delete(f"/dictionaries/{theme_id}")
        success = resp.status_code in (200, 202, 204)
        if success:
            logger.info(f"Question theme deleted: ID={theme_id}")
        else:
            logger.warning(f"Question theme delete failed: {resp.status_code} {resp.text[:200]}")
        return success

    # ── Банк вопросов ────────────────────────────────────────────────────

    def add_question_to_bank(self, question_id: int, entity_type: str = "test", parent_id: int = None) -> int:
        """Добавление вопроса теста/опроса (question_id из TestsEndpoint.create_question/
        PollsEndpoint.create_question) в банк вопросов. entity_type: test | poll.
        Возвращает questions_bank_id — им же и удаляется (delete_bank_questions)."""
        resp = self.client.post(
            "/questions-bank/add",
            json={"question_ids": [question_id], "parent_id": parent_id, "entity_type": entity_type},
        )
        expect_status(resp, (200, 201))
        questions = resp.json().get("data", [])
        question = questions[0] if questions else {}
        bank_question_id = question.get("questions_bank_id")
        if not bank_question_id:
            raise AssertionError(
                f"В ответе добавления вопроса в банк отсутствует questions_bank_id: {resp.json()}"
            )
        logger.info(f"Question added to bank: question_id={question_id}, bank_id={bank_question_id}")
        return int(bank_question_id)

    def delete_bank_questions(self, question_bank_ids: list) -> bool:
        """Массовое удаление вопросов из банка вопросов."""
        resp = self.client.post("/questions-bank/delete", json={"ids": question_bank_ids})
        success = resp.status_code in (200, 202, 204)
        if success:
            logger.info(f"Bank questions deleted: {question_bank_ids}")
        else:
            logger.warning(f"Bank questions delete failed: {resp.status_code} {resp.text[:200]}")
        return success
