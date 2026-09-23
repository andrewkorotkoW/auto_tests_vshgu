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

    def create_course_material(self, name: str, content_id: int, is_visible: bool = True,
                                short_description: str = "", description: str = "") -> Dict:
        """Создание материала БЗ типа «курс» — оборачивает уже созданную активность (content_id),
        в отличие от статьи/видео/аудио/книги/файла материал курса не несёт свой файл/текст."""
        payload = {
            "data": {
                "id": None,
                "name": name,
                "content_id": content_id,
                "short_description": short_description,
                "type": "course",
                "is_visible": is_visible,
                "description": description,
                "article_text": "",
                "cover_uuid": "",
                "duration": 0,
                "files": [],
                "authors": [],
                "bundles": [],
                "categories": [],
                "competencies": [],
                "tags": [],
                "professional_areas": [],
            }
        }
        return self.create_material(payload)

    # ── Достижения ──────────────────────────────────────────────────────

    def get_default_achievement_icon_uuid(self) -> str:
        """UUID стандартной иконки достижения (обязателен в payload создания)."""
        resp = self.client.get("/admin/achievements/achievement-default-icons")
        expect_status(resp, 200)
        icons = resp.json().get("data", [])
        if not icons or not icons[0].get("uuid"):
            raise AssertionError(f"Нет стандартных иконок достижений: {resp.text[:500]}")
        return icons[0]["uuid"]

    def create_achievement(self, payload: dict) -> Dict:
        """Создание достижения."""
        resp = self.client.post("/admin/achievements", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Achievement created: ID={data['id']}, name={data.get('name')}")
        return data

    def create_material_count_achievement(self, name: str, description: str, material_type: str,
                                           count: int = 1, is_active: bool = True) -> Dict:
        """Достижение с условием «количество изученных материалов заданного типа»."""
        payload = {
            "name": name,
            "description": description,
            "is_active": is_active,
            "icon_uuid": self.get_default_achievement_icon_uuid(),
            "conditions": [
                {
                    "type": "material_count",
                    "count": count,
                    "material_type": material_type,
                }
            ],
        }
        return self.create_achievement(payload)

    def list_achievements(self, name_filter: str = "", per_page: int = 25, page: int = 1) -> list:
        """Список достижений (админка), с опциональным фильтром по названию."""
        endpoint = f"/admin/achievements?per-page={per_page}&page={page}"
        if name_filter:
            endpoint += f"&filters[name]={name_filter}"
        resp = self.client.get(endpoint)
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def find_achievement_by_name(self, name: str) -> Dict | None:
        """Поиск достижения по точному названию среди отфильтрованного списка."""
        for achievement in self.list_achievements(name_filter=name):
            if achievement.get("name") == name:
                return achievement
        return None

    def get_user_achievements(self, full_name: str, per_page: int = 25, page: int = 1) -> list:
        """«Выдача»: история достижений, полученных пользователями (админка)."""
        endpoint = (
            f"/admin/achievements/users?per-page={per_page}&page={page}"
            f"&filters[full_name]={full_name}"
        )
        resp = self.client.get(endpoint)
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def delete_achievement(self, achievement_id: int) -> bool:
        """Удаление достижения по ID."""
        resp = self.client.delete(f"/admin/achievements/{achievement_id}")
        success = resp.status_code in (200, 202, 204)
        if success:
            logger.info(f"Achievement deleted: {achievement_id}")
        else:
            logger.warning(f"Delete achievement failed: {resp.status_code} {resp.text[:200]}")
        return success