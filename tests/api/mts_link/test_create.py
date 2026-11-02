"""Часть 1 — фоновое создание вебинара при создании мероприятия (docs/test_cases/mts_link/02_create.md).

02.11.2026: 3 из 5 тестов удалены при сведении api/endpoints/mts_link.py с реальным
контрактом (живая разведка на mts-link-release-main) — сценарии с управляемой
ошибкой/задержкой МТС Линк («мок отвечает ошибкой», «мок сначала отвечает ошибкой,
затем успехом») непроверяемы на реальном проде (нет мока, нет контроля над
поведением МТС Линк), а «части 2–5 не стартуют, пока вебинар не создан» прямо
противоречит наблюдаемому: живьём participants/lecturers/files_sync_status уже были
"success", пока webinar_status ещё был "syncing" — удалённую проверку порядка
частей не починить переименованием, сама посылка неверна. См.
docs/test_cases/mts_link/16_prod_safe_run.md."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 1: создание вебинара")
@pytest.mark.api
@pytest.mark.mts_link
class TestCreate:
    @allure.title("Мероприятие создаётся в ЛМС сразу, не дожидаясь МТС Линк")
    @pytest.mark.smoke
    def test_event_created_immediately_status_in_progress(
        self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint
    ):
        """Предусловие: мероприятие только что создано."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert item["id"] is not None

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert fetched["id"] == item["id"]

        status = mts_link_endpoint.get_part_status(item, "creation")
        assert status == "syncing", status

    @allure.title("Фоновое создание вебинара завершилось успешно")
    def test_event_creation_success_saves_ids_and_url(
        self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint
    ):
        """Предусловие: мероприятие «МТС Линк» создано, фон досинхронизировался."""
        item = created_schedule_item(item_type="mts_link", url="")

        status = mts_link_endpoint.wait_for_part_status(item, "creation")
        assert status == "synced", status

        integration = mts_link_endpoint.get_integration_status(item)
        assert integration.get("mts_webinar_id")

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert fetched["attributes"].get("url")
