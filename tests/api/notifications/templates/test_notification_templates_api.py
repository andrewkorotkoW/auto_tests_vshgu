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

                # До 11.11.2026 здесь был pytest.xfail «шаблон остаётся в списке непредсказуемо
                # долго». Дефекта не было: клиент слал delete с JSON {"ids": [...]} вместо
                # query template_ids[] (контракт админки), сервер отвечал success и ничего не
                # удалял, а list_templates к тому же читал только первую страницу. С верным
                # контрактом шаблон пропадает сразу и GET /templates/{id} даёт 404.
                assert wait_until(_is_absent, timeout=12, interval=3), (
                    f"Шаблон {template_id} остался в GET /notifications/templates через 12 с после delete"
                )
        finally:
            try:
                notifications_endpoint.delete_templates([template_id])
            except Exception:
                pass
