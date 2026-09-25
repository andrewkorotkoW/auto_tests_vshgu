"""Админка → «Каталоги → Темы вопросов»: админ создаёт тему вопроса через UI-форму
каталога и видит её в списке.

Перенос test_04_admin_creates_question_theme_in_catalog.py коллеги
(origin/feature/test-constructor-autotests, src/ui/pages/catalogs_page.py::CatalogsPage)
на нашу архитектуру: локаторы каталога тем перенесены в ConstructorAdminPage (задача
требует «Локаторы только в Page Object (test_constructor_admin_page.py)», отдельный
CatalogsPage не заводим), тема создаётся через UI (это и есть предмет проверки),
удаляется через QuestionBankEndpoint по id, найденному после создания."""
import allure
import pytest

from api.helpers.data_generator import unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Админка: каталог тем вопросов")
class TestAdminCreatesQuestionThemeInCatalog:

    @allure.title("UI: Администратор создаёт тему вопроса в каталоге")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_creates_question_theme_in_catalog(
        self, constructor_admin_page, env, question_bank_endpoint, register_question_theme
    ):
        theme_name = f"Автотест_ТемаКаталог_{unique_suffix()}"

        with allure.step("1. Открыть каталог тем вопросов и создать тему"):
            constructor_admin_page.open_question_themes_catalog(env.ui_base_url)
            constructor_admin_page.create_question_theme_via_ui(theme_name)

        with allure.step("2. Найти тему в списке и проверить строку"):
            constructor_admin_page.search_question_theme_by_name(theme_name)
            theme = question_bank_endpoint.find_theme_by_name(theme_name)
            assert theme, f"Созданная тема не найдена через API: {theme_name}"
            register_question_theme(theme["id"])
            constructor_admin_page.assert_question_theme_row_visible(theme_name)
