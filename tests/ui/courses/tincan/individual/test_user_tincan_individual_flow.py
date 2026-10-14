import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.tincan_page import TincanPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("User Tincan Individual Flow")
class TestUserTincanIndividualFlow:

    @allure.title("Пользователь проходит курс Tincan через инд. трек")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    @pytest.mark.e2e
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Стенд develop (06.10.2026): плеер курса (/xapi/drivers/cmi5, новая вкладка) грузит пакет "
            "из /static/content/<uuid>/… и получает 502 Bad Gateway от nginx — «Перейти к изучению» "
            "не появляется. Прежняя причина xfail («курс не показывается в инд. обучении») была "
            "ошибкой page-объекта (не переключалась вкладка «Курсы и тесты», тур подменял карточки "
            "демо-данными) — исправлено, курс отображается и открывается."
        ),
    )
    def test_user_tincan_individual(self, page, api_client, prepared_user):
        from api.endpoints.tincan import TincanEndpoint
        tincan_ep = TincanEndpoint(api_client)

        # ========== API ==========
        with allure.step("1. Создать пользователя (с закрытым онбордингом — иначе тур подменяет карточки демо-данными)"):
            user = prepared_user()

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
                tincan_page.wait_loaded()
            tincan_page.page.screenshot(path="allure-results/tincan_ind_completed.png")
            allure.attach.file("allure-results/tincan_ind_completed.png", "Курс пройден", allure.attachment_type.PNG)

            # Итог прохождения: все вопросы отвечены — вариантов ответа в тесте больше нет
            expect(tincan_page.frame.locator("label.c-radio")).to_have_count(0)

        with allure.step("7. Очистка"):
            tincan_ep.mass_delete([course_id])

        logger.info("Tincan Individual — курс пройден!")


    @allure.title("Инд. обучение: в карточке курса отображается доп. файл (как в потоке)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.e2e
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Кандидат в дефект (develop, 06.10.2026): у курса, назначенного через инд. обучение "
            "(/users/content/distant/assign-activities), в карточке на вкладке «Курсы и тесты» нет "
            "блока файлов (span.files-table__text) — отображаются только название, срок, описание "
            "и «Начать». Page-объект потока ожидает файл в карточке (span.files-table__text), но "
            "потоковый тест сейчас сам xfail по навигации — сравнить с потоком вживую не удалось; "
            "уточнить у разработки, должны ли доп. файлы показываться в инд. обучении."
        ),
    )
    def test_individual_course_shows_additional_file(self, page, api_client, prepared_user):
        from api.endpoints.tincan import TincanEndpoint
        from api.helpers.data_generator import generate_tincan_payload
        tincan_ep = TincanEndpoint(api_client)
        user = prepared_user()
        course = tincan_ep.create(generate_tincan_payload(
            archive_uuid=tincan_ep.upload_archive(), cover_uuid=tincan_ep.upload_cover(),
            sub_files_uuids=[tincan_ep.upload_sub_file()],
        ))
        try:
            tincan_ep.assign_activities([course["id"]], [user["id"]])
            LoginPage(page).login(user["email"], user["password"])
            UserSidebarPage(page).dismiss_popups()
            tincan_page = TincanPage(page)
            tincan_page.start_tincan_individual(expect_sub_file=True)
        finally:
            tincan_ep.mass_delete([course["id"]])
