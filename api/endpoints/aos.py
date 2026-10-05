from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class AosEndpoint:
    """Методы для работы с АОС (тесты)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание АОС."""
        resp = self.client.post("/tests", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"AOS created: ID={data.get('content_id')}, name={data.get('name')}")
        return data

    def get(self, aos_id: int) -> Dict:
        """Получение АОС по ID."""
        resp = self.client.get(f"/tests/{aos_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def activate(self, program_id: int, stream_id: int, aos_id: int) -> bool:
        """Активация/деактивация АОС."""
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/feedback/{aos_id}/change-active",
            json={}
        )
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"AOS activated: ID={aos_id}")
        else:
            logger.warning(f"AOS activate failed: ID={aos_id}, status={resp.status_code}")
        return success

    def stream_feedback(self, program_id: int, stream_id: int) -> list:
        """Список АОС потока с публичными ссылками (после активации у записи появляется launch_url)."""
        resp = self.client.get(f"/programs/{program_id}/streams/{stream_id}/feedback")
        expect_status(resp, 200)
        data = resp.json().get("data", [])
        return data if isinstance(data, list) else [data]

    def public_link(self, program_id: int, stream_id: int, aos_id: int) -> str:
        """Публичная ссылка на АОС: /testing/player?stream_feedback_content=<id записи АОС потока>.
        Это не content_id самой АОС — id выдаёт бэкенд после активации на потоке."""
        for item in self.stream_feedback(program_id, stream_id):
            attrs = item.get("attributes", item)
            if str(attrs.get("content_id") or attrs.get("test_id") or item.get("id")) == str(aos_id) and attrs.get("launch_url"):
                return attrs["launch_url"]
        links = [it.get("attributes", it).get("launch_url") for it in self.stream_feedback(program_id, stream_id)]
        links = [l for l in links if l]
        assert links, f"У АОС {aos_id} на потоке {stream_id} нет launch_url — активирована ли она?"
        return links[0]

    def mass_delete(self, content_ids: list) -> bool:
        """Массовое удаление АОС.

        АОС (type=feedback) хранится в модели TestContent, а не Activity —
        /activities/mass-delete отдаёт 404 «No query results for model ... Activity»,
        рабочий эндпоинт тот же, что и у тестов/опросов: DELETE /tests с contents_ids
        (см. TestsEndpoint.mass_delete/PollsEndpoint.mass_delete).
        """
        payload = {"contents_ids": content_ids}
        resp = self.client.delete("/tests", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"AOS mass deleted: {content_ids}")
        else:
            logger.warning(f"AOS mass delete failed: {resp.status_code} {resp.text[:200]}")
        return success
