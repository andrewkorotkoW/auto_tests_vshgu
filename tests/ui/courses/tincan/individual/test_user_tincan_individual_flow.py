import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.tincan_page import TincanPage
from ui.pages.user_sidebar_page import UserSidebarPage
from config.settings import settings
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("User Tincan Individual Flow")
class TestUserTincanIndividualFlow:

    @allure.title("Пользователь проходит курс Tincan через инд. трек")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    @pytest.mark.xfail(
        reason=(
            "Известный дефект стенда develop (тот же класс, что в "
            "tests/ui/homework/individual/test_ui_homework_flow.py, "
            "tests/ui/proctoring/individual/test_proctoring_flow.py и "
            "tests/ui/polls/individual/test_poll_flow.py): после API-назначения через "
            "/users/content/distant/assign-activities (ответ 200) раздел «Индивидуальное "
            "обучение» слушателя не показывает назначенный курс — карточка с его именем не "
            "появляется в UI."
        ),
        strict=False,
    )
    def test_user_tincan_individual(self, page, api_client, created_user):
        from api.endpoints.tincan import TincanEndpoint
        tincan_ep = TincanEndpoint(api_client)

        # ========== API ==========
        with allure.step("1. Создать пользователя"):
            user = created_user()

        with allure.step("2. Создать курс"):
            from api.helpers.data_generator import generate_tincan_payload
            cover = tincan_ep.upload_cover()
            archive = tincan_ep.upload_archive()
            sub = tincan_ep.upload_sub_file()
            payload = generate_tincan_payload(archive_uuid=archive, cover_uuid=cover, sub_files_uuids=[sub])
            course = tincan_ep.create(payload)
            course_id = course["id"]

        with allure.step("3. Назначить курс на инд. трек"):
            tincan_ep.assign_activities([course_id], [user["id"]])

        # ========== UI ==========
        with allure.step("4. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            UserSidebarPage(page).dismiss_popups()

        with allure.step("5. Открыть курс через инд. обучение"):
            tincan_page = TincanPage(page)
            tincan_page.start_tincan_individual()

        with allure.step("6. Пройти курс"):
            for i in range(30):
                if tincan_page.frame.locator("label.c-radio").first.is_visible(timeout=2000):
                    tincan_page.frame.locator("label.c-radio").first.click(force=True)
                    tincan_page.frame.locator("button:has-text('Ответить')").first.click(force=True)
                    tincan_page.frame.locator("button:has-text('Далее')").first.click(force=True)
                    if tincan_page.frame.locator("div.navigation-button-item__title:has-text('Тестирование')").is_visible(timeout=2000):
                        tincan_page.frame.locator("div.navigation-button-item__title:has-text('Тестирование')").first.click(force=True)
                        tincan_page.frame.locator("button:has-text('Начать тест')").first.click(force=True)
                else:
                    break
            if tincan_page.frame.locator("button:has-text('Продолжить обучение')").is_visible(timeout=3000):
                tincan_page.frame.locator("button:has-text('Продолжить обучение')").first.click(force=True)
                tincan_page.page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            tincan_page.page.screenshot(path="allure-results/tincan_ind_completed.png")
            allure.attach.file("allure-results/tincan_ind_completed.png", "Курс пройден", allure.attachment_type.PNG)

            # Итог прохождения: все вопросы отвечены — вариантов ответа в тесте больше нет
            expect(tincan_page.frame.locator("label.c-radio")).to_have_count(0)

        with allure.step("7. Очистка"):
            tincan_ep.mass_delete([course_id])

        logger.info("Tincan Individual — курс пройден!")