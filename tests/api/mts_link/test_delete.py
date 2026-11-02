"""Часть 6 — удаление вебинара (docs/test_cases/mts_link/07_delete.md).

02.11.2026: 4 из 5 тестов удалены при сведении api/endpoints/mts_link.py с реальным
контрактом — «фоном удаляются вебинар и сессия» / «регистрации/лекторы/файлы
удаляются вместе» / «после успешного ретрая не остаётся висящих объектов» требуют
аудит-лога запросов к МТС Линк (get_request_log_entries), а он бьёт в
подтверждённо несуществующий `/admin/mts-link/request-log-audit` (404, проверено
02.11.2026) — без него нельзя увидеть, что реально происходит в фоне после
удаления. «Ошибка удаления → автоматический ретрай» требует управляемой ошибки от
МТС Линк, которую нечем спровоцировать на реальном проде (нет мока) — и совпадает
по сути с уже задокументированным реальным багом №3 (асинхронный DeleteMtsWebinarJob
иногда падает, см. docs/test_cases/mts_link/16_prod_safe_run.md), который
недетерминирован и не воспроизводится по требованию."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 6: удаление вебинара")
@pytest.mark.api
@pytest.mark.mts_link
class TestDelete:
    @allure.title("Удаление сразу в ЛМС")
    @pytest.mark.smoke
    def test_delete_event_immediately_in_lms(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно»."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item, "creation") == "synced"

        deleted = schedule_items_endpoint.delete(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert deleted is True
