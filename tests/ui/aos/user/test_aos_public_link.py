import allure
import pytest
from playwright.sync_api import expect
from ui.pages.aos_page import AosPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("AOS Public Link")
class TestAosPublicLink:

    @allure.title("Пройти АОС по публичной ссылке без авторизации")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.xfail(
        reason=(
            "URL публичной ссылки '/testing/player?stream_feedback_content={id}' в тесте "
            "не подтверждён ничем в коде проекта (нигде больше не встречается, AosEndpoint.create "
            "не возвращает токен/hash публичной ссылки) — на develop анонимного пользователя по "
            "этому URL перекидывает на страницу логина. Нужна проверка реального механизма "
            "публичного доступа к АОС (например, кнопка «Скопировать ссылку» в админке), "
            "прежде чем чинить локаторы дальше по сценарию."
        ),
        strict=False,
    )
    def test_public_aos_pass(self, page, created_aos):
        from config.settings import settings

        # 1. Создать АОС через фикстуру
        with allure.step("1. Создать АОС"):
            aos = created_aos()
            logger.info(f"АОС: ID={aos['id']}")

        # 2. Сформировать публичную ссылку
        public_url = f"{settings.UI_BASE_URL}/testing/player?stream_feedback_content={aos['id']}"

        # 3. Открыть ссылку (без авторизации)
        with allure.step("2. Открыть публичную ссылку"):
            page.context.clear_cookies()  # убрать все куки, чтобы точно быть анонимом
            page.goto(public_url)
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/aos_public_opened.png")
            allure.attach.file("allure-results/aos_public_opened.png", "АОС по публичной ссылке", allure.attachment_type.PNG)

        # 4. Начать АОС (кнопка «Начать»)
        with allure.step("3. Начать АОС"):
            aos_page = AosPage(page)
            # Используем готовый метод для запуска анкеты (без открытия программы)
            aos_page.launch_questionnaire()  # если такого метода нет, просто дважды кликнем «Начать»

        # 5. Пройти вопросы (используем те же универсальные методы)
        with allure.step("4. Пройти вопросы"):
            for i in range(9):
                if page.locator("label.c-radio, input[type='radio']").first.is_visible(timeout=2000):
                    aos_page.answer_first_option()
                    aos_page.click_answer()
                    aos_page.click_next()
                elif page.locator("textarea").first.is_visible(timeout=2000):
                    aos_page.answer_textarea(f"Ответ {i+1}")
                    aos_page.click_answer()
                    aos_page.click_next()
                elif page.locator("input[type='checkbox']").first.is_visible(timeout=2000):
                    aos_page.answer_first_checkboxes(3)
                    aos_page.click_answer()
                    aos_page.click_next()
                else:
                    break
            # Завершить
            aos_page.click_finish()

        # 6. Финальный скриншот
        with allure.step("5. Скриншот результата"):
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/aos_public_completed.png")
            allure.attach.file("allure-results/aos_public_completed.png", "АОС пройдена публично", allure.attachment_type.PNG)

            # Итог прохождения: кнопка «Завершить» и форма опроса больше не отображаются
            expect(page.locator("button:has-text('Завершить')")).to_have_count(0)
            logger.info("Публичное прохождение АОС успешно!")