import allure
import pytest


KNOWN_REGISTER_TEMPLATE_TYPES = [
    "register_application",
    "user_verified_email",
    "application_accepted",
    "application_rejected",
]


@allure.feature("Уведомления")
@allure.story("Шаблоны саморегистрации и формы оценки")
class TestRegisterReviewTemplatesApi:

    @allure.title("GET /notifications/register-templates — список шаблонов саморегистрации")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_register_templates_list_schema(self, notifications_endpoint):
        templates = notifications_endpoint.list_register_templates()
        assert templates, "Список шаблонов саморегистрации пуст"
        for template in templates:
            assert template.get("type")
            assert "title" in template
            assert "body" in template

    @allure.title("GET /notifications/register-templates/{type} — известный тип возвращает схему")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    @pytest.mark.parametrize("template_type", KNOWN_REGISTER_TEMPLATE_TYPES)
    def test_register_template_by_known_type(self, notifications_endpoint, template_type):
        template = notifications_endpoint.get_register_template(template_type)
        assert template["type"] == template_type
        assert template["title"]
        assert template["body"]

    @allure.title("GET /notifications/register-templates/{type} — неизвестный тип: кандидат в дефект")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Кандидат в дефект (см. README §13): для неизвестного type GET "
            "/notifications/register-templates/{type} отвечает 200 c {'type': null, 'title': "
            "null, 'body': null} вместо ожидаемого 404 — непоследовательно с GET "
            "/notifications/{id}, где несуществующий id даёт 404."
        ),
    )
    def test_register_template_unknown_type_returns_404(self, api_client):
        resp = api_client.get("/notifications/register-templates/Автотест_несуществующий_тип")
        assert resp.status_code == 404, f"Ожидали 404, получили {resp.status_code}: {resp.text}"

    @allure.title("PUT register-template — тема/текст меняются и возвращаются к исходным в teardown")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_register_template_round_trip_restores_original(self, notifications_endpoint):
        """Round-trip подтверждён разведкой как безопасный (POST возвращает 200 с теми же
        значениями, что были переданы) — исходные title/body шаблона register_application
        обязательно возвращаются в finally, даже при падении assert."""
        template_type = "register_application"
        original = notifications_endpoint.get_register_template(template_type)

        try:
            with allure.step("Временно изменить тему и текст"):
                updated = notifications_endpoint.update_register_template(
                    template_type, "Автотест_временная_тема", "<p>Автотест временный текст</p>"
                )
                assert updated["title"] == "Автотест_временная_тема"
                assert updated["body"] == "<p>Автотест временный текст</p>"

            with allure.step("Изменения видны при повторном GET"):
                fetched = notifications_endpoint.get_register_template(template_type)
                assert fetched["title"] == "Автотест_временная_тема"
                assert fetched["body"] == "<p>Автотест временный текст</p>"
        finally:
            with allure.step("Вернуть исходные значения"):
                restored = notifications_endpoint.update_register_template(
                    template_type, original["title"], original["body"]
                )
                assert restored["title"] == original["title"]
                assert restored["body"] == original["body"]

    @allure.title("GET /notifications/review-templates — 200 и список ожидаемой схемы")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_review_templates_list_schema(self, notifications_endpoint):
        """На develop список пуст (см. отчёт разведки) — PUT/GET по id не проверяется:
        нет существующего шаблона, id которого можно было бы безопасно использовать без
        хардкода из БД."""
        templates = notifications_endpoint.list_review_templates()
        assert isinstance(templates, list)
        for template in templates:
            assert "id" in template
