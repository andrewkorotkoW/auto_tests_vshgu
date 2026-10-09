"""Фикстуры для tests/api/ratings (docs/qr_code_ratings_recon.md, раздел «Рейтинги/отзывы»).

entity_type для tincan-курса подобран эмпирически при подготовке этой задачи (живыми
запросами на develop, см. коммит): сырой tincan (`created_tincan`/`entity_type="activity"`)
всегда отвечает 422 "Not reviewable entity" — даже для слушателя, которому активность
назначена (`assigned_user`/`assign_activities`). Рабочий путь — обернуть tincan материалом
базы знаний типа «курс» (уже существующая в корневом conftest.py фикстура `created_course`,
которая делает именно это: created_tincan + knowledge_base_endpoint.create_course_material)
и ставить отзыв на сам материал: entity_type="knowledge_base_material",
entity_id=material["id"] (не content_id/id исходного tincan). Подтверждено живым 201."""
import requests
import pytest

from api.client import ApiClient
from api.endpoints.ratings import RatingsEndpoint
from config.environments import login
from utils.logger import logger

ENTITY_TYPE_KB_MATERIAL = "knowledge_base_material"


@pytest.fixture
def anon_api_client(env):
    """Клиент без авторизации — для проверки 401 у приватных ручек рейтингов."""
    session = requests.Session()
    return ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name)


@pytest.fixture
def second_user_ratings_endpoint(env, created_user):
    """RatingsEndpoint под настоящим вторым пользователем (отдельная сессия, не admin) —
    для проверки прав обычного слушателя (change-status доступен только admin, см.
    docs/qr_code_ratings_recon.md)."""

    def _create():
        user = created_user()
        session = login(env, user["email"], user["password"])
        client = ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name)
        return user, RatingsEndpoint(client)

    return _create


@pytest.fixture
def created_rating(ratings_endpoint):
    """Создаёт отзыв через переданный RatingsEndpoint (свой или второго пользователя)
    и гарантированно удаляет его (DELETE /ratings/my-review) после теста — на develop
    уже 65+ реальных отзывов, тесты не должны оставлять мусор."""
    created = []

    def _create(endpoint=None, **kwargs):
        ep = endpoint or ratings_endpoint
        data = ep.create_rating(**kwargs)
        created.append((ep, kwargs["entity_type"], kwargs["entity_id"]))
        return data

    yield _create

    for ep, entity_type, entity_id in created:
        try:
            ep.delete_my_review(entity_type, entity_id)
        except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
            logger.warning(f"Не удалось удалить отзыв entity_type={entity_type} entity_id={entity_id}: {exc}")
