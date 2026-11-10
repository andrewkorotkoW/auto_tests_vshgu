"""Слушатель проходит АОС (анкету обратной связи) целиком.

Сценарий переписан 10.11.2026 под реальную структуру плеера: АОС из generate_aos_payload
(без своих вопросов) — это не визард «один вопрос — один экран» с кнопкой «Вперед», а
группы вопросов по одной на экран («Вебинар …»: три шкалы 1–10 + комментарий + чекбоксы
компетенций; «Организация учебного дня»: шкалы + комментарий), см. AosPage. Старый
сценарий ждал «Вперед», которого в плеере нет, и с 24.09 висел под xfail.
"""
import re

import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.aos_page import AosPage
from ui.pages.user_sidebar_page import UserSidebarPage
from config.settings import settings
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("User AOS Flow")
class TestUserAosFlow:

    @allure.title("Пользователь проходит АОС полностью")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    @pytest.mark.e2e
    def test_user_complete_aos(self, page, api_client, prepared_user, created_aos, assignments_endpoint):
        """API: создать → назначить → UI: логин → пройти все группы анкеты → «Спасибо» →
        повторный вход: вкладки «Анкета обратной связи» больше нет."""

        # ========== API: ПОДГОТОВКА ==========
        with allure.step("1. Создать пользователя"):
            user = prepared_user()
            logger.info(f"Пользователь: {user['email']} / {user['password']}")

        with allure.step("2. Создать АОС"):
            aos = created_aos()
            logger.info(f"АОС: ID={aos['id']}")

        with allure.step("3. Активировать АОС"):
            from api.endpoints.aos import AosEndpoint
            aos_ep = AosEndpoint(api_client)
            aos_ep.activate(aos["program_id"], aos["stream_id"], aos["id"])
            logger.info("✅ АОС активирован")

        with allure.step("4. Назначить пользователя в поток"):
            assignments_endpoint.assign(
                aos["program_id"], aos["stream_id"], [user["id"]]
            )
            logger.info("✅ Пользователь назначен")

        # ========== UI: ПРОХОЖДЕНИЕ ==========
        with allure.step("5. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            UserSidebarPage(page).dismiss_popups()

        with allure.step("6. Начать АОС"):
            aos_page = AosPage(page)
            # Тур показывается отдельно на каждой странице (см. докстринг dismiss_popups) и
            # иногда рендерится с задержкой после networkidle — повторный вызов подчищает
            # затемнение, которое иначе перехватывает клик по карточке программы
            UserSidebarPage(page).dismiss_popups()
            aos_page.start_aos(aos["program_name"])

        with allure.step("7. Пройти все группы вопросов: шкалы, комментарии, компетенции → «Завершить»"):
            groups = aos_page.complete_questionnaire()
            # две группы: «Вебинар …» (по мероприятию расписания) и «Организация учебного дня»
            assert groups >= 2, f"ожидали минимум 2 группы вопросов, прошли {groups}"
            logger.info(f"✅ АОС пройден: {groups} групп(ы)")

        with allure.step("8. После «Спасибо за прохождение опроса!» плеер возвращает в «Моё обучение»"):
            expect(page).to_have_url(re.compile(r"/education(?:[/?#]|$)"), timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/03_aos_completed.png")
            allure.attach.file("allure-results/03_aos_completed.png", "АОС пройден", allure.attachment_type.PNG)

        with allure.step("9. Повторный вход — вкладка не отображается после прохождения АОС"):
            page.context.clear_cookies()
            login_page.login(user["email"], user["password"])
            UserSidebarPage(page).dismiss_popups()

            # Снова открываем программу — тем же путём, что и в шаге 6 (карточка в «Моё
            # обучение» открывается кнопкой «Перейти к программе», заголовок не кликабелен;
            # старый локатор span:has-text(<имя>) карточку уже не находил)
            aos_page.open_program(aos["program_name"])
            UserSidebarPage(page).dismiss_popups()

            # Скриншот после входа в программу
            page.screenshot(path="allure-results/04_reopen_program.png")
            allure.attach.file("allure-results/04_reopen_program.png", "Повторный вход в программу",
                               allure.attachment_type.PNG)

            # Проверяем, что вкладки нет
            expect(page.locator("text=Анкета обратной связи")).to_be_hidden(timeout=3000)
            logger.info("Вкладка скрыта")
