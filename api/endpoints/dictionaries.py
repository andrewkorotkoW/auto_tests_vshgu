from typing import Dict, List, Optional

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger


class DictionariesEndpoint:
    """Методы для работы со справочниками (/api/v1/dictionaries/*) — общий REST-ресурс
    на все типы (поле `type`, backing enum Dictionaries\\Enums\\DictionaryType на
    бэкенде). В админке есть раздел «Справочники» с CRUD-страницами для части типов
    (program_type/learning_format/program_department/region/municipality/tag, см.
    ui/pages/admin_dictionaries_page.py и уточнение в docs/plans/2026-09-25_dictionaries_mission.md);
    project/program_level своей страницы не имеют — только через этот API. Известные по
    разведке типы и где они используются как поля форм:
      - project, program_level, program_department, program_type, learning_format —
        обязательные селекты формы создания потока программы (/admin/programs/{id}/streams/create:
        «Проект», «Стоимостная группа», «Подразделение реализации», «Вид программы»,
        «Форма реализации»), см. generate_stream_payload;
      - region, municipality — поля region_id/municipality_id формы пользователя,
        см. generate_user_payload (только для чтения на develop — тестами не создавались);
      - tag — темы вопросов конструктора тестов/опросов, уже покрыт отдельным
        QuestionBankEndpoint (api/endpoints/question_bank.py) с тем же /dictionaries.
    """

    def __init__(self, client: ApiClient):
        self.client = client

    def list_by_type(self, dictionary_type: str) -> List[Dict]:
        """Полный отсортированный список элементов справочника по типу — тот же запрос,
        которым админка подгружает опции выпадающего списка при открытии формы
        (GET /dictionaries/by-type/{type}), без серверной пагинации."""
        resp = self.client.get(
            f"/dictionaries/by-type/{dictionary_type}"
            "?sort[0][name]=dictionary.name&sort[0][direction]=asc"
        )
        expect_status(resp, 200)
        return resp.json()["data"]

    def list(self, dictionary_type: str = None, name: str = None, per_page: int = 25, page: int = 1) -> List[Dict]:
        """Постраничный список справочника (GET /dictionaries), опционально
        отфильтрованный по типу и/или точному имени."""
        endpoint = f"/dictionaries?per-page={per_page}&page={page}"
        if dictionary_type:
            endpoint += f"&filters[type]={dictionary_type}"
        if name:
            endpoint += f"&filters[name]={name}"
        resp = self.client.get(endpoint)
        expect_status(resp, 200)
        return resp.json()["data"]

    def create(self, name: str, dictionary_type: str) -> Dict:
        """Создание элемента справочника. Без `type` бэкенд отвечает 500 вместо
        ожидаемой валидационной 422 (см. отчёт разведки docs/plans/) — не подгонять
        под это поведение, а звать с явным dictionary_type."""
        resp = self.client.post("/dictionaries", json={"name": name, "type": dictionary_type})
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Dictionary item created: ID={data['id']}, type={dictionary_type}, name={name}")
        return data

    def update(self, dictionary_id: int, name: str) -> Dict:
        """Обновление имени элемента справочника. Метод — PATCH, не PUT
        (PUT/GET по /dictionaries/{id} отвечают 405, см. отчёт разведки)."""
        resp = self.client.patch(f"/dictionaries/{dictionary_id}", json={"name": name})
        expect_status(resp, 200)
        return resp.json()["data"]

    def delete(self, dictionary_id: int) -> bool:
        """Удаление элемента справочника."""
        resp = self.client.delete(f"/dictionaries/{dictionary_id}")
        success = resp.status_code in (200, 202, 204)
        if success:
            logger.info(f"Dictionary item deleted: ID={dictionary_id}")
        else:
            logger.warning(f"Dictionary item delete failed: ID={dictionary_id}, status={resp.status_code}")
        return success

    def find_by_name(self, dictionary_type: str, name: str) -> Optional[Dict]:
        """Поиск элемента справочника по типу и точному имени через list_by_type
        (без пагинации — находит и только что созданный элемент)."""
        for item in self.list_by_type(dictionary_type):
            if item.get("name") == name:
                return item
        return None
