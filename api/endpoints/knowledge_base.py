import mimetypes
import time
from pathlib import Path
from typing import Dict, Optional

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

    def upload_material_file(self, file_path, content_type: Optional[str] = None) -> Dict:
        """Загрузка файла контента материала (аудио/видео/книга/файл) — /upload/material_files.
        Возвращает элемент data[0] (uuid + attributes) для поля files при создании материала."""
        file_path = Path(file_path)
        guessed_type = content_type or mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        with file_path.open("rb") as fh:
            resp = self.client.upload(
                "/upload/material_files",
                files={"files[0]": (file_path.name, fh, guessed_type)},
            )
        expect_status(resp, (200, 201))
        files = resp.json().get("data")
        if not isinstance(files, list) or not files or not files[0].get("uuid"):
            raise AssertionError(f"Ответ загрузки файла материала без uuid: {resp.text[:500]}")
        return files[0]

    def create_article_material(self, name: str, article_text: str, is_visible: bool = True,
                                 short_description: str = "", description: str = "") -> Dict:
        """Создание материала БЗ типа «Статья» — текст статьи передаётся напрямую (без файла)."""
        payload = {
            "data": {
                "id": None,
                "name": name,
                "short_description": short_description,
                "type": "article",
                "is_visible": is_visible,
                "description": description,
                "article_text": article_text,
                "cover_uuid": "",
                "duration": 0,
                "files": [],
                "authors": [{"name": "AQA", "avatar_url": "", "avatar_uuid": ""}],
                "bundles": [],
                "categories": [],
                "competencies": [],
                "tags": [],
                "professional_areas": [],
            }
        }
        return self.create_material(payload)

    def create_file_material(self, name: str, material_type: str, file_path, content_type: Optional[str] = None,
                              duration: int = 0, is_visible: bool = True,
                              short_description: str = "", description: str = "") -> Dict:
        """Создание материала БЗ с файлом контента (типы аудио/видео/книга/файл): сначала
        загружает файл через upload_material_file, затем создаёт материал с полученным uuid."""
        uploaded_file = self.upload_material_file(file_path, content_type=content_type)
        payload = {
            "data": {
                "id": None,
                "name": name,
                "short_description": short_description,
                "type": material_type,
                "is_visible": is_visible,
                "description": description,
                "article_text": "",
                "cover_uuid": "",
                "duration": duration,
                "files": [
                    {
                        "file_uuid": uploaded_file["uuid"],
                        "attributes": uploaded_file.get("attributes", {}),
                    }
                ],
                "authors": [],
                "bundles": [],
                "categories": [],
                "competencies": [],
                "tags": [],
                "professional_areas": [],
            }
        }
        return self.create_material(payload)

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

    @staticmethod
    def material_set_condition(material_id: int) -> dict:
        """Условие достижения «конкретный материал изучен» (в отличие от material_count,
        где считается количество материалов заданного типа)."""
        return {
            "type": "material_set",
            "entity_type": "knowledge_base_material",
            "entity_id": material_id,
        }

    def create_achievement_with_conditions(self, name: str, description: str, conditions: list,
                                            is_active: bool = True) -> Dict:
        """Достижение с произвольным списком условий — для составных достижений
        (несколько material_set условий, например «аудио + книга»)."""
        payload = {
            "name": name,
            "description": description,
            "is_active": is_active,
            "icon_uuid": self.get_default_achievement_icon_uuid(),
            "conditions": conditions,
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

    def wait_user_achievement(self, full_name: str, achievement_name: str,
                               timeout: int = 120, interval: int = 5) -> Dict:
        """Опрашивает историю полученных достижений (get_user_achievements), пока в ней не
        появится запись с нужным названием достижения — начисление происходит асинхронно."""
        deadline = time.monotonic() + timeout
        last_history: list = []
        while time.monotonic() < deadline:
            last_history = self.get_user_achievements(full_name)
            for user_achievement in last_history:
                if (user_achievement.get("achievement") or {}).get("name") == achievement_name:
                    return user_achievement
            time.sleep(interval)
        raise AssertionError(
            f"Достижение «{achievement_name}» не появилось в истории пользователя «{full_name}» "
            f"за {timeout}с. Последняя история: {last_history}"
        )

    # ── Прохождение материала слушателем, статистика ───────────────────────

    def launch_material_assignment(self, material_id: int) -> Dict:
        """POST — фиксирует начало изучения материала слушателем (клиент должен быть
        создан с пользовательской, не админской, сессией)."""
        resp = self.client.post(f"/knowledge-base/materials/{material_id}/assignment")
        expect_status(resp, (200, 201))
        return resp.json().get("data", {})

    def complete_material_assignment(self, material_id: int) -> Dict:
        """PUT — фиксирует завершение изучения материала слушателем."""
        resp = self.client.put(f"/knowledge-base/materials/{material_id}/assignment")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    def pass_material_via_api(self, material_id: int) -> None:
        """API fallback для завершения изучения материала — запуск + завершение назначения.
        Используется как подстраховка к UI-действию (дочитать/дослушать/досмотреть до конца),
        когда фиксация прогресса медиа в браузере ненадёжна (см. перенос coллеги)."""
        self.launch_material_assignment(material_id)
        self.complete_material_assignment(material_id)

    def get_material_statistics(self, full_name: str, per_page: int = 25, page: int = 1) -> list:
        """Статистика изученных материалов по пользователям («Рейтинг» в админке)."""
        endpoint = (
            f"/knowledge-base/admin/material-statistics?per-page={per_page}&page={page}"
            f"&filters[name]={full_name}"
        )
        resp = self.client.get(endpoint)
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def wait_material_statistics(self, full_name: str, expected: dict,
                                  timeout: int = 120, interval: int = 5) -> Dict:
        """Опрашивает get_material_statistics, пока значения полей из expected (например
        {"article": 1, "total": 1}) не совпадут — статистика обновляется асинхронно."""
        deadline = time.monotonic() + timeout
        last_statistics: list = []
        while time.monotonic() < deadline:
            last_statistics = self.get_material_statistics(full_name)
            for row in last_statistics:
                if all(int(row.get(key, 0)) == value for key, value in expected.items()):
                    return row
            time.sleep(interval)
        raise AssertionError(
            f"Статистика материалов пользователя «{full_name}» не обновилась до {expected} "
            f"за {timeout}с. Последняя статистика: {last_statistics}"
        )