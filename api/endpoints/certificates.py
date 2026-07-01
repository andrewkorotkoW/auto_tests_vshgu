from typing import Dict
from api.client import ApiClient
from utils.logger import logger

class CertificatesEndpoint:
    """Методы для работы с шаблонами сертификатов."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create_template(self, payload: dict) -> Dict:
        """Создание шаблона сертификата."""
        resp = self.client.post("/certificates/templates/create", json=payload)
        assert resp.status_code in (200, 201), (
            f"Template create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        # Сервер возвращает template_id, а не id
        data["id"] = data["template_id"]
        logger.info(f"Template created: ID={data['id']}, name={data.get('name')}")
        return data

    def delete_templates(self, template_ids: list) -> bool:
        """Удаление шаблонов сертификатов по списку ID."""
        payload = {"template_ids": template_ids}
        resp = self.client.post("/certificates/templates/delete", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Templates deleted: {template_ids}")
        else:
            logger.warning(f"Templates delete failed: {resp.status_code} {resp.text[:200]}")
        return success

    def assign_template(self, template_id: int, content_ids: list, show_certificate: bool = True,
                        notify: bool = True) -> Dict:
        """Назначение шаблона сертификата на контент."""
        payload = {
            "template_id": template_id,
            "meta": {
                "showCertificate": show_certificate,
                "notify": notify
            },
            "content_ids": content_ids
        }
        resp = self.client.post("/certificates/template/assign", json=payload)
        assert resp.status_code in (200, 201), f"Assign template failed: {resp.status_code} {resp.text}"
        data = resp.json()
        logger.info(f"Template {template_id} assigned to content {content_ids}")
        return data