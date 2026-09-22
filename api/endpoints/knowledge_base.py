from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status

class KnowledgeBaseEndpoint:
    """Методы для работы с материалами базы знаний."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create_material(self, payload: dict) -> Dict:
        """Создание материала (курса/файла/книги) в базе знаний."""
        resp = self.client.post("/knowledge-base/admin/materials", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Material created: ID={data['id']}, name={data.get('name')}")
        return data

    def toggle_visibility(self, material_id: int, is_visible: bool = False) -> Dict:
        """Переключение видимости материала."""
        payload = {"data": {"is_visible": is_visible}}
        resp = self.client.patch(
            f"/knowledge-base/admin/materials/{material_id}/toggle-visibility",
            json=payload
        )
        expect_status(resp, 200)
        data = resp.json().get("data", {})
        logger.info(f"Visibility for material {material_id} set to {is_visible}")
        return data

    def delete_materials(self, material_ids: list) -> bool:
        """Удаление материалов по списку ID."""
        payload = {
            "data": {
                "material_ids": material_ids
            }
        }
        resp = self.client.delete("/knowledge-base/admin/materials", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Materials deleted: {material_ids}")
        else:
            logger.warning(f"Delete materials failed: {resp.status_code} {resp.text[:200]}")
        return success

    def delete(self, material_id: int) -> bool:
        """Удаление одного материала."""
        return self.delete_materials([material_id])

    def list_tags(self) -> list:
        """Список тегов базы знаний."""
        resp = self.client.get("/knowledge-base/admin/tags")
        expect_status(resp, 200)
        return resp.json()["data"]["tags"]