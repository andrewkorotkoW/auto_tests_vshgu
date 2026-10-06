"""Мобильная вёрстка (Pixel 7): слушатель открывает «Уведомления» (/portal-notifications)
и видит уведомление, адресованное ему.

Перенос desktop-сценария tests/ui/notifications/user/test_user_sees_notification.py на
мобильный профиль и тот же NotificationsPage — мобильная ветка в page object не нужна
(см. docs/mobile/layout_facts.md п.6: страница открывается по URL без проблем, шапка
«← Назад» вместо заголовка раздела, нижняя панель вкладок видна, тот же набор из
4 пунктов). Создание уведомления — напрямую через NotificationsEndpoint/
generate_notification_payload (как tests/ui/notifications/conftest.py::created_notification),
без общей фикстуры: она лежит в tests/ui/notifications/conftest.py и не видна тестам
в tests/ui/mobile/, а заводить фикстуру на один тест в отдельном дереве избыточно."""
import allure
import pytest
from playwright.sync_api import expect

from api.endpoints.notifications import NotificationsEndpoint
from api.helpers.data_generator import generate_notification_payload
from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.login_page import LoginPage
from ui.pages.notifications_page import NotificationsPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("Мобильная вёрстка")
@allure.story("Уведомления (/portal-notifications)")
class TestMobileNotifications:

    @allure.title("Мобильный (Pixel 7): слушатель видит в «Уведомлениях» своё уведомление")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.mobile
    def test_mobile_user_sees_notification(
        self, page, env, api_client, prepared_user, is_mobile,
    ):
        assert is_mobile, "Тест должен запускаться с --mobile/MOBILE=1 — иначе он не проверяет мобильную вёрстку"
        allure.dynamic.parameter("device", "Pixel 7")

        notifications_endpoint = NotificationsEndpoint(api_client)
        notification_id = None
        try:
            with allure.step("1. Подготовить слушателя и создать уведомление, адресованное ему"):
                user = prepared_user()
                prepare_user_for_tests_via_api(env, user["email"], user["password"])
                payload = generate_notification_payload(users=[user["id"]])
                notification = notifications_endpoint.create(payload)
                notification_id = notification["id"]
                caption = notification["caption"]
                expected_text = notification["text"].replace("<p>", "").replace("</p>", "")

            with allure.step(f"2. Войти слушателем '{user['email']}'"):
                LoginPage(page).login(
                    user["email"], user["password"], base_url=env.ui_base_url, handle_onboarding=False
                )
                UserSidebarPage(page).dismiss_popups()
                assert "/auth" not in page.url, page.url

            notifications_page = NotificationsPage(page)
            with allure.step("3. Открыть «Уведомления»"):
                notifications_page.open(env.ui_base_url)

            with allure.step("4. Тема уведомления видна в списке"):
                card = notifications_page.notification_card(caption)
                expect(card).to_be_visible(timeout=15000)
                assert caption in notifications_page.notification_titles()

            with allure.step("5. Текст уведомления совпадает с созданным"):
                assert notifications_page.notification_text(caption) == expected_text

            with allure.step("6. Открыть уведомление"):
                notifications_page.open_notification(caption)

            with allure.step("7. Скриншот экрана уведомлений (вёрстка Pixel 7)"):
                page.screenshot(path="allure-results/mobile_notifications.png")
                allure.attach.file(
                    "allure-results/mobile_notifications.png", "Уведомления (моб.)", allure.attachment_type.PNG
                )
        finally:
            if notification_id is not None:
                try:
                    notifications_endpoint.delete([notification_id])
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"Failed to delete notification {notification_id}: {exc}")
