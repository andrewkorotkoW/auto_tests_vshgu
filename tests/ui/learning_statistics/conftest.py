"""UI-фикстуры для тестов «Статистика обучения → Курсы» (/admin/learning-statistics/courses).

Данные (`course_with_listeners`/`course_without_listeners`) — общие для API- и UI-тестов
этого раздела, вынесены в tests/conftest.py (видны и tests/api/learning_statistics).
Здесь остаётся только то, что специфично для UI: авторизованная страница администратора
с закрытыми онбординг-попапами.
"""
import pytest

from ui.pages.user_sidebar_page import UserSidebarPage


@pytest.fixture
def course_stats_admin_page(admin_page, env):
    """Страница админки на разделе «Статистика обучения» с закрытыми онбординг-попапами."""
    admin_page.goto(f"{env.ui_base_url}/admin/learning-statistics")
    UserSidebarPage(admin_page).dismiss_popups()
    yield admin_page
