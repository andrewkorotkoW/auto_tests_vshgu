import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_template_payload

# Карточка просмотра шаблона (/admin/mail-template/{id}/show) обрезает значение поля
# «Наименование» через Blade-рендер Str::limit(value, 32) + "…" (подтверждено живым прогоном:
# имена из 10/20/32 символов показываются целиком, из 33/40/60 — обрезаются ровно до 32 символов
# с добавлением многоточия). Это не дефект (значение в БД полное, find_template_by_name находит
# запись по полному новому имени через /search — усечение только в show-вёрстке), поэтому
# сравниваем с усечённым до 32 символов префиксом, а не с полным сгенерированным именем.
_TEMPLATE_SHOW_NAME_LIMIT = 32


@allure.feature("Хелпдеск: Шаблоны")
@allure.story("CRUD шаблона ответа")
class TestTemplatesApi:

    @allure.title("POST /admin/mail-template — шаблон создаётся и находится в поиске списка")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_create_template(self, helpdesk_endpoint, created_helpdesk_template):
        template = created_helpdesk_template()

        with allure.step("GET /admin/mail-template/search — шаблон найден по наименованию"):
            found = helpdesk_endpoint.find_template_by_name(template["payload"]["name"])
            assert found is not None, f"Шаблон {template['payload']['name']!r} не найден в списке"

    @allure.title("GET /admin/mail-template/{id}/show — карточка шаблона содержит данные созданного шаблона")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_view_template(self, helpdesk_endpoint, created_helpdesk_template):
        template = created_helpdesk_template()

        html = helpdesk_endpoint.get_template(template["id"])
        assert template["payload"]["name"][:_TEMPLATE_SHOW_NAME_LIMIT] in html
        assert template["payload"]["keywords"] in html

    @allure.title("PUT /admin/mail-template/{id} — наименование шаблона обновляется")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_update_template(self, helpdesk_endpoint, created_helpdesk_template):
        template = created_helpdesk_template()
        new_payload = dict(template["payload"])
        new_name = f"{template['payload']['name']}_updated"
        new_payload["name"] = new_name

        with allure.step("PUT /admin/mail-template/{id} с изменённым наименованием"):
            resp = helpdesk_endpoint.update_template(template["id"], new_payload)
            assert resp.status_code < 400, f"Не удалось обновить шаблон: {resp.status_code} {resp.text[:300]}"

        with allure.step("GET /admin/mail-template/search — новое наименование находится в списке"):
            # Не проверяем show-страницу буквальным new_name: «Наименование» на ней обрезается
            # Str::limit(.., 32) + «…», и поскольку исходное имя уже длиннее 32 символов, суффикс
            # "_updated" не попадает в видимую (обрезанную) часть — такая проверка не отличила бы
            # обновлённое значение от старого. /search фильтрует по полному значению в БД.
            found = helpdesk_endpoint.find_template_by_name(new_name)
            assert found is not None, f"Шаблон с новым именем {new_name!r} не найден после обновления"

    @allure.title("DELETE /admin/mail-template/{id} — шаблон удаляется и пропадает из списка")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_delete_template(self, helpdesk_endpoint):
        payload = generate_helpdesk_template_payload()
        resp = helpdesk_endpoint.create_template(payload)
        assert resp.status_code < 400, f"Не удалось создать шаблон: {resp.status_code} {resp.text[:300]}"
        found = helpdesk_endpoint.find_template_by_name(payload["name"])
        assert found is not None, f"Шаблон {payload['name']!r} не найден перед удалением"
        template_id = found["id"]

        deleted = False
        try:
            with allure.step("DELETE /admin/mail-template/{id}"):
                resp = helpdesk_endpoint.delete_template(template_id)
                assert resp.status_code < 400, f"Не удалось удалить шаблон: {resp.status_code} {resp.text[:300]}"
                deleted = True

            with allure.step("GET /admin/mail-template/search — шаблон не находится в списке"):
                again = helpdesk_endpoint.find_template_by_name(payload["name"])
                assert again is None, "Шаблон всё ещё находится в списке после удаления"
        finally:
            if not deleted:
                try:
                    helpdesk_endpoint.delete_template(template_id)
                except Exception:  # noqa: BLE001 — teardown не должен ронять прогон
                    pass
