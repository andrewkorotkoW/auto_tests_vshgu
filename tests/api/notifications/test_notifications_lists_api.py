import allure
import pytest


@allure.feature("Уведомления")
@allure.story("Списки и справочники")
class TestNotificationsListsApi:

    @allure.title("GET /notifications содержит созданное уведомление с полями id/тема/дата/получатели")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_notifications_list_has_expected_fields(
        self, created_user, created_notification, notifications_endpoint
    ):
        receiver = created_user()
        notification = created_notification(users=[receiver["id"]])

        with allure.step("Найти созданное уведомление в общем списке GET /notifications"):
            found = notifications_endpoint.find_by_name(notification["name"])
            assert found is not None, "Созданное уведомление не найдено в GET /notifications"

        with allure.step("Проверить обязательные поля: id, тема (caption), дата, получатели"):
            assert found["id"] == notification["id"]
            assert found.get("caption"), "Нет темы (caption) уведомления"
            assert "sent_at" in found and "send_at" in found, (
                "Нет полей даты отправки (sent_at — фактическая, send_at — плановая)"
            )
            assert "users" in found, "Нет поля получателей (users)"

    @allure.title("GET /notifications/creators — непустой справочник авторов уведомлений")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_creators_dictionary_not_empty(self, notifications_endpoint):
        creators = notifications_endpoint.creators()
        assert creators, "Справочник авторов уведомлений пуст"
        for creator in creators:
            assert "id" in creator
            assert "attributes" in creator

    @allure.title("GET /notifications/receivers — непустой справочник получателей")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_receivers_dictionary_not_empty(self, notifications_endpoint):
        receivers = notifications_endpoint.receivers()
        assert receivers, "Справочник получателей пуст"
        for receiver in receivers:
            assert "id" in receiver
            assert "attributes" in receiver

    @allure.title("GET /notifications/text-variables — непустой справочник переменных подстановки")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_text_variables_dictionary_not_empty(self, notifications_endpoint):
        variables = notifications_endpoint.text_variables()
        assert variables, "Справочник переменных подстановки текста пуст"
        for label, placeholder in variables.items():
            assert label
            assert placeholder.startswith("{") and placeholder.endswith("}"), (
                f"Переменная '{label}' имеет неожиданный формат: {placeholder}"
            )
