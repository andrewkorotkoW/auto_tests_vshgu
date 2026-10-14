from typing import Dict, List

from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class ExportsEndpoint:
    """Методы для работы со списком «Отчётов» LMS (GET /exports) — в т.ч. отчётов LRS
    (type 14, имя файла lrs_statement_export_*), см. docs/lrs/lrs_recon.md раздел «Отчёты»."""

    def __init__(self, client: ApiClient):
        self.client = client

    def list_exports(self, page: int = None, per_page: int = None, type: int = None) -> List[Dict]:
        """Постраничный список отчётов, опционально отфильтрованный по типу.
        ApiClient.get не принимает params — query-строка собирается вручную,
        как в api/endpoints/dictionaries.py."""
        query = []
        if page is not None:
            query.append(f"page={page}")
        if per_page is not None:
            query.append(f"per_page={per_page}")
        if type is not None:
            query.append(f"type={type}")
        endpoint = "/exports" + ("?" + "&".join(query) if query else "")
        resp = self.client.get(endpoint)
        expect_status(resp, 200)
        data = resp.json()
        return data.get("data", data)

    def find_lrs_export(self, name_prefix: str = "lrs_statement_export_") -> List[Dict]:
        """Отчёты LRS (type 14) с именем файла, начинающимся с name_prefix — для поиска
        только что созданного тестом отчёта среди возможных старых записей."""
        exports = self.list_exports(type=14)
        return [item for item in exports if str(item.get("name", "")).startswith(name_prefix)]

    def mass_delete(self, export_ids: list) -> bool:
        """Массовое удаление отчётов (DELETE /exports/mass-delete)."""
        if not export_ids:
            return True
        payload = {
            "data": {
                "attributes": {
                    "export_ids": export_ids
                }
            }
        }
        resp = self.client.delete("/exports/mass-delete", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Exports mass deleted: IDs={export_ids}")
        else:
            logger.warning(f"Exports mass delete failed: status={resp.status_code}, {resp.text[:200]}")
        return success
