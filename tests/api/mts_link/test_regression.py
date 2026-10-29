"""Регресс: появление типа «МТС Линк» не ломает обычные очные мероприятия
(docs/test_cases/mts_link/15_regression.md).

Перенесено из tests/ui/mts_link/test_regression.py 29.10.2026 (прогон #114, test_hub):
UI-вариант (3 теста через AdminEventMtsPage.open_create_form/is_mts_link_type_option_visible,
1 через таблицу «Слушатели» с фильтром «Очка») написан до живой разведки 29.10.2026 и либо
зовёт несуществующие методы, либо требует непростой UI-флоу (фильтр → колонка по мероприятию,
см. докстринг stream_listeners_page.py) ради проверки, которую решает один API-запрос:
реальный риск регрессии — бэкендный (не задевает ли появление mts_link общий код обычных
мероприятий), не UI-рендеринга. Контракт подтверждён прогоном #113, 29.10.2026 (реальное
прохождение теста): у item_type="mts_link" в ответе schedule-items есть блок
attributes.mts_link (webinar_status, mts_event_id, ...) — у обычных мероприятий его быть не
должно."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Регресс существующего функционала")
@pytest.mark.api
@pytest.mark.mts_link
class TestRegression:
    @allure.title("Обычное мероприятие не получает блок mts_link")
    @pytest.mark.smoke
    def test_regular_event_has_no_mts_link_block(self, created_schedule_item, schedule_items_endpoint):
        """Предусловие: тенант с настроенной интеграцией МТС Линк (появление нового типа
        не должно задевать обычный)."""
        item = created_schedule_item(item_type="webinar")
        fetched = schedule_items_endpoint.get(
            item["program_id"], item["stream_id"], item["module_id"], item["id"]
        )
        assert fetched["attributes"].get("mts_link") is None, (
            f"У обычного мероприятия (item_type=webinar) появился блок mts_link: "
            f"{fetched['attributes'].get('mts_link')!r}"
        )
