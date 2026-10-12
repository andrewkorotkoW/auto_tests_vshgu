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
    def test_public_aos_pass(self, page, created_aos, aos_endpoint):
        from config.settings import settings

        # 1. Создать АОС через фикстуру
        with allure.step("1. Создать АОС"):
            aos = created_aos()
            logger.info(f"АОС: ID={aos['id']}")

        # 2. Активировать АОС на потоке и получить публичную ссылку от бэкенда
        with allure.step("1.1. Активировать АОС на потоке и получить публичную ссылку"):
            assert aos_endpoint.activate(aos["program_id"], aos["stream_id"], aos["id"]), "АОС не активировалась"
            public_url = aos_endpoint.public_link(aos["program_id"], aos["stream_id"], aos["id"])
            logger.info(f"Публичная ссылка: {public_url}")
            assert "stream_feedback_content=" in public_url, f"Неожиданный формат ссылки: {public_url}"

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

        # 5. Пройти вопросы: АОС — группы вопросов на одной странице (шкалы 1–10, комментарий,
        #    чекбоксы) и кнопка «Ответить»; первый экран обязан появиться, иначе анонимный доступ не работает
        with allure.step("4. Пройти вопросы"):
            answerable = page.locator("textarea, input[type='checkbox'], input[type='radio'], label.c-radio").first
            expect(answerable).to_be_visible(timeout=15000)
            finish_btn = page.locator("button:has-text('Завершить')").first
            groups_answered = 0
            next_group_btn = page.locator("button:has-text('Перейти к следующей группе')").first
            # Пока плеер переключает группу вопросов, кнопки стоят в aria-busy="true", а
            # контейнер вопросов перехватывает клики — ждём, пока занятых элементов не останется
            # (это и есть конец перехода, а не фиксированная пауза).
            busy = page.locator("[aria-busy='true']")
            for _ in range(10):
                expect(busy).to_have_count(0, timeout=15000)
                if finish_btn.is_visible():
                    break
                if next_group_btn.is_visible():
                    next_group_btn.click()
                    page.wait_for_load_state("networkidle")
                    continue
                # шкалы 1–10: в каждой выбираем «10»
                for scale_ten in page.locator("button:text-is('10'), .scale-item:text-is('10'), [class*='scale'] :text-is('10')").all():
                    scale_ten.click()
                for area in page.locator("textarea").all():
                    area.fill(f"Ответ автотеста {groups_answered + 1}")
                checkboxes = page.locator("input[type='checkbox']")
                for i in range(min(3, checkboxes.count())):
                    checkboxes.nth(i).check(force=True)
                radios = page.locator("label.c-radio, .v-radio")
                if radios.count():
                    radios.first.click(force=True)
                answer_btn = page.locator("button:has-text('Ответить')").first
                expect(answer_btn).to_be_enabled(timeout=5000)
                answer_btn.click()
                groups_answered += 1
                page.wait_for_load_state("networkidle")
                page.screenshot(path=f"allure-results/aos_public_group_{groups_answered}.png")
            logger.info(f"Отвечено групп вопросов: {groups_answered}")
            assert groups_answered > 0, "Ни одна группа вопросов не была отвечена"

        # 6. Финальный экран «Спасибо за прохождение опроса!» — единственный надёжный признак,
        #    что ответы приняты; кнопка «Завершить» на нём лишь закрывает плеер
        with allure.step("5. Финальный экран"):
            # после последней группы появляется «Завершить» — по нему плеер отдаёт ответы и показывает благодарность
            expect(finish_btn).to_be_visible(timeout=10000)
            finish_btn.click()
            thanks = page.get_by_text("Спасибо за прохождение опроса")
            expect(thanks).to_be_visible(timeout=15000)
            expect(answerable).to_have_count(0)
            page.screenshot(path="allure-results/aos_public_completed.png")
            allure.attach.file("allure-results/aos_public_completed.png", "АОС пройдена публично", allure.attachment_type.PNG)
            finish_btn.click()
            logger.info("Публичное прохождение АОС успешно!")