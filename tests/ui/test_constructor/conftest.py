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
import pytest

from api.endpoints.question_bank import QuestionBankEndpoint
from api.helpers.data_generator import (
    generate_constructor_question_payload,
    generate_poll_payload,
    generate_single_choice_answers,
    generate_test_payload,
    unique_suffix,
)
from ui.pages.test_constructor_admin_page import ConstructorAdminPage
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
