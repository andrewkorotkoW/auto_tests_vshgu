from typing import Dict, Optional

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger


class TicketsEndpoint:
    """Методы для работы с обращениями в техподдержку (/api/v1/tickets/*)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание обращения. Ответ — {"message": "Ok"}, без ID созданного тикета
        (см. find_by_title и отчёт разведки)."""
        resp = self.client.post("/tickets", json=payload)
        expect_status(resp, (200, 201))
        logger.info(f"Ticket create requested: title={payload.get('title')}")
        return resp.json()

    def my_tickets(self) -> list:
        """Обращения текущего пользователя (первая страница списка, per_page=25)."""
        resp = self.client.get("/tickets/my-tickets")
        expect_status(resp, 200)
        return resp.json()["data"]

    def _my_tickets_page(self, page: int) -> list:
        resp = self.client.get(f"/tickets/my-tickets?page={page}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def find_by_title(self, title: str) -> Optional[Dict]:
        """POST /tickets не возвращает ID — созданный тикет находят по теме в my-tickets.

        Список пагинирован (per_page=25, сортировка по возрастанию created_at; параметры
        sort=-created_at/-id/order=desc сервером игнорируются — проверено разведкой), поэтому
        на аккаунте с историей больше одной страницы обращений (обычное дело для общего
        тестового аккаунта develop) только что созданный тикет почти всегда попадает на
        последнюю страницу. Листаем страницы от последней к первой, а не только первую
        страницу, как раньше, — иначе find_by_title перестаёт находить свежие тикеты."""
        resp = self.client.get("/tickets/my-tickets")
        expect_status(resp, 200)
        body = resp.json()
        last_page = body.get("meta", {}).get("last_page", 1)

        for page in range(last_page, 0, -1):
            data = body["data"] if page == 1 else self._my_tickets_page(page)
            for ticket in data:
                if ticket.get("title") == title:
                    return ticket
        return None

    def get_messages(self, ticket_id: int) -> list:
        """Переписка по обращению."""
        resp = self.client.get(f"/tickets/{ticket_id}/messages")
        expect_status(resp, 200)
        return resp.json()["data"]

    def add_message(self, ticket_id: int, text: str) -> Dict:
        """Добавление сообщения в переписку обращения."""
        resp = self.client.post(f"/tickets/{ticket_id}/messages", json={"text": text})
        expect_status(resp, 200)
        return resp.json()

    def close(self, ticket_id: int) -> Dict:
        """Закрытие обращения."""
        resp = self.client.put(f"/tickets/{ticket_id}/close")
        expect_status(resp, 200)
        return resp.json()
