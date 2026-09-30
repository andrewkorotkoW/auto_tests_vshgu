"""Часть 8 — ручной перезапуск синхронизации (docs/test_cases/mts_link/09_retry.md)."""
import allure
import pytest

from config.settings import settings


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 8: ручной перезапуск синхронизации")
@pytest.mark.ui
@pytest.mark.mts_link
class TestRetry:
    def _open_card(self, admin_event_mts_page, item):
        admin_event_mts_page.open(
            settings.UI_BASE_URL, item["program_id"], item["stream_id"], item["module_id"], item["id"]
        )

    @allure.title("Кнопка «Повторить» видна только при ошибке")
    @pytest.mark.smoke
    def test_retry_button_visible_only_on_error(self, admin_event_mts_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: два мероприятия — одно со статусом «Ошибка» по части, другое «Успешно»."""
        broken_item = created_schedule_item(item_type="mts_link", url="")
        self._open_card(admin_event_mts_page, broken_item)
        assert admin_event_mts_page.is_retry_button_visible("files") is True

        ok_item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_summary_status(ok_item["id"], timeout=90.0) == "success"
        self._open_card(admin_event_mts_page, ok_item)
        for part in ("creation", "webinar_data", "participants", "lecturers", "files"):
            assert admin_event_mts_page.is_retry_button_visible(part) is False

    @allure.title("Перезапуск конкретной части запускает синхронизацию только её")
    def test_retry_specific_part_syncs_only_that_part(self, admin_event_mts_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: часть «Файлы презентаций» в статусе «Ошибка», остальные — «Успешно»."""
        item = created_schedule_item(item_type="mts_link", url="")
        before = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"])

        self._open_card(admin_event_mts_page, item)
        admin_event_mts_page.click_retry("files")
        assert mts_link_endpoint.wait_for_part_status(item["id"], "files") == "success"

        after = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"])
        new_ops = {e.get("operation") for e in after[len(before):]}
        assert new_ops.issubset({"upload_file"}), new_ops

    @allure.title("Перезапуск создания вебинара тянет всю цепочку")
    def test_retry_creation_triggers_full_chain(self, admin_event_mts_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: часть «Создание вебинара» в статусе «Ошибка», остальные части не запущены."""
        item = created_schedule_item(item_type="mts_link", url="")
        self._open_card(admin_event_mts_page, item)
        admin_event_mts_page.click_retry("creation")

        assert mts_link_endpoint.wait_for_part_status(item["id"], "creation") == "success"
        for part in ("webinar_data", "participants", "lecturers", "files"):
            assert mts_link_endpoint.wait_for_part_status(item["id"], part, timeout=90.0) == "success"

    @allure.title("При идущем авторетрае повторный ручной запуск не создаётся")
    def test_manual_retry_not_duplicated_during_auto_retry(self, admin_event_mts_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: часть в статусе «Ошибка», авторетрай уже выполняется (мок задерживает ответ)."""
        item = created_schedule_item(item_type="mts_link", url="")
        before = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"], operation="upload_file")

        self._open_card(admin_event_mts_page, item)
        admin_event_mts_page.click_retry("files")

        after = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"], operation="upload_file")
        assert len(after) - len(before) <= 1, "Ожидался максимум один параллельный запрос по части"
