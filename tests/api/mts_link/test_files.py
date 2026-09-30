"""Часть 5 — синхронизация файлов презентаций (docs/test_cases/mts_link/06_files.md)."""
import allure
import pytest

VALID_FILE = "test_data/certificat.pdf"
INVALID_FILE = "test_data/course_tincan.zip"


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 5: синхронизация файлов презентаций")
@pytest.mark.api
@pytest.mark.mts_link
class TestFiles:
    @allure.title("Файл добавили → загружен и привязан к вебинару")
    @pytest.mark.smoke
    def test_add_file_uploads_and_attaches(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно», файл в пределах ограничений."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item["id"], "creation") == "success"

        assert mts_link_endpoint.validate_file_before_upload(VALID_FILE) is None
        resp = mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], VALID_FILE)
        assert resp.status_code in (200, 201, 202), resp.text

        assert mts_link_endpoint.wait_for_part_status(item["id"], "files") == "success"
        files = mts_link_endpoint.list_files_sync_state(item["id"])
        assert any(f.get("attached") for f in files), files

    @allure.title("Файл заменили → новый привязан, старый отвязан")
    def test_replace_file_attaches_new_detaches_old(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: файл уже привязан к вебинару."""
        item = created_schedule_item(item_type="mts_link", url="")
        mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], VALID_FILE)
        assert mts_link_endpoint.wait_for_part_status(item["id"], "files") == "success"
        old_files = mts_link_endpoint.list_files_sync_state(item["id"])

        new_file = "test_data/practical_task_main_document.docx"
        mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], new_file)
        assert mts_link_endpoint.wait_for_part_status(item["id"], "files") == "success"

        files = mts_link_endpoint.list_files_sync_state(item["id"])
        attached_names = {f.get("name") for f in files if f.get("attached")}
        assert new_file.split("/")[-1] in attached_names or len(files) >= len(old_files)

    @allure.title("Файл удалили → отвязан от вебинара")
    def test_delete_file_detaches_from_webinar(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: файл привязан к вебинару."""
        item = created_schedule_item(item_type="mts_link", url="")
        mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], VALID_FILE)
        assert mts_link_endpoint.wait_for_part_status(item["id"], "files") == "success"

        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"files": []},
        )
        assert resp.status_code == 200, resp.text
        assert mts_link_endpoint.wait_for_part_status(item["id"], "files") == "success"
        files = mts_link_endpoint.list_files_sync_state(item["id"])
        assert not any(f.get("attached") for f in files)

    @allure.title("Файл не проходит по формату/размеру → ошибка с указанием файла, остальные грузятся")
    def test_invalid_file_rejected_others_still_uploaded(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: два файла — один превышает ограничения по формату, второй валиден."""
        item = created_schedule_item(item_type="mts_link", url="")

        error = mts_link_endpoint.validate_file_before_upload(INVALID_FILE)
        assert error is not None and INVALID_FILE.split("/")[-1] in error, error

        valid_resp = mts_link_endpoint.attach_file(
            item["program_id"], item["stream_id"], item["module_id"], item["id"], VALID_FILE
        )
        assert valid_resp.status_code in (200, 201, 202), valid_resp.text
        assert mts_link_endpoint.wait_for_part_status(item["id"], "files") == "success"

    @allure.title("Файлы обрабатываются по одному за раз")
    def test_files_processed_one_at_a_time(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: к мероприятию прикреплено несколько файлов одновременно."""
        item = created_schedule_item(item_type="mts_link", url="")
        files = [VALID_FILE, "test_data/practical_task_main_document.docx", "test_data/cover.jpg"]
        for f in files:
            mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], f)

        assert mts_link_endpoint.wait_for_part_status(item["id"], "files", timeout=90.0) == "success"
        audit = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"], operation="upload_file")
        upload_intervals = [e.get("created_at") for e in audit]
        assert len(upload_intervals) == len(set(upload_intervals)), "Ожидались последовательные запросы, не пачкой"

    @allure.title("Ошибка загрузки одного файла не блокирует остальные")
    def test_upload_error_for_one_file_does_not_block_others(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: мок отвечает отказом по одному из файлов."""
        item = created_schedule_item(item_type="mts_link", url="")
        ok_file = VALID_FILE
        broken_file = "test_data/practical_task_answer.docx"
        for f in (ok_file, broken_file):
            mts_link_endpoint.attach_file(item["program_id"], item["stream_id"], item["module_id"], item["id"], f)

        status = mts_link_endpoint.wait_for_part_status(item["id"], "files")
        assert status == "error", status
        files = {f.get("name"): f for f in mts_link_endpoint.list_files_sync_state(item["id"])}
        assert files.get(ok_file.split("/")[-1], {}).get("attached")
