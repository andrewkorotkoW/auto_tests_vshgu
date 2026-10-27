"""UI: слушатель проходит курс SCORM 2004 в модуле программы (поток) — от назначения по API до
«Повторить» в карточке. Кейс TC-COURSES-005 (docs/test_cases/courses.md). Общие шаги —
tests/ui/courses/scorm/scorm_flow.py, page object — ui/pages/scorm_page.py.

Маршрут слушателя: «Моё обучение» → карточка программы → «Перейти к программе» → страница модуля
`/education/program/<uuid>/module/<id>/activities` — на стенде 2420 (27.10.2026) модуль открыт сразу,
вкладка «Курсы и тесты» активна и карточка курса выбрана. Tincan-аналог
(tests/ui/courses/tincan/stream) помечен xfail по этой навигации на develop 06.10 — если здесь
«Курсы и тесты» окажется неактивной, это и будет воспроизведение того дефекта."""
import allure
import pytest

from api.endpoints.tincan import TincanEndpoint
from ui.pages.login_page import LoginPage
from ui.pages.scorm_page import ScormCoursePage
from ui.pages.user_sidebar_page import UserSidebarPage
from tests.ui.courses.scorm.scorm_flow import create_scorm_course, pass_scorm_and_verify


@allure.feature("Courses")
@allure.story("SCORM: поток")
class TestUserScormStreamFlow:

    @allure.title("UI: слушатель проходит курс SCORM 2004 в модуле программы — результат 100%, statements, «Повторить»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.e2e
    def test_user_scorm_stream(self, page, api_client, prepared_user, created_program, created_stream, created_module, assignments_endpoint):
        tincan_ep = TincanEndpoint(api_client)

        with allure.step("1. API: программа → поток → модуль, слушатель назначен в поток, курс SCORM 2004 в модуле"):
            program = created_program(name="E2E_SCORM_UI")
            stream = created_stream(program_id=program["id"])
            module = created_module(program_id=program["id"], stream_id=stream["id"])
            user = prepared_user()
            assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])
            course = create_scorm_course(tincan_ep)
            assert tincan_ep.assign_to_module(program["id"], stream["id"], module["id"], [course["id"]]), "курс не назначен в модуль"

        try:
            with allure.step("2. Логин слушателя → карточка программы → «Перейти к программе» → курс в модуле"):
                LoginPage(page).login(user["email"], user["password"])
                UserSidebarPage(page).dismiss_popups()
                course_page = ScormCoursePage(page)
                course_page.open_program_course(program["name"], course["name"])

            with allure.step("3–7. Пройти курс и проверить результат (плеер, SCORM API, xAPI, карточка)"):
                pass_scorm_and_verify(course_page, course)
        finally:
            with allure.step("8. Очистка: удалить курс (программа/поток/модуль/слушатель — фикстурами)"):
                tincan_ep.mass_delete([course["id"]])
