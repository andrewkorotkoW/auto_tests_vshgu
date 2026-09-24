import os
from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class TincanEndpoint:
    """Методы для работы с курсами Tincan."""

    def __init__(self, client: ApiClient):
        self.client = client

    def upload_cover(self, file_path: str = "test_data/cover.jpg") -> str:
        """Загрузка обложки через ту же авторизованную сессию, что и остальные запросы
        (раньше — внешний curl с кукой по имени «develop», что ломалось на любом стенде
        с другим именем куки). Возвращает uuid файла или пустую строку."""
        with open(file_path, "rb") as f:
            resp = self.client.session.post(
                f"{self.client.base_url}/upload/cover",
                files={"cover": (os.path.basename(file_path), f, "image/jpeg")},
                # Content-Type: None снимает session-заголовок application/json — иначе multipart не уходит
                headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest", "Content-Type": None},
                timeout=60,
            )
        if resp.status_code not in (200, 201):
            logger.warning(f"upload_cover failed: {resp.status_code} {resp.text[:200]}")
            return ""
        data = resp.json().get("data", {})
        if isinstance(data, list):
            return data[0].get("uuid", "") if data else ""
        return data.get("uuid", "")

    def upload_archive(self, file_path: str = "test_data/course_tincan.zip") -> str:
        import subprocess, os
        cookie_header = self.client.session.headers.get("Cookie", "")
        if not cookie_header:
            cookie_header = f"develop={self.client.session.cookies.get('develop')}"
        base = self.client.base_url
        result = subprocess.run([
            "curl", "-s",
            f"{base}/upload/course_archive",
            "-H", "Accept: application/json",
            "-H", "X-Requested-With: XMLHttpRequest",
            "-b", cookie_header,
            "-F", f"files[0]=@{file_path};type=application/zip",
            "-F", "type=course-tincan"
        ], capture_output=True, text=True)
        resp_json = __import__('json').loads(result.stdout)
        data = resp_json.get("data", {})
        if isinstance(data, list):
            return data[0].get("uuid", "") if data else ""
        return data.get("uuid", "")

    def upload_sub_file(self, file_path: str = "test_data/sub_files.jpg") -> str:
        import subprocess, os
        cookie_header = self.client.session.headers.get("Cookie", "")
        if not cookie_header:
            cookie_header = f"develop={self.client.session.cookies.get('develop')}"
        base = self.client.base_url
        result = subprocess.run([
            "curl", "-s",
            f"{base}/upload/schedule_item_files",
            "-H", "Accept: application/json",
            "-H", "X-Requested-With: XMLHttpRequest",
            "-b", cookie_header,
            "-F", f"files[0]=@{file_path};type=image/jpeg"
        ], capture_output=True, text=True)
        resp_json = __import__('json').loads(result.stdout)
        data = resp_json.get("data", {})
        if isinstance(data, list):
            return data[0].get("uuid", "") if data else ""
        return data.get("uuid", "")

    def mass_delete(self, content_ids: list) -> bool:
        """Массовое удаление курсов."""
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
            logger.info(f"Tincan mass deleted: {content_ids}")
        else:
            logger.warning(f"Tincan mass delete failed: {resp.status_code}")
        return success

    def delete(self, content_id: int) -> bool:
        """Удаление одного курса Tincan."""
        return self.mass_delete([content_id])

    def assign_to_module(self, program_id: int, stream_id: int, module_id: int, content_ids: list) -> bool:
        """Назначение курса в модуль."""
        payload = {
            "data": {
                "attributes": {
                    "content_ids": content_ids,
                    "stream_module_id": module_id
                }
            }
        }
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/mass-addition",
            json=payload
        )
        success = resp.status_code in (200, 201)
        if success:
            logger.info(f"Course assigned to module {module_id}: {content_ids}")
        else:
            logger.warning(f"Course assign failed: {resp.status_code}")
        return success

    def assign_users(self, module_id: int, content_id: int, stream_id: int, user_ids: list) -> bool:
        """Назначение пользователей на курс."""
        resp = self.client.post(
            f"/modules/{module_id}/contents/{content_id}/lpd/assignment?stream={stream_id}",
            json={"users": user_ids}
        )
        success = resp.status_code in (200, 201)
        if success:
            logger.info(f"Users {user_ids} assigned to course {content_id}")
        else:
            logger.warning(f"Course user assign failed: {resp.status_code}")
        return success

    def create(self, payload: dict) -> Dict:
        """Создание курса Tincan."""
        resp = self.client.post("/content", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Tincan created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def assign_activities(self, content_ids: list, user_ids: list) -> bool:
        payload = {
            "data": {"attributes": {"content_ids": content_ids, "user_ids": user_ids}}
        }
        resp = self.client.post("/users/content/distant/assign-activities", json=payload)
        success = resp.status_code in (200, 201)
        if success:
            logger.info(f"Activities {content_ids} assigned to users {user_ids}")
        else:
            logger.warning(f"Assign activities failed: {resp.status_code}")
        return success

    def upload_certificate_file(self, file_path: str = "test_data/certificat.pdf") -> str:
        """Загрузка PDF-файла для сертификата. Возвращает UUID."""
        import subprocess
        cookie_header = self.client.session.headers.get("Cookie", "")
        if not cookie_header:
            cookie_header = f"develop={self.client.session.cookies.get('develop')}"
        base = self.client.base_url
        result = subprocess.run([
            "curl", "-s",
            f"{base}/upload/certificate_template",
            "-H", "Accept: application/json",
            "-H", "X-Requested-With: XMLHttpRequest",
            "-b", cookie_header,
            "-F", f"file=@{file_path};type=application/pdf"
        ], capture_output=True, text=True)
        resp_json = __import__('json').loads(result.stdout)
        data = resp_json.get("data", {})
        if isinstance(data, list):
            return data[0].get("uuid", "") if data else ""
        return data.get("uuid", "")

