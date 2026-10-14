"""UI: пользователь заходит в «Уведомления» (/portal-notifications) и видит уведомление,
адресованное ему, с тем же текстом, что при создании.

Разведкой (ad-hoc скрипт вне pytest) подтверждено: страница отображает тему уведомления
из поля `caption` (не `name` — `name` нигде в карточке не показывается, это только
внутренний идентификатор для админского списка `/notifications`), в DOM рендерится сразу
после создания без заметной задержки, за карточку отвечает отдельный пользовательский
API `GET /api/v1/my-notifications` (не тот же `/notifications/*`, что в Части 1 плана).
"""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.notifications_page import NotificationsPage


@allure.feature("Уведомления UI")
@allure.story("Пользователь видит своё уведомление")
class TestUserSeesNotification:

    @allure.title("Пользователь видит в «Уведомлениях» тему и текст созданного уведомления")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.notifications
    @pytest.mark.e2e
    def test_user_sees_notification(self, user_page, env, created_notification, current_user_id):
        notification = created_notification(users=[current_user_id])
        caption = notification["caption"]
        expected_text = notification["text"].replace("<p>", "").replace("</p>", "")

        notifications_page = NotificationsPage(user_page)
        with allure.step("Открыть «Уведомления»"):
            notifications_page.open(env.ui_base_url)

        with allure.step("Тема уведомления видна в списке"):
            card = notifications_page.notification_card(caption)
            expect(card).to_be_visible(timeout=15000)
            assert caption in notifications_page.notification_titles()

        with allure.step("Текст уведомления совпадает с созданным"):
            assert notifications_page.notification_text(caption) == expected_text

        with allure.step("Открыть уведомление"):
            notifications_page.open_notification(caption)
