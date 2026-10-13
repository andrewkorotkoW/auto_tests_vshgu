"""UI: админка → «Уведомления» → вкладка «Все уведомления» — созданное уведомление
должно быть видно в таблице.

До 13.10.2026 был помечен xfail (кандидат в дефект: отправленное через resend уведомление
не появлялось в таблице — см. докстринг ui/pages/admin_notifications_page.py и README §13).
Снято: XPASS в ночном develop (run 65) и на k8s (run 67), затем 3 из 3 на k8s с --runxfail.
"""
import allure
import pytest

from ui.pages.admin_notifications_page import AdminNotificationsPage
from utils.retry import wait_until


@allure.feature("Уведомления UI")
@allure.story("Админка — таблица «Все уведомления»")
class TestAdminNotificationsTable:

    @allure.title("Созданное и отправленное уведомление видно в таблице админки «Все уведомления»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.notifications
    def test_admin_sees_created_notification_in_table(
        self, admin_page, env, created_notification, current_user_id, notifications_endpoint
    ):
        notification = created_notification(users=[current_user_id])

        with allure.step("Отправить уведомление явно (create() отдаёт его с send_at=null)"):
            result = notifications_endpoint.resend(notification["id"])
            assert result.get("status") == "success"

        admin_notifications_page = AdminNotificationsPage(admin_page)

        def _row_visible() -> bool:
            admin_notifications_page.open_all(env.ui_base_url)
            row = admin_notifications_page.notification_row(notification["name"])
            return row.count() > 0

        with allure.step("Дождаться строки с названием уведомления в таблице"):
            found = wait_until(_row_visible, timeout=24, interval=6)

        assert found, "Уведомление не появилось в таблице админки «Все уведомления»"
