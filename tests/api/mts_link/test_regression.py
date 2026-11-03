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

    # Регресс бага №6 (docs/test_cases/mts_link/16_prod_safe_run.md): невалидный/отсутствующий
    # `type` ронял 500 ValueError из ScheduleItemType::from() (ScheduleItemStoreRequest.php:60) со
    # стектрейсом и путём /srv/app в ответе. Воспроизводилось трижды (27.10, 30.10, 02.11), 03.11.2026
    # на mts-link-release-main исправлено — все три сценария дают чистый 422. Тест — чтобы 500 не
    # вернулась: проверяем и код, и что в теле нет следов исключения/серверных путей.
    @allure.title("Невалидный/отсутствующий type → 422, не 500 ({case})")
    @pytest.mark.parametrize("case", ["invalid_type", "missing_type", "put_partial_without_type"])
    def test_invalid_or_missing_type_returns_422_not_500(
        self, case, api_client, created_module, created_schedule_item, mts_link_endpoint
    ):
        """Предусловие: -. Баг №6, см. комментарий выше."""
        if case == "put_partial_without_type":
            item = created_schedule_item(item_type="webinar")
            resp = api_client.put(
                f"/programs/{item['program_id']}/streams/{item['stream_id']}"
                f"/modules/{item['module_id']}/schedule-items/{item['id']}",
                json={"data": {"attributes": {"name": "Автотест_без_type"}}},
            )
        else:
            module = created_module()
            payload = mts_link_endpoint.build_event_payload()
            if case == "invalid_type":
                payload["data"]["attributes"]["type"] = "definitely_not_a_type"
            else:
                del payload["data"]["attributes"]["type"]
            resp = api_client.post(
                f"/programs/{module['program_id']}/streams/{module['stream_id']}"
                f"/modules/{module['id']}/schedule-items",
                json=payload,
            )

        assert resp.status_code == 422, f"{case}: ожидали 422, получили {resp.status_code}: {resp.text[:300]}"
        body = resp.text
        assert "/srv/app" not in body and "ValueError" not in body and '"trace"' not in body, (
            f"{case}: в ответе 422 не должно быть стектрейса/серверных путей: {body[:300]}"
        )
        # Ошибка должна быть привязана именно к полю type (тело приходит с \uXXXX-экранированием,
        # по подстроке «Тип» в сыром тексте не искать).
        errors = resp.json().get("errors") or {}
        assert "data.attributes.type" in errors, f"{case}: ожидали ошибку валидации по полю type: {body[:300]}"
