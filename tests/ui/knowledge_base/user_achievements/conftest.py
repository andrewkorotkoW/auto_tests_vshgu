"""Общие фикстуры для тестов «слушатель получает достижение»: подготовка материала через
API (по типу), достижения (простого или составного) и их удаление даже при падении теста.

Перенос achievement_prepare_api.py / knowledge_base_material_prepare_api.py / cleanup_manager.py
коллеги (репозиторий lms, feature/dashboard-autotests) на наш слой: KnowledgeBaseEndpoint
вместо requests-хелперов, created_tincan вместо ручной загрузки архива, обычные фикстуры
с yield-teardown вместо CleanupManager.
"""
from pathlib import Path

import pytest

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from config.environments import build_storage_state, login

from api.client import ApiClient
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.helpers.data_generator import unique_suffix
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[4] / "test_data"

# На develop UI-действие (скролл статьи/книги, воспроизведение аудио/видео, скачивание файла)
# не всегда порождает сетевой запрос о прогрессе — эмпирически проверено на типе «книга»
# (PDF-viewer прокручивается до 100%, но achievements/users не видит завершения и за 120с
# ожидания). Поэтому во всех тестах user_achievements/* после UI-действия завершение
# материала дополнительно подтверждается через API (KnowledgeBaseEndpoint.pass_material_via_api
# от имени слушателя, см. user_api_client) — это не подмена UI-проверки (UI-действие всё
# равно выполняется), а детерминированное условие для получения достижения.

# Ключ — тип материала как в API, значение — файл test_data для типов с контентным файлом.
FILE_BACKED_MATERIALS = {
    "audio": ("audio.mp3", "audio/mpeg"),
    "video": ("video.mp4", "video/mp4"),
    "book": ("certificat.pdf", "application/pdf"),
    "file": ("certificat.pdf", "application/pdf"),
}


@pytest.fixture
def kb_endpoint(api_client):
    return KnowledgeBaseEndpoint(api_client)


@pytest.fixture
def kb_user(env, created_user):
    """Свежий слушатель на каждый тест достижений. Раньше тесты шли под общим аккаунтом
    user_session: на странице «Достижения» в «Полученных» показывается не больше 6 карточек
    без пагинации, а у общего аккаунта накопились десятки полученных достижений (11 completed на
    07.10) — новое достижение в параллельном прогоне не попадало в видимые 6, тест падал
    (test_user_gets_achievement_by_material[audio] в полном прогоне 07.10). У свежего пользователя
    в «Полученных» ровно одно достижение, и счётчики рейтинга/статистики не делятся с другими
    тестами."""
    user = created_user()
    prepare_user_for_tests_via_api(env, user["email"], user["password"])
    session = login(env, user["email"], user["password"])
    return {"user": user, "session": session}


@pytest.fixture
def user_api_client(env, kb_user):
    """API-клиент от имени свежего слушателя (kb_user) — для действий, которые должен
    выполнять сам пользователь (запуск/завершение изучения материала), в отличие от
    api_client (админ), которым готовятся данные."""
    return ApiClient(session=kb_user["session"], base_url=env.api_base_url, cookie_name=env.cookie_name)


@pytest.fixture
def user_page(browser, env, kb_user, build_context_kwargs, apply_env_timeouts):
    """Страница Playwright под свежим слушателем kb_user (переопределяет корневой user_page
    для тестов достижений)."""
    storage_state = build_storage_state(env, kb_user["session"])
    context = browser.new_context(**build_context_kwargs(storage_state))
    apply_env_timeouts(context)
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def kb_test_user_full_name(kb_user):
    """ФИО свежего слушателя — для поиска в истории/рейтинге админки."""
    u = kb_user["user"]
    return f"{u['surname']} {u['name']} {u['patronymic']}"


@pytest.fixture
def material_for_type(kb_endpoint, created_tincan, tincan_endpoint):
    """Создаёт материал БЗ нужного типа через API с префиксом «Автотест_» и возвращает
    (material_id, material_name). Удаляет все созданные материалы после теста, даже если
    тест упал. Материал создаётся видимым напрямую в payload (is_visible=True) — в отличие
    от создания через форму админки (там материал по умолчанию скрыт, см. память
    kb_article_hidden_by_default), toggle-visibility здесь не нужен: это чистый тоггл вне
    зависимости от переданного значения, и вызов на уже видимом материале скрывает его
    обратно (найдено при переносе — POST вернул is_visible=true, PATCH toggle — is_visible=false)."""
    created_ids = []

    def _create(material_type: str) -> tuple:
        name = f"Автотест_Материал_{material_type}_{unique_suffix()}"

        if material_type == "article":
            article_text = "".join(
                f"<p>Абзац {number}. Текст автотестовой статьи для проверки достижений.</p>"
                for number in range(1, 41)
            )
            material = kb_endpoint.create_article_material(name=name, article_text=article_text)
        elif material_type == "course":
            # Архив загружаем заново: у контента с захардкоженным archive_uuid ручка
            # /content/launch/{id} отвечает 404 «курс не найден», и портал уводит вкладку на /404
            # (проверено 25.09.2026 на develop; со свежим архивом launch → 200 и курс открывается
            # в новом окне, как у материала 469).
            archive_uuid = tincan_endpoint.upload_archive("test_data/course_tincan.zip")
            tincan = created_tincan(archive_uuid=archive_uuid)
            material = kb_endpoint.create_course_material(name=name, content_id=tincan["id"])
        elif material_type in FILE_BACKED_MATERIALS:
            file_name, content_type = FILE_BACKED_MATERIALS[material_type]
            duration = 60 if material_type in ("audio", "video") else 0
            material = kb_endpoint.create_file_material(
                name=name,
                material_type=material_type,
                file_path=TEST_DATA_DIR / file_name,
                content_type=content_type,
                duration=duration,
            )
        else:
            raise ValueError(f"Неизвестный тип материала: {material_type!r}")

        material_id = material["id"]
        created_ids.append(material_id)
        return material_id, material.get("name") or name

    yield _create

    for material_id in reversed(created_ids):
        try:
            kb_endpoint.delete_materials([material_id])
        except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
            logger.warning(f"Не удалось удалить материал БЗ id={material_id}: {exc}")


@pytest.fixture
def achievement_for(kb_endpoint):
    """Создаёт достижение через API с префиксом «Автотест_» и возвращает
    (achievement_id, achievement_name). Без material_ids — простое достижение «количество
    материалов заданного типа» (material_type/count); с material_ids — составное достижение
    из нескольких условий «конкретный материал изучен» (material_set). Удаляет после теста
    даже при падении."""
    created_ids = []

    def _create(*, description: str, material_type: str = None, count: int = 1,
                material_ids: list = None) -> tuple:
        if material_ids:
            name = f"Автотест_Достижение_составное_{unique_suffix()}"
            conditions = [kb_endpoint.material_set_condition(material_id) for material_id in material_ids]
            achievement = kb_endpoint.create_achievement_with_conditions(
                name=name, description=description, conditions=conditions,
            )
        else:
            name = f"Автотест_Достижение_{material_type}_{unique_suffix()}"
            achievement = kb_endpoint.create_material_count_achievement(
                name=name, description=description, material_type=material_type, count=count,
            )

        achievement_id = achievement["id"]
        created_ids.append(achievement_id)
        return achievement_id, achievement.get("name") or name

    yield _create

    for achievement_id in reversed(created_ids):
        try:
            kb_endpoint.delete_achievement(achievement_id)
        except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
            logger.warning(f"Не удалось удалить достижение id={achievement_id}: {exc}")
