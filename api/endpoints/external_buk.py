"""Входящий REST интеграции БУК → АСУО: /api/v1/external/buk/users.

Контракт (asuo-buk-api-contracts): POST — первичный приём пользователей на синхронизацию,
PUT — повторная передача/уточнение, DELETE — разрыв связи. Все три принимают
{"users": [...]} и отвечают HTTP 200 с поэлементным результатом
{"buk_user_id", "success", "user" | "error"}. Сопоставление асинхронное: сразу после
POST статус recorded, итог (synced/synced_manual/pending/conflict/rejected) появляется
через несколько секунд.
"""
import time
from typing import Dict, List, Optional

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger

SYNC_TERMINAL = {"synced", "synced_manual", "pending", "conflict", "rejected", "unsynced"}


class ExternalBukEndpoint:
    PATH = "/external/buk/users"

    def __init__(self, client: ApiClient):
        self.client = client

    # --- сырые вызовы: возвращают список элементов результата -----------------------------
    def post_users(self, users: List[dict]) -> List[Dict]:
        resp = self.client.post(self.PATH, json={"users": users})
        expect_status(resp, 200)
        return resp.json()["users"]

    def put_users(self, users: List[dict]) -> List[Dict]:
        resp = self.client.put(self.PATH, json={"users": users})
        expect_status(resp, 200)
        return resp.json()["users"]

    def delete_users(self, buk_user_ids: List[str]) -> List[Dict]:
        resp = self.client.delete(self.PATH, json={"users": [{"buk_user_id": b} for b in buk_user_ids]})
        expect_status(resp, 200)
        return resp.json()["users"]

    # --- удобные обёртки для одного пользователя ---------------------------------------
    def post_user(self, user: dict) -> Dict:
        return self.post_users([user])[0]

    def put_user(self, user: dict) -> Dict:
        return self.put_users([user])[0]

    def delete_user(self, buk_user_id: str) -> Dict:
        return self.delete_users([buk_user_id])[0]

    def wait_for_match(self, user: dict, timeout: float = 40.0, delay: float = 6.0,
                       stale_status: Optional[str] = None) -> Dict:
        """Дождаться итога асинхронного сопоставления после POST/PUT/DELETE.

        GET в контракте нет, поэтому состояние читаем повторным PUT с тем же телом.
        Важно: ответ на PUT отражает состояние ДО обработки этого PUT (сопоставление
        асинхронное), поэтому первый опрос идёт после паузы, а «recorded» считаем
        незавершённым состоянием и опрашиваем дальше.
        """
        deadline = time.monotonic() + timeout
        result: Optional[Dict] = None
        while time.monotonic() < deadline:
            time.sleep(delay)
            result = self.put_user(user)
            status = (result.get("user") or {}).get("sync_status")
            logger.info(f"BUK {user.get('buk_user_id')}: sync_status={status}")
            if not result.get("success"):
                return result
            if status in SYNC_TERMINAL and status != stale_status:
                return result
        return result

    def put_and_wait(self, user: dict, **kwargs) -> Dict:
        """PUT с новыми данными, затем дождаться результата повторного сопоставления.

        Сам ответ на PUT показывает прежнее состояние записи, итог появляется позже.
        """
        applied = self.put_user(user)
        if not applied.get("success"):
            return applied
        # Прежнее состояние (например, pending) может ещё пару опросов возвращаться как есть,
        # пока повторное сопоставление не отработало — ждём, пока статус не сменится.
        before = (applied.get("user") or {}).get("sync_status")
        return self.wait_for_match(user, stale_status=before, **kwargs)
