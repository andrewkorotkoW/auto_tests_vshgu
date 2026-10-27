"""Общие шаги прохождения SCORM-курса слушателем — для инд. трека, модуля программы и e2e-проверки
в OpenLRS (tests/e2e/lrs). Пакет — test_data/test_lms_scorm_2004.zip (Storyline, вопрос с
ответом «3»), page object — ui/pages/scorm_page.py."""
import time

import allure
from playwright.sync_api import expect

from api.endpoints.tincan import TincanEndpoint
from api.helpers.data_generator import generate_scorm_payload
from ui.pages.scorm_page import ScormCoursePage, StorylinePlayer

SCORM_ARCHIVE = "test_data/test_lms_scorm_2004.zip"
CORRECT_ANSWER = "3"
EXPECTED_VERBS = {"initialized", "launched", "responded", "passed", "completed"}


def create_scorm_course(tincan_ep: TincanEndpoint, prefix: str = "Автотест_SCORM2004") -> dict:
    """Обложка + архив SCORM 2004 → курс (`content_type: course-scorm`). Удалять — `mass_delete`."""
    cover = tincan_ep.upload_cover()
    archive = tincan_ep.upload_archive(SCORM_ARCHIVE)
    course = tincan_ep.create(generate_scorm_payload(name=f"{prefix}_{int(time.time() * 1000)}", archive_uuid=archive, cover_uuid=cover))
    return {"id": course["id"], "name": course["attributes"]["name"], "attributes": course["attributes"]}


def pass_scorm_and_verify(course_page: ScormCoursePage, course: dict) -> StorylinePlayer:
    """Карточка открыта → «Начать» → пройти пакет → проверить результат в плеере, в SCORM API и
    в отправленных xAPI-statements → закрыть плеер → карточка показывает «Повторить».
    Возвращает плеер (с записанными statements) для дополнительных проверок."""
    with allure.step("Карточка курса: название с суффиксом клиента, кнопка «Начать»"):
        assert course["name"] in course_page.details_text(), course_page.details_text()[:200]
        assert course_page.action_button_text() == "Начать", course_page.action_button_text()

    with allure.step("«Начать» → плеер /xapi/drivers/scorm в новой вкладке, пакет Storyline загружен"):
        player = course_page.start()
        player.wait_ready()
        assert "tst_lms" in player.body_text(), player.body_text()[:200]

    with allure.step("Пройти пакет: NEXT → ответ «3» → SUBMIT → Continue → Results «Your Score: 100%»"):
        results = player.pass_test_package(CORRECT_ANSWER)
        assert "100%" in results, results

    with allure.step("SCORM API драйвера: completion_status=completed, success_status=passed, score 100"):
        values = player.scorm_values()
        allure.attach(str(values), "cmi.*", allure.attachment_type.TEXT)
        assert values.get("completion_status") == "completed", values
        assert values.get("success_status") == "passed", values
        assert str(values.get("score_raw")) == "100", values

    with allure.step("Драйвер отправил xAPI-statements initialized/launched/responded/passed/completed в POST /xAPI/statements"):
        player.page.wait_for_timeout(2000)
        verbs = set(player.sent_verbs)
        allure.attach("\n".join(player.sent_verbs), "verbs", allure.attachment_type.TEXT)
        missing = EXPECTED_VERBS - verbs
        assert not missing, f"Не отправлены statements {sorted(missing)}; отправлены: {player.sent_verbs}"
        responded = player.statement("responded")
        assert responded.get("result", {}).get("response") == CORRECT_ANSWER, responded

    with allure.step("Закрыть плеер → в карточке курса кнопка «Повторить»"):
        player.close()
        course_page.page.wait_for_timeout(2000)
        course_page.reload_card()
        expect(course_page.action_button).to_have_text("Повторить", timeout=15000)
    return player
