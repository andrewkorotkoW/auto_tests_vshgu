"""Админка → «Каталоги → Темы вопросов»: админ переименовывает существующую тему
вопроса через UI-форму редактирования.

Перенос test_05_admin_edits_question_theme_in_catalog.py коллеги
(origin/feature/test-constructor-autotests) — см. докстринг test_04_* (та же логика
переноса локаторов в ConstructorAdminPage). Тема создаётся через API
(created_question_theme), правится через UI — предмет проверки. Отдельного teardown
не нужно: created_question_theme удаляет тему по id, который не меняется при
переименовании."""
import allure
import pytest

from api.helpers.data_generator import unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Админка: каталог тем вопросов")
class TestAdminEditsQuestionThemeInCatalog:

    @allure.title("UI: Администратор переименовывает тему вопроса в каталоге")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_edits_question_theme_in_catalog(self, constructor_admin_page, env, created_question_theme):
        suffix = unique_suffix()
        theme_name = f"Автотест_ТемаПравка_{suffix}"
        updated_theme_name = f"Автотест_ТемаПравкаОбновлено_{suffix}"

        with allure.step("1. Создать тему вопроса через API"):
            created_question_theme(name=theme_name)

        with allure.step("2. Найти тему в каталоге и переименовать"):
            constructor_admin_page.open_question_themes_catalog(env.ui_base_url)
            constructor_admin_page.search_question_theme_by_name(theme_name)
            constructor_admin_page.edit_question_theme_via_ui(theme_name, updated_theme_name)

        with allure.step("3. Найти тему по новому имени и проверить строку"):
            constructor_admin_page.search_question_theme_by_name(updated_theme_name)
            constructor_admin_page.assert_question_theme_row_visible(updated_theme_name)
