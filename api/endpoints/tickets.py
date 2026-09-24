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
        """Обращения текущего пользователя."""
        resp = self.client.get("/tickets/my-tickets")
        expect_status(resp, 200)
        return resp.json()["data"]

    def find_by_title(self, title: str) -> Optional[Dict]:
        """POST /tickets не возвращает ID — созданный тикет находят по теме в my-tickets."""
        for ticket in self.my_tickets():
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
