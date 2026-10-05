"""Обобщённое прохождение опроса/АОС слушателем по последовательности вопросов
поверх ui.pages.test_constructor_player_page.ConstructorPlayerPage — по образцу
эталонного сценария tests/ui/aos/user/test_aos_public_link.py (группы вопросов на
одной странице, «Ответить» → «Перейти к следующей группе» → «Завершить», финальный
экран «Спасибо за прохождение опроса!»), но с поддержкой веток конструктора:
доп. вопросы по теме после неверного ответа в тесте и пропуск необязательной группы
по ответу в опросе/АОС. Проверка недостижимой группы при активации — сценарий на
стороне админки (см. ConstructorAdminPage.assert_stream_feedback_activation_blocked),
сюда не относится: до неё дело не доходит, слушатель такую АОС не открывает.

Функции без allure.step внутри (как и в Page Object, см. докстринг
ui/pages/test_constructor_player_page.py) — шаги логирует вызывающий тест.
"""
from typing import List

from ui.pages.test_constructor_player_page import ConstructorPlayerPage


def pass_group_sequence_by_answer(
    player_page: ConstructorPlayerPage,
    *,
    start_question_text: str,
    branch_answer_text: str,
    target_question_text: str,
    skipped_question_text: str = None,
) -> None:
    """Пройти стартовую группу опроса/АОС с последовательностью вопросов по
    ответам: выбранный вариант (branch_answer_text) должен перевести сразу в
    целевую группу (target_question_text), минуя промежуточную
    (skipped_question_text, если задана — проверяем, что она не показана)."""
    player_page.assert_question_visible(start_question_text)
    has_next_group = player_page.answer_current_group(branch_answer_text)
    assert has_next_group, "После стартовой группы должен быть переход дальше по последовательности"
    player_page.assert_question_visible(target_question_text)
    if skipped_question_text:
        player_page.assert_question_not_visible(skipped_question_text)


def pass_test_with_additional_questions(
    player_page: ConstructorPlayerPage,
    *,
    main_question_text: str,
    wrong_answer_text: str,
    additional_questions: List[str],
    additional_correct_answer_text: str,
) -> None:
    """Пройти тест с доп. вопросами по теме после неправильного ответа на основной
    вопрос: основной вопрос отвечается заведомо неверно (wrong_answer_text), после
    чего по очереди появляются additional_questions — каждый отвечается верно
    (additional_correct_answer_text), на последнем тест завершается."""
    player_page.assert_question_visible(main_question_text)
    player_page.answer_question(wrong_answer_text)

    for index, question_text in enumerate(additional_questions):
        player_page.go_to_next_question()
        player_page.assert_question_visible(question_text)
        if index == len(additional_questions) - 1:
            player_page.answer_question(additional_correct_answer_text)
            player_page.finish_test()
        else:
            player_page.answer_question(additional_correct_answer_text)


def pass_all_groups(player_page: ConstructorPlayerPage, max_groups: int = 10) -> None:
    """Полное прохождение опроса/АОС без проверки конкретных вопросов по пути —
    доответить все группы до «Завершить» и подтвердить финальный экран."""
    player_page.answer_groups_until_finish(max_groups=max_groups)
    player_page.finish_survey()
