"""Фикстуры для тестов конструктора тестов/опросов (админка → «Конструктор тестов
и опросов»): создание теста/опроса/вопросов через наши API-эндпоинты
(TestsEndpoint/PollsEndpoint из корневого conftest.py, QuestionBankEndpoint здесь),
темы вопросов и вопросы из банка — с обязательной очисткой после теста.

created_test/created_poll (корневой conftest.py) для конструктора не подходят один в
один: created_test удаляет тест сам, а created_poll — нет (используется в местах, где
опрос не должен переживать удаление пользователя/назначения). Здесь оба варианта
нужны как тест, так и опрос, поэтому используем tests_endpoint/polls_endpoint напрямую
и всегда снимаем созданное через mass_delete в teardown — как просит задача.
"""
from datetime import datetime, timedelta

import pytest

from api.endpoints.question_bank import QuestionBankEndpoint
from api.helpers.data_generator import (
    generate_aos_payload,
    generate_constructor_question_payload,
    generate_poll_payload,
    generate_schedule_item_payload,
    generate_single_choice_answers,
    generate_test_payload,
    unique_suffix,
)
from ui.pages.login_page import LoginPage
from ui.pages.test_constructor_admin_page import ConstructorAdminPage
from ui.pages.test_constructor_player_page import ConstructorPlayerPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@pytest.fixture
def question_bank_endpoint(api_client):
    return QuestionBankEndpoint(api_client)


@pytest.fixture
def constructor_admin_page(admin_page):
    """ConstructorAdminPage поверх уже авторизованной страницы админа (см. admin_page
    в корневом conftest.py — авторизация через storage_state, без ручного логина)."""
    return ConstructorAdminPage(admin_page)


@pytest.fixture
def constructor_player_page(user_page):
    """ConstructorPlayerPage поверх уже авторизованной страницы общего env-пользователя
    (см. user_page в корневом conftest.py) — годится там, где не важно, какой именно
    слушатель проходит тест/опрос (тест/опрос открывается напрямую по content_id, без
    индивидуального назначения). Если сценарию нужен свой ID слушателя (назначение
    теста/потока конкретному пользователю, статистика по ФИО) — используйте
    constructor_listener_page."""
    return ConstructorPlayerPage(user_page)


@pytest.fixture
def constructor_listener_page(page, prepared_user):
    """Страница и данные свежесозданного слушателя (в отличие от constructor_player_page
    поверх общего env-пользователя user_page) — нужна там, где сценарий требует именно
    того пользователя, которого мы назначили на тест/поток (assignments_endpoint/
    polls_endpoint.assign_activities). prepared_user снимает блокирующую модалку
    «данные о себе» через API; логин и закрытие тура/cookie-баннера — тем же способом,
    что и в tests/ui/aos/user/test_user_aos_flow.py (LoginPage.login +
    UserSidebarPage.dismiss_popups)."""
    user = prepared_user()
    LoginPage(page).login(user["email"], user["password"])
    UserSidebarPage(page).dismiss_popups()
    return ConstructorPlayerPage(page), user


@pytest.fixture
def created_constructor_test(tests_endpoint):
    """Создаёт тест (type=test) конструктора с уникальным именем. Удаляет после теста
    через TestsEndpoint.mass_delete."""
    content_ids = []

    def _create(**kwargs):
        payload = generate_test_payload(**kwargs)
        data = tests_endpoint.create(payload)
        content_ids.append(data["content_id"])
        return data

    yield _create

    if content_ids:
        try:
            tests_endpoint.mass_delete(content_ids)
        except Exception as e:
            logger.warning(f"Failed to mass delete constructor tests {content_ids}: {e}")


@pytest.fixture
def created_constructor_poll(polls_endpoint):
    """Создаёт опрос (type=poll) конструктора с уникальным именем. Удаляет после теста
    через PollsEndpoint.mass_delete."""
    content_ids = []

    def _create(**kwargs):
        payload = generate_poll_payload(**kwargs)
        data = polls_endpoint.create(payload)
        content_ids.append(data["content_id"])
        return data

    yield _create

    if content_ids:
        try:
            polls_endpoint.mass_delete(content_ids)
        except Exception as e:
            logger.warning(f"Failed to mass delete constructor polls {content_ids}: {e}")


@pytest.fixture
def created_question_theme(question_bank_endpoint):
    """Создаёт тему вопроса (каталог dictionaries, type=tag) с уникальным именем.
    Удаляет после теста через QuestionBankEndpoint.delete_theme."""
    theme_ids = []

    def _create(name: str = None):
        theme_name = name or f"Автотест_ТемаВопроса_{unique_suffix()}"
        data = question_bank_endpoint.create_theme(theme_name)
        theme_ids.append(data["id"])
        return data

    yield _create

    for theme_id in theme_ids:
        try:
            question_bank_endpoint.delete_theme(theme_id)
        except Exception as e:
            logger.warning(f"Failed to delete question theme {theme_id}: {e}")


@pytest.fixture
def constructor_test_question(tests_endpoint):
    """Фабрика вопросов конструктора для теста (см. generate_constructor_question_payload —
    тема/группа/доп. вопросы/последовательность), сразу отправляет PUT и возвращает вопрос."""

    def _create(content_id: int, *, text: str = None, answers: list = None, **kwargs):
        question_text = text or f"Автотест_Вопрос_{unique_suffix()}"
        payload = generate_constructor_question_payload(
            question_text=question_text,
            answers=answers or generate_single_choice_answers(),
            **kwargs,
        )
        return tests_endpoint.create_question(content_id, payload)["data"]

    return _create


@pytest.fixture
def constructor_poll_question(polls_endpoint):
    """Фабрика вопросов конструктора для опроса/АОС — как constructor_test_question,
    но через PollsEndpoint (опросы и АОС обязательно требуют поле group)."""

    def _create(content_id: int, *, text: str = None, answers: list = None, **kwargs):
        question_text = text or f"Автотест_Вопрос_{unique_suffix()}"
        payload = generate_constructor_question_payload(
            question_text=question_text,
            answers=answers or generate_single_choice_answers(),
            **kwargs,
        )
        return polls_endpoint.create_question(content_id, payload)["data"]

    return _create


@pytest.fixture
def constructor_sequence_answers():
    """Собрать question_sequence (см. generate_constructor_question_payload) для
    вопроса с последовательностью: каждому варианту ответа (answers, в том же
    порядке) — своя целевая группа перехода (target_group_ids). Чистый билдер
    данных без API-вызовов, удалять после теста нечего."""

    def _build(answers: list, target_group_ids: list) -> list:
        assert len(answers) == len(target_group_ids), "На каждый ответ нужна своя целевая группа"
        return [
            {
                "source_id": answer["id"],
                "source_type": "answer",
                "target_type": "group",
                "target_group_id": target_group_id,
            }
            for answer, target_group_id in zip(answers, target_group_ids)
        ]

    return _build


@pytest.fixture
def sequence_questions_activated(polls_endpoint):
    """Включить последовательность вопросов по ответам (settings.sequence_questions)
    для уже созданного опроса/АОС — обёртка над PollsEndpoint.set_sequence_questions."""

    def _activate(poll_data: dict, is_valid: bool = True):
        return polls_endpoint.set_sequence_questions(poll_data, is_active=True, is_valid=is_valid)

    return _activate


@pytest.fixture
def extra_questions_activated(tests_endpoint):
    """Включить доп. вопросы после неправильного ответа (settings.extra_questions)
    для уже созданного теста — обёртка над TestsEndpoint.set_extra_questions_active."""

    def _activate(test_data: dict):
        return tests_endpoint.set_extra_questions_active(test_data, is_active=True)

    return _activate


@pytest.fixture
def bank_question(question_bank_endpoint):
    """Добавляет уже созданный (через constructor_test_question/constructor_poll_question)
    вопрос в банк вопросов. Возвращает questions_bank_id и снимает его после теста
    (сам донорский тест/опрос снимается его собственной фикстурой created_constructor_*)."""
    bank_ids = []

    def _add(question_id: int, entity_type: str = "test", parent_id: int = None):
        bank_id = question_bank_endpoint.add_question_to_bank(question_id, entity_type=entity_type, parent_id=parent_id)
        bank_ids.append(bank_id)
        return bank_id

    yield _add

    if bank_ids:
        try:
            question_bank_endpoint.delete_bank_questions(bank_ids)
        except Exception as e:
            logger.warning(f"Failed to delete bank questions {bank_ids}: {e}")


@pytest.fixture
def created_stream_feedback(created_program, created_stream, created_module, schedule_items_endpoint, aos_endpoint):
    """Создаёт поток с двумя очными мероприятиями (разное время — иначе бэкенд
    отвечает 422 «Дата очного курса не может пересекаться с другими курсами в
    модуле») в одном модуле и АОС по ним (is_last_day=True). Бэкенд при создании
    такой АОС сам генерирует 4 группы вопросов конструктора: по одной на каждое
    мероприятие («Вебинар <препод> «<имя мероприятия>»») + «Организация учебного
    дня» + «Организация модуля» (та же структура, что и при создании через UI
    вкладки «Анкета обратной связи» потока — разведано на develop через
    _scout_aos_default.py). Удаляет АОС через AosEndpoint.mass_delete; поток/модуль/
    программа снимаются их собственными фикстурами."""
    content_ids = []

    def _create(name: str = None, is_active: bool = False):
        program = created_program()
        stream = created_stream(program_id=program["id"])
        module = created_module(program_id=program["id"], stream_id=stream["id"])

        suffix = unique_suffix()
        first_event_name = f"Автотест_Мероприятие1_{suffix}"
        second_event_name = f"Автотест_Мероприятие2_{suffix}"
        today = datetime.now()

        first_item = schedule_items_endpoint.create(
            program["id"], stream["id"], module["id"],
            generate_schedule_item_payload(
                name=first_event_name,
                date_time_from=today.strftime("%Y-%m-%dT10:05"),
                date_time_to=(today + timedelta(hours=1)).strftime("%Y-%m-%dT11:05"),
            ),
        )
        second_item = schedule_items_endpoint.create(
            program["id"], stream["id"], module["id"],
            generate_schedule_item_payload(
                name=second_event_name,
                date_time_from=(today + timedelta(hours=2)).strftime("%Y-%m-%dT12:05"),
                date_time_to=(today + timedelta(hours=3)).strftime("%Y-%m-%dT13:05"),
            ),
        )

        payload = generate_aos_payload(name=name, schedule_item_ids=[first_item["id"], second_item["id"]], is_last_day=True)
        aos_data = aos_endpoint.create(payload)
        content_id = aos_data["content_id"]
        content_ids.append(content_id)

        if is_active:
            assert aos_endpoint.activate(program["id"], stream["id"], content_id), f"АОС {content_id} не активировалась"

        return {
            "content_id": content_id,
            "program_id": program["id"],
            "stream_id": stream["id"],
            "first_event_name": first_event_name,
            "second_event_name": second_event_name,
            "attributes": aos_data,
        }

    yield _create

    if content_ids:
        try:
            aos_endpoint.mass_delete(content_ids)
        except Exception as e:
            logger.warning(f"Failed to mass delete stream feedback {content_ids}: {e}")
