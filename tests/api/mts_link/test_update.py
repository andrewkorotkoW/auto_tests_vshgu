"""Часть 2 — синхронизация изменений мероприятия (docs/test_cases/mts_link/03_update.md).

02.11.2026: сведено с реальным контрактом (живая разведка на mts-link-release-main).
«webinar_data» как отдельная от «creation» часть — был домыслом: в реальной форме
редактирования один блок «Синхронизация вебинара» (MtsLinkEndpoint._PART_FIELD
теперь мапит оба имени на одно и то же поле webinar_status). Промежуточное
значение сразу после правки (было "in_progress") не перепроверялось отдельно для
UPDATE живьём (только для СОЗДАНИЯ, там подтверждено "syncing") — проверка этого
переходного состояния убрана, остался только конечный "synced".

2 теста удалены: «изменение только внутренних полей не создаёт запроса» и «ошибка
обновления» — первый требует доказать ОТСУТСТВИЕ запроса к МТС Линк (аудит-лог,
подтверждённо несуществующий эндпоинт, 404), второй требует управляемой ошибки от
МТС Линк (нет мока). «Ошибка обновления → автоматический ретрай» удалён туда же."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 2: обновление данных вебинара")
@pytest.mark.api
@pytest.mark.mts_link
class TestUpdate:
    @allure.title("Изменение полей, уходящих в МТС Линк, запускает синхронизацию")
    @pytest.mark.smoke
    def test_update_synced_fields_triggers_sync(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно»."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item, "creation") == "synced"

        new_name = "Изменённое название вебинара"
        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"name": new_name},
        )
        assert resp.status_code == 200, resp.text

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert fetched["attributes"]["name"] == new_name
        assert mts_link_endpoint.wait_for_part_status(item, "webinar_data") == "synced"

    @allure.title("После начала вебинара редактирование заблокировано")
    def test_update_blocked_after_webinar_started(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: мероприятие «МТС Линк», время начала вебинара наступило."""
        item = created_schedule_item(
            item_type="mts_link", url="",
            date_time_from="2020-01-01T10:00", date_time_to="2020-01-01T11:00",
        )
        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"name": "Попытка изменить начавшийся вебинар"},
        )
        assert resp.status_code in (403, 422), resp.text
