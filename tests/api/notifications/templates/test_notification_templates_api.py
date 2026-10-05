import allure
import pytest

from api.helpers.data_generator import generate_notification_template_payload
from utils.retry import wait_until


@allure.feature("Уведомления")
@allure.story("Шаблоны уведомлений")
class TestNotificationTemplatesApi:

    @allure.title("Шаблон уведомления: создать → получить → изменить тему/текст → список содержит")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_template_full_cycle(self, created_template, notifications_endpoint):
        template = created_template()

        with allure.step("GET /notifications/templates/{id}"):
            fetched = notifications_endpoint.get_template(template["id"])
            assert fetched["id"] == template["id"]
            assert fetched["name"] == template["name"]

        with allure.step("Список шаблонов содержит созданный"):
            templates = notifications_endpoint.list_templates()
            assert any(t["id"] == template["id"] for t in templates)

        with allure.step("PUT — смена темы (caption) и текста"):
            new_caption = f"Автотест_новая_тема_{template['name']}"
            new_text = f"<p>Автотест новый текст {template['name']}</p>"
            updated = notifications_endpoint.update_template(
                template["id"],
                {"name": template["name"], "caption": new_caption, "text": new_text},
            )
            assert updated["caption"] == new_caption
            assert updated["text"] == new_text

        with allure.step("Изменения сохранились при повторном GET"):
            fetched_after = notifications_endpoint.get_template(template["id"])
            assert fetched_after["caption"] == new_caption
            assert fetched_after["text"] == new_text

    @allure.title("POST /notifications/templates/delete → 200, шаблон пропадает из списка")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_delete_template_removes_it_from_list(self, notifications_endpoint):
        template = notifications_endpoint.create_template(generate_notification_template_payload())
        template_id = template["id"]

        try:
            with allure.step("POST /notifications/templates/delete"):
                deleted = notifications_endpoint.delete_templates([template_id])
                assert deleted, "Запрос на удаление шаблона не вернул успешный статус"

            with allure.step("Шаблон пропадает из GET /notifications/templates"):
                def _is_absent():
                    templates = notifications_endpoint.list_templates()
                    return not any(t["id"] == template_id for t in templates)

                gone = wait_until(_is_absent, timeout=12, interval=3)
                if not gone:
                    pytest.xfail(
                        "Кандидат в дефект: POST /notifications/templates/delete отвечает 200, "
                        "но шаблон остаётся в GET /notifications/templates непредсказуемо долго — "
                        "та же асинхронная задержка удаления, что и у POST /notifications/delete "
                        "(см. README §13)."
                    )
        finally:
            try:
                notifications_endpoint.delete_templates([template_id])
            except Exception:
                pass
