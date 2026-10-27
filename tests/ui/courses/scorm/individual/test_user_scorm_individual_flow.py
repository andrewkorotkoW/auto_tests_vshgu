"""UI: слушатель проходит курс SCORM 2004 через «Индивидуальное обучение» — от назначения по API
до «Повторить» в карточке. Кейс TC-COURSES-004 (docs/test_cases/courses.md). Общие шаги —
tests/ui/courses/scorm/scorm_flow.py, page object — ui/pages/scorm_page.py.

Не зависит от OpenLRS: факт отправки xAPI-statements проверяется перехватом `POST /xAPI/statements`
из вкладки плеера, поэтому тест идёт на любом окружении (develop/stage/stand). Попадание statements
в OpenLRS — отдельный e2e tests/e2e/lrs/test_scorm_statements_in_lrs.py."""
import allure
import pytest

from api.endpoints.tincan import TincanEndpoint
from ui.pages.login_page import LoginPage
from ui.pages.scorm_page import ScormCoursePage
from ui.pages.user_sidebar_page import UserSidebarPage
from tests.ui.courses.scorm.scorm_flow import create_scorm_course, pass_scorm_and_verify


@allure.feature("Courses")
@allure.story("SCORM: инд. обучение")
class TestUserScormIndividualFlow:

    @allure.title("UI: слушатель проходит курс SCORM 2004 через инд. обучение — результат 100%, statements, «Повторить»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.e2e
    @pytest.mark.smoke
    def test_user_scorm_individual(self, page, api_client, prepared_user):
        tincan_ep = TincanEndpoint(api_client)

        with allure.step("1. API: слушатель (онбординг закрыт), курс SCORM 2004, назначение на инд. трек"):
            user = prepared_user()
            course = create_scorm_course(tincan_ep)
            assert tincan_ep.assign_activities([course["id"]], [user["id"]]), "assign-activities не 2xx"

        try:
            with allure.step("2. Логин слушателя → Индивидуальное обучение → Курсы и тесты → карточка курса"):
                LoginPage(page).login(user["email"], user["password"])
                UserSidebarPage(page).dismiss_popups()
                course_page = ScormCoursePage(page)
                course_page.open_individual_course(course["name"])

            with allure.step("3–7. Пройти курс и проверить результат (плеер, SCORM API, xAPI, карточка)"):
                pass_scorm_and_verify(course_page, course)
        finally:
            with allure.step("8. Очистка: удалить курс"):
                tincan_ep.mass_delete([course["id"]])
