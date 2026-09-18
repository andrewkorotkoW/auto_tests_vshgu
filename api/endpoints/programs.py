from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class ProgramsEndpoint:
    """Методы для работы с программами."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание программы. Возвращает данные созданной программы."""
        resp = self.client.post("/programs", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Program created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def get(self, program_id: int) -> Dict:
        """Получение программы по ID."""
        resp = self.client.get(f"/programs/{program_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def delete(self, program_id: int) -> bool:
        """Удаление программы."""
        resp = self.client.delete(f"/programs/{program_id}")
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Program deleted: ID={program_id}")
        else:
            logger.warning(f"Program delete failed: ID={program_id}, status={resp.status_code}")
        return success

    def mass_delete(self, program_ids: list) -> bool:
        """Массовое удаление программ."""
        payload = {
            "data": {
                "attributes": {
                    "programs_ids": program_ids
                }
            }
        }
        resp = self.client.delete("/programs/mass-delete", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Programs mass deleted: IDs={program_ids}")
        else:
            logger.warning(f"Mass delete failed: status={resp.status_code}, {resp.text[:200]}")
        return success
