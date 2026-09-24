"""Админка → «Конструктор тестов и опросов»: админ создаёт опрос через мастер
создания и видит его в таблице конструктора.

Перенос test_03_admin_creates_poll_and_sees_it_in_constructor_table.py коллеги
(origin/feature/test-constructor-autotests) — см. докстринг test_01_* (та же логика
поиска строки без search_by_name, тот же паттерн teardown)."""
import allure
import pytest

from api.helpers.data_generator import unique_suffix
from utils.logger import logger


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Админка: создание опроса")
class TestAdminCreatesPollAndSeesItInConstructorTable:

    @allure.title("UI: Администратор создаёт опрос и видит его в таблице конструктора")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_creates_poll_and_sees_it_in_constructor_table(self, constructor_admin_page, env, tests_endpoint):
        constructor_name = f"Автотест_КонструкторОпрос_{unique_suffix()}"
        topic = "AQA constructor poll topic"
        content_id = None

        try:
            with allure.step("1. Открыть форму создания и создать опрос"):
                constructor_admin_page.open_create_page(env.ui_base_url)
                constructor_admin_page.create_poll_on_first_step(
                    admin_name=constructor_name,
                    external_name=constructor_name,
                    topic=topic,
                )
                content_id = constructor_admin_page.get_current_constructor_id()
                constructor_admin_page.assert_created_poll_constructor_opened()
                logger.info(f"Опрос создан через UI: ID={content_id}, name={constructor_name}")

            with allure.step("2. Открыть таблицу конструктора и убедиться, что опрос виден"):
                constructor_admin_page.open_constructor_table(env.ui_base_url)
                constructor_admin_page.assert_constructor_row_visible(
                    constructor_name=constructor_name,
                    constructor_type="Опрос",
                    topic=topic,
                )
        finally:
            with allure.step("3. Удалить опрос через API"):
                if content_id is not None:
                    tests_endpoint.mass_delete([content_id])
                    logger.info(f"Опрос удалён: ID={content_id}")
                else:
                    logger.warning("content_id не получен — удалять через API нечего")
