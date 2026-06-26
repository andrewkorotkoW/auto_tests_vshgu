from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class UsersEndpoint:
    """Методы для работы с пользователями."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание пользователя. Возвращает данные созданного пользователя."""
        resp = self.client.post("/users", json=payload)
        assert resp.status_code in (200, 201), (
            f"User create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        logger.info(f"User created: ID={data['id']}, email={data['attributes'].get('email')}")
        return data

    def get(self, user_id: int) -> Dict:
        """Получение пользователя по ID."""
        resp = self.client.get(f"/users/{user_id}")
        assert resp.status_code == 200, f"Get user failed: {resp.status_code}"
        return resp.json()["data"]

    def delete(self, user_id: int) -> bool:
        """Удаление пользователя."""
        resp = self.client.delete(f"/users/{user_id}")
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"User deleted: ID={user_id}")
        else:
            logger.warning(f"User delete failed: ID={user_id}, status={resp.status_code}")
        return success

    def get_users(self, params: dict = None) -> list:
        """Получить список пользователей, фильтруя локально."""
        resp = self.client.get("/users")
        assert resp.status_code == 200, f"Get users failed: {resp.status_code}"
        users = resp.json().get("data", [])
        if params:
            # пример локальной фильтрации
            role = params.get("role")
            surname_endswith = params.get("filter[surname]", "").rstrip("*")
            if role:
                users = [u for u in users if u.get("attributes", {}).get("role") == role]
            if surname_endswith:
                users = [u for u in users if u.get("attributes", {}).get("surname", "").endswith(surname_endswith)]
        logger.info(f"Found {len(users)} users after filtering")
        return users

