from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class ExternalCasEndpoint:
    """Методы для работы с внешним CAS API."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create_program(self, payload: dict) -> Dict:
        resp = self.client.post("/external/cas/programs", json=payload)
        assert resp.status_code in (200, 201), (
            f"External CAS create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CREATE PROGRAM RAW RESPONSE: {data}")  # ← добавить
        logger.info(f"External CAS program created: {data}")
        return data

    def delete_program(self, program_id: int) -> bool:
        """Удаление программы CAS."""
        resp = self.client.delete(f"/external/cas/sync/programs/{program_id}")
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"External CAS program deleted: ID={program_id}")
        else:
            logger.warning(f"External CAS program delete failed: {resp.status_code} - {resp.text[:200]}")
        return success

    def create_stream(self, program_id: int, payload: dict) -> Dict:
        """Создание потока для программы CAS."""
        resp = self.client.post(f"/external/cas/programs/{program_id}/streams", json=payload)
        assert resp.status_code in (200, 201), (
            f"External CAS stream create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"External CAS stream created: {data}")
        return data

    def delete_stream(self, program_id: int, stream_id: int) -> bool:
        """Удаление потока программы CAS."""
        resp = self.client.delete(f"/external/cas/sync/programs/{program_id}/streams/{stream_id}")
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"External CAS stream deleted: program={program_id}, stream={stream_id}")
        else:
            logger.warning(f"External CAS stream delete failed: {resp.status_code} - {resp.text[:200]}")
        return success

    def create_user(self, payload: dict) -> Dict:
        """Создание пользователя через внешний CAS."""
        resp = self.client.post("/external/cas/users", json=payload)
        assert resp.status_code in (200, 201), (
            f"External CAS user create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"External CAS user created: {data}")
        return data

    def delete_user(self, user_id: int) -> bool:
        """Удаление синхронизации пользователя CAS."""
        resp = self.client.delete(f"/external/cas/sync/users/{user_id}")
        if resp.status_code == 400 and "не доступно" in resp.text:
            logger.info(f"CAS user sync already removed: user_id={user_id}")
            return True
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"External CAS user sync deleted: user_id={user_id}")
        else:
            logger.warning(f"External CAS user delete failed: {resp.status_code} - {resp.text[:200]}")
        return success

    def sync_user(self, user_id: int, payload: dict = None) -> Dict:
        """Синхронизация пользователя с CAS."""
        if payload is None:
            payload = {}
        resp = self.client.post(f"/external/cas/sync/users/{user_id}", json=payload)
        assert resp.status_code in (200, 201), (
            f"CAS user sync failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS user synced: user_id={user_id}")
        return data

    def sync_users_bulk(self, users: list) -> Dict:
        """Массовая синхронизация пользователей."""
        resp = self.client.post("/external/cas/sync/users", json=users)
        assert resp.status_code in (200, 201), (
            f"CAS bulk sync failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS bulk sync completed: {len(users)} users")
        return data

    def sync_stream(self, program_id: int, stream_id: int) -> Dict:
        resp = self.client.post(f"/external/cas/sync/programs/{program_id}/streams/{stream_id}")
        if resp.status_code == 400:
            if "должен быть не синхронизирован" in resp.text or "не синхронизирован" in resp.text:
                logger.info(f"CAS stream already synced or disabled: stream={stream_id}")
                return resp.json()
        assert resp.status_code in (200, 201), (
            f"CAS stream sync failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS stream synced: program={program_id}, stream={stream_id}")
        return data

    def update_stream(self, program_id: int, stream_id: int, date_from: str, date_to: str) -> Dict:
        """Обновление потока CAS."""
        payload = {"date_from": date_from, "date_to": date_to}
        resp = self.client.put(
            f"/external/cas/programs/{program_id}/streams/{stream_id}",
            json=payload
        )
        assert resp.status_code in (200, 201), (
            f"CAS stream update failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS stream updated: program={program_id}, stream={stream_id}")
        return data

    def export_assignments(self, cas_application_uids: list, stream_id: int) -> Dict:
        payload = {"cas_application_uids": cas_application_uids, "stream_id": stream_id}
        resp = self.client.post("/external/cas/assignments/export", json=payload)
        logger.info(f"Export response: status={resp.status_code}, body={resp.text[:300]}")
        if resp.status_code == 422 and (
                "формируется" in resp.text or "\\u0444\\u043e\\u0440\\u043c\\u0438" in resp.text):
            logger.info(f"Export already in progress for stream={stream_id}")
            return resp.json()
        assert resp.status_code in (200, 201), (
            f"CAS export assignments failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS assignments exported: stream={stream_id}")
        return data

    def assign_users(self, stream_id: int, user_ids: list, status: str = "enlisted",
                     enlisted_text: str = "Зачислен по причине автотеста",
                     enlisted_link: str = "https://autotest.com",
                     dismissed_text: str = None,
                     dismissed_link: str = None) -> Dict:
        import time
        # Генерируем уникальный cas_application_uid для каждого пользователя
        for user in user_ids:
            if "cas_application_uid" not in user:
                user["cas_application_uid"] = f"auto-{int(time.time())}-{user['user_id']}"

        payload = {
            "user_ids": user_ids,
            "stream_id": stream_id,
            "status": status
        }
        if status == "enlisted":
            payload["enlisted_text"] = enlisted_text
            payload["enlisted_link"] = enlisted_link
        elif status == "dismissed":
            payload["dismissed_text"] = dismissed_text or "Отчислен по причине автотеста"
            payload["dismissed_link"] = dismissed_link or "https://autotest.com"

        resp = self.client.post("/external/cas/assignments", json=payload)
        assert resp.status_code in (200, 201), (
            f"CAS assign failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS users assigned to stream {stream_id}: {len(user_ids)} users, status={status}")
        return data

    def update_user(self, user_id: int, payload: dict) -> Dict:
        resp = self.client.put(f"/external/cas/users/{user_id}", json=payload)
        assert resp.status_code in (200, 201), (
            f"CAS user update failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS user updated: user_id={user_id}")
        return data

    def sync_program(self, program_id: int) -> Dict:
        resp = self.client.post(f"/external/cas/sync/programs/{program_id}")
        assert resp.status_code in (200, 201), (
            f"CAS program sync failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS program synced: program_id={program_id}")
        return data

    def correct_sync(self, program_id: int, stream_id: int, source_program_id: int, source_stream_id: int) -> Dict:
        """Корректировка синхронизации потока."""
        payload = {
            "source_program_id": source_program_id,
            "source_stream_id": source_stream_id
        }
        resp = self.client.post(
            f"/external/cas/sync/programs/{program_id}/streams/{stream_id}/correction",
            json=payload
        )
        assert resp.status_code in (200, 201), (
            f"CAS correction failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS correction done: program={program_id}, stream={stream_id}")
        return data

    def dismiss_assignments(self, stream_id: int, user_ids: list) -> Dict:
        """Снятие назначений с потока."""
        payload = {"stream_id": stream_id, "user_ids": user_ids}
        resp = self.client.delete("/external/cas/assignments", json=payload)
        assert resp.status_code in (200, 204), (
            f"CAS dismiss failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS assignments dismissed: stream={stream_id}, users={user_ids}")
        return data