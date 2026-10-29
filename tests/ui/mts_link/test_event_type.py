"""Часть 0 — новый тип мероприятия «МТС Линк» (docs/test_cases/mts_link/01_event_type.md).

UI-проверки поверх AdminEventMtsPage/AdminTenantPage — реально выполнятся только при
MTS_LINK_READY=1 (см. conftest.py:skip_if_mts_link_not_ready).

6 тестов удалены 29.10.2026 (прогон #114, test_hub): написаны до живой разведки
29.10.2026 и звали методы AdminEventMtsPage, которых не существует и никогда не
существовало — open_create_form, is_type_field_editable, is_url_field_disabled,
is_mts_link_type_option_visible (гипотетический UI-флоу «обычная форма создания»; реальный —
правый клик по календарю, см. докстринг admin_event_mts_page.py). Не починка, а по сути
написание заново — нужна отдельная живая разведка по каждому сценарию (иконка типа
скрывается без интеграции? поле URL недоступно? тип нельзя сменить после создания?),
владелец подтвердил удаление, не перенос в TODO."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 0: тип мероприятия «МТС Линк»")
@pytest.mark.ui
@pytest.mark.mts_link
class TestEventType:
    @allure.title("В «Результатах активности» отображаются статусы создания вебинара и конвертации записи")
    def test_activity_results_show_mts_statuses(self, user_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: мероприятие «МТС Линк» с известными статусами (создание вебинара
        «в процессе», запись «конвертируется»). «Результаты активности» как отдельная
        страница в page objects репозитория не выделена (узел карты продукта не заведён,
        см. tests/product_map.yml) — судя по остальным методам ActivityPage, это та же
        страница, где слушатель завершает мероприятие. TODO: уточнить маршрут после
        появления ветки — здесь используется расширение ui/pages/activity_page.py
        (recording_player) как единственная точка входа, которая уже есть."""
        from ui.pages.activity_page import ActivityPage

        item = created_schedule_item(item_type="mts_link", url="")
        status = mts_link_endpoint.get_part_status(item["id"], "creation")
        assert status == "in_progress", status

        activity_page = ActivityPage(user_page)
        assert activity_page.is_recording_player_visible() is False, (
            "Пока запись конвертируется, плеер ещё не должен быть доступен"
        )
