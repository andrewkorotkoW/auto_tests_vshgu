"""Админка → «Конструктор тестов и опросов» → АОС потока: если ветвление
последовательности вопросов не оставляет ни одного пути в одну из групп (вторая
группа мероприятия), конструктор подсвечивает её как недостижимую («Нет связей»), а
активировать такую анкету на потоке нельзя — бэкенд отвечает «Данная версия АОС
недоступна для активации», переключатель активности откатывается обратно.

Перенос test_18_admin_cannot_activate_feedback_with_unreachable_sequence_group.py
коллеги (origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка —
как в test_15_*/test_17_* (created_stream_feedback, ветвление через
constructor_poll_question/constructor_sequence_answers), но в отличие от test_17_*
(где вторая группа мероприятия остаётся достижимой хоть по одному ответу) здесь оба
ответа стартовой группы ведут в «Организация учебного дня», group1_id никто не
целит — это и есть недостижимая группа. Разведано на develop через первый (неудачный)
прогон test_17_*: POST .../feedback/{id}/change-active отвечает 400 с тем же текстом
статуса, что и проверяет ConstructorAdminPage.assert_stream_feedback_activation_blocked,
до того, как этот файл был написан отдельно — is_valid, переданный в
PollsEndpoint.set_sequence_questions, на активацию не влияет, бэкенд сам
пересчитывает реальную достижимость групп."""
import allure
import pytest

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Админка: АОС потока с последовательностью вопросов")
class TestAdminCannotActivateFeedbackWithUnreachableSequenceGroup:

    @allure.title("UI: Администратор не может активировать АОС потока с недостижимой группой в последовательности")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_cannot_activate_feedback_with_unreachable_sequence_group(
        self,
        constructor_admin_page,
        env,
        polls_endpoint,
        created_stream_feedback,
        constructor_poll_question,
        sequence_questions_activated,
        constructor_sequence_answers,
    ):
        feedback_name = f"Автотест_АОСНедостижимая_{unique_suffix()}"

        with allure.step("1. Создать АОС потока по двум мероприятиям"):
            flow = created_stream_feedback(name=feedback_name)
            content_id = flow["content_id"]

        with allure.step("2. Найти автосозданные группы мероприятий/дня"):
            questions = polls_endpoint.get_questions(content_id)
            groups = {}
            for question in questions:
                groups.setdefault(question["group_id"], question["group"]["group_title"])

            group0_id = next(gid for gid, title in groups.items() if flow["first_event_name"] in title)
            day_group_id = next(gid for gid, title in groups.items() if title == "Организация учебного дня")

        with allure.step("3. Настроить ветвление так, чтобы вторая группа осталась недостижимой"):
            sequence_questions_activated(flow["attributes"])

            first_question_text = f"Автотест_АОСНедостижимаяВетвление_{unique_suffix()}"
            branch_answers = generate_single_choice_answers("Автотест_АОСНедостижимаяВДень1", "Автотест_АОСНедостижимаяВДень2")
            constructor_poll_question(
                content_id,
                text=first_question_text,
                group_id=group0_id,
                order=6,
                answers=branch_answers,
                question_sequence=constructor_sequence_answers(branch_answers, [day_group_id, day_group_id]),
            )

        with allure.step("4. Проверить в конструкторе, что вторая группа помечена недостижимой"):
            constructor_admin_page.open_constructor_by_id(env.ui_base_url, content_id)
            constructor_admin_page.assert_sequence_questions_enabled()
            constructor_admin_page.assert_feedback_group_has_no_relations(flow["second_event_name"])

        with allure.step("5. Проверить, что активация анкеты на потоке блокируется"):
            constructor_admin_page.open_stream_feedback_tab(env.ui_base_url, flow["program_id"], flow["stream_id"])
            constructor_admin_page.assert_stream_feedback_row_visible(feedback_name)
            constructor_admin_page.assert_stream_feedback_activation_blocked(feedback_name)
