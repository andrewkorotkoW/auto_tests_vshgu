"""Часть 5 — синхронизация файлов презентаций (docs/test_cases/mts_link/06_files.md).

02.11.2026: сведено с реальным контрактом (живая разведка на mts-link-release-main).
Реальный путь загрузки — `POST /upload/schedule_item_files` (не
`.../schedule-items/{id}/files`, которого не существует) + отдельный ПОЛНЫЙ PUT
элемента расписания, чтобы добавить загруженный материал в attributes.files (см.
MtsLinkEndpoint.attach_file). У привязанных файлов НЕТ индивидуального статуса
привязки/синхронизации — только метаданные материала (имя/размер/url) плюс
агрегированный files_sync_status; поэтому проверки ниже смотрят на присутствие
файла по имени в attributes.files + на files_sync_status, а не на выдуманный флаг
f["attached"].

2 теста удалены: «файлы обрабатываются по одному за раз» требовал аудит-лога
запросов к МТС Линк (get_request_log_entries, подтверждённо несуществующий
эндпоинт, 404) — без него нельзя увидеть интервалы между запросами; к тому же
реальный эндпоинт загрузки принимает files[] пачкой, а не по одному файлу за раз,
так что сама посылка теста («по одному») under вопросом. «Ошибка загрузки одного
файла не блокирует остальные» требует управляемой ошибки от МТС Линк, которую
нечем спровоцировать на реальном проде (нет мока)."""
import allure
import pytest

VALID_FILE = "test_data/certificat.pdf"
INVALID_FILE = "test_data/course_tincan.zip"


def _file_names(fetched_attributes: dict) -> set:
    return {f.get("material", {}).get("name") for f in fetched_attributes.get("files", [])}


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 5: синхронизация файлов презентаций")
@pytest.mark.api
@pytest.mark.mts_link
class TestFiles:
    @allure.title("Файл добавили → загружен и привязан к вебинару")
    @pytest.mark.smoke
    def test_add_file_uploads_and_attaches(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно», файл в пределах ограничений."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item, "creation") == "synced"

        assert mts_link_endpoint.validate_file_before_upload(VALID_FILE) is None
        resp = mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], VALID_FILE)
        assert resp.status_code == 200, resp.text

        assert mts_link_endpoint.wait_for_part_status(item, "files") == "success"
        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert "certificat.pdf" in _file_names(fetched["attributes"])

    @allure.title("Файл заменили → новый привязан, старый отвязан")
    def test_replace_file_attaches_new_detaches_old(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: файл уже привязан к вебинару."""
        item = created_schedule_item(item_type="mts_link", url="")
        mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], VALID_FILE)
        assert mts_link_endpoint.wait_for_part_status(item, "files") == "success"

        new_file = "test_data/practical_task_main_document.docx"
        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"files": []},
        )
        assert resp.status_code == 200, resp.text
        mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], new_file)
        assert mts_link_endpoint.wait_for_part_status(item, "files") == "success"

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        names = _file_names(fetched["attributes"])
        assert "practical_task_main_document.docx" in names
        assert "certificat.pdf" not in names

    @allure.title("Файл удалили → отвязан от вебинара")
    def test_delete_file_detaches_from_webinar(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: файл привязан к вебинару."""
        item = created_schedule_item(item_type="mts_link", url="")
        mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], VALID_FILE)
        assert mts_link_endpoint.wait_for_part_status(item, "files") == "success"

        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"files": []},
        )
        assert resp.status_code == 200, resp.text
        assert mts_link_endpoint.wait_for_part_status(item, "files") == "success"
        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert fetched["attributes"].get("files") == []

    @allure.title("Файл не проходит по формату/размеру → клиентская проверка не даёт отправить")
    def test_invalid_file_rejected_before_upload(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: файл превышает ограничения по формату."""
        item = created_schedule_item(item_type="mts_link", url="")

        error = mts_link_endpoint.validate_file_before_upload(INVALID_FILE)
        assert error is not None and INVALID_FILE.split("/")[-1] in error, error
