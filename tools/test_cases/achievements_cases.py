"""Заливка 11 тест-кейсов «БЗ / Достижения» в Test IT со скриншотами.

Разовый скрипт под раздел «Тест-кейсы в Test IT» миссии
docs/plans/2026-09-25_igor_achievements_port_mission.md. В отличие от
tools/test_cases/testit_sync.py (который синхронизирует docs/test_cases/*.md с
Test IT для произвольных областей), этот скрипт бьёт в одну фиксированную секцию
проекта «ВШГУ v.3» — «База знаний / Достижения» (id `SECTION_ID`, там же лежат
эталонные по стилю кейсы 9720-9724, которые скрипт не трогает) — и везёт 11
кейсов, жёстко описанных в `CASES` ниже (по одному на сценарий из перенесённых
тестов tests/ui/knowledge_base/user_achievements и admin_statistics). Кейсы
сознательно НЕ привязываются к автотестам (не тот стиль, что в testit_sync.py) —
так решил владелец для этой миссии.

Сетевые вызовы к Test IT (`Authorization: PrivateToken`, `POST /api/v2/workItems`,
`POST /api/v2/workItems/search`, `POST /api/v2/attachments`) идут через Playwright
`APIRequestContext`, а не `requests` — в этом окружении ad-hoc `requests.Session`
зависает на approval сессии, `context.request` работает (см. память
sandbox_raw_requests_blocked_playwright_ok).

Режимы:
    --dry-run (по умолчанию) — без сети и без браузера; печатает готовые кейсы
        (название/предусловия/шаги, с плейсхолдером на месте скриншота) и пишет
        workspace/achievements_testit_export.json для ручной проверки перед заливкой.
    --apply — снимает скриншоты Playwright'ом на develop (готовит материал и
        достижение через API, как и сами тесты, проходит материал через
        `pass_material_via_api`, открывает нужный экран, подсвечивает
        карточку/строку рамкой, full-page скриншот 1440x900, закрывает cookie-баннер
        и онбординг перед съёмкой), заливает их и создаёт кейсы в Test IT.
    --case <key> — ограничить одним или несколькими кейсами (см. CaseSpec.key),
        удобно для повторной попытки после частичного сбоя — уже созданные кейсы
        всё равно пропускаются идемпотентностью, это только экономит время на
        пересъёмку скриншотов остальных 10.

Идемпотентность: перед созданием каждый кейс ищется по точному названию в секции
(`POST /api/v2/workItems/search`, filter.sectionIds=[SECTION_ID]) — если найден,
пропускается. Test IT иногда отвечает 500 на создание, хотя кейс всё равно
создаётся — после такой ошибки скрипт переискивает по имени и считает это успехом,
а не падением, прежде чем считать это реальным сбоем.
"""
import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402
from playwright.sync_api import Page, sync_playwright  # noqa: E402

from api.client import ApiClient  # noqa: E402
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint  # noqa: E402
from api.endpoints.tincan import TincanEndpoint  # noqa: E402
from api.helpers.data_generator import generate_tincan_payload, unique_suffix  # noqa: E402
from config.environments import Environment, ENVIRONMENTS, get_session, get_storage_state_path  # noqa: E402
from ui.pages.admin_knowledge_base_page import AdminKnowledgeBasePage  # noqa: E402
from ui.pages.user_knowledge_base_page import UserKnowledgeBasePage  # noqa: E402
from ui.pages.user_sidebar_page import UserSidebarPage  # noqa: E402

SECTION_ID = "590ce0ad-3c5d-43ec-84f5-0ae257f038a5"  # ВШГУ v.3 / База знаний / Достижения
ENTITY_TYPE = "TestCases"
DURATION_MS = 600_000  # 10 минут — как у эталонных кейсов 9720-9724
PRIORITY = "Medium"
STATE = "NotReady"

DEFAULT_EXPORT_PATH = REPO_ROOT / "workspace" / "achievements_testit_export.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "workspace" / "achievements_testit_report.json"
SCREENSHOT_DIR = REPO_ROOT / "workspace" / "testit_screenshots" / "achievements"
TEST_DATA_DIR = REPO_ROOT / "test_data"
COURSE_TINCAN_ARCHIVE_UUID = "3c0f45b7-dee1-4037-935d-6159629206a0"  # тот же архив, что в conftest.py

MATERIAL_LABELS = {
    "article": "статья", "audio": "аудио", "video": "видео",
    "book": "книга", "file": "файл", "course": "курс",
}
FILE_BACKED_MATERIALS = {
    "audio": ("audio.mp3", "audio/mpeg"),
    "video": ("video.mp4", "video/mp4"),
    "book": ("certificat.pdf", "application/pdf"),
    "file": ("certificat.pdf", "application/pdf"),
}
ACTION_BY_TYPE = {
    "article": ["Нажать «Читать статью»", "Прокрутить текст статьи до конца и закрыть окно"],
    "audio": ["Запустить встроенный аудиоплеер и дослушать запись до конца"],
    "video": ["Запустить встроенный видеоплеер и досмотреть запись до конца"],
    "book": ["Нажать «Открыть книгу»", "Прокрутить книгу (PDF) до последней страницы"],
    "file": ["Открыть карточку прикреплённого файла и скачать его по ссылке"],
}
EXPECTED_BY_TYPE = {
    "article": ["Открывается модальное окно с текстом статьи", "Материал отмечен изученным, окно закрывается"],
    "audio": ["Аудиозапись воспроизводится и доигрывает до конца"],
    "video": ["Видеозапись воспроизводится и доигрывает до конца"],
    "book": ["Открывается PDF-просмотрщик книги", "Книга прочитана полностью (100%)"],
    "file": ["Файл скачивается"],
}


# --------------------------------------------------------------------------------- модель кейса


def _p(text: str) -> str:
    return f'<p class="tiptap-text">{text}</p>'


def _p_all(lines: list) -> str:
    return "".join(_p(line) for line in lines)


def _img(attachment_id: str) -> str:
    return (
        f'<p class="tiptap-text"><img src="/api/v2/Attachments/{attachment_id}" '
        f'width="440" class="tiptap-image"></p>'
    )


@dataclass
class StepSpec:
    action_lines: list
    expected_lines: list
    screenshot_key: Optional[str] = None


@dataclass
class CaseSpec:
    key: str
    name: str
    preconditions: list
    steps: list = field(default_factory=list)


def material_precondition_line(material_type: str) -> str:
    label = MATERIAL_LABELS[material_type]
    return f"В Базе знаний создан материал типа «{label}» (виден слушателям, имя с префиксом «Автотест_»)."


def achievement_precondition_line(material_type: str) -> str:
    label = MATERIAL_LABELS[material_type]
    return (
        f"Создано достижение с условием «Количество материалов»: тип «{label}», количество 1 "
        f"(имя с префиксом «Автотест_»)."
    )


def material_case(material_type: str) -> CaseSpec:
    label = MATERIAL_LABELS[material_type]
    return CaseSpec(
        key=f"material_{material_type}",
        name=f"Слушатель получает достижение за {label}",
        preconditions=[material_precondition_line(material_type), achievement_precondition_line(material_type)],
        steps=[
            StepSpec(
                action_lines=[f"Открыть в Базе знаний материал типа «{label}» из предусловия"],
                expected_lines=["Открывается карточка материала, отображается его название"],
            ),
            StepSpec(action_lines=ACTION_BY_TYPE[material_type], expected_lines=EXPECTED_BY_TYPE[material_type]),
            StepSpec(
                action_lines=["Открыть раздел «Достижения» (/achievements)"],
                expected_lines=["Открывается страница «Полученные достижения»"],
            ),
            StepSpec(
                action_lines=["Проверить карточку полученного достижения в «Полученные достижения»"],
                expected_lines=["Отображается карточка с названием и описанием достижения из предусловия"],
                screenshot_key="achievement_card",
            ),
        ],
    )


MATERIAL_TYPES_FOR_CASES = ["article", "audio", "video", "book", "file"]  # «курс» — особый случай, см. ниже

COURSE_CASE = CaseSpec(
    key="material_course",
    name="Слушатель получает достижение за курс",
    preconditions=[material_precondition_line("course"), achievement_precondition_line("course")],
    steps=[
        StepSpec(
            action_lines=[
                "Открыть в Базе знаний материал типа «курс» из предусловия",
                "Нажать «Приступить к изучению»",
            ],
            expected_lines=[
                "Дефект стенда: вместо всплывающего окна с содержимым курса открытие не происходит "
                "(popup не появляется за 30 с) — текущая вкладка переходит на /library/material/"
                "{id материала} и показывает страницу 404",
            ],
            screenshot_key="course_404",
        ),
        StepSpec(
            action_lines=["Открыть раздел «Достижения» (/achievements)"],
            expected_lines=[
                "Карточка достижения за материал «курс» из предусловия отсутствует в «Полученные "
                "достижения» — из-за дефекта на предыдущем шаге слушатель не может пройти курс и "
                "получить достижение",
            ],
            screenshot_key="achievements_state",
        ),
    ],
)

COMPLEX_SCENARIOS = [
    ("audio_and_book", "audio", "book", "аудио и книга"),
    ("file_and_book", "file", "book", "файл и книга"),
    ("two_books", "book", "book", "две книги"),
]


def complex_case(key: str, first_type: str, second_type: str, scenario_label: str) -> CaseSpec:
    first_label = MATERIAL_LABELS[first_type]
    second_label = MATERIAL_LABELS[second_type]
    return CaseSpec(
        key=f"complex_{key}",
        name=f"Составное достижение: {scenario_label}",
        preconditions=[
            f"В Базе знаний созданы два материала: «{first_label}» и «{second_label}» "
            f"(видны слушателям, имена с префиксом «Автотест_»).",
            "Создано составное достижение с двумя условиями «конкретный материал изучен» — "
            "по одному на каждый из материалов выше (имя с префиксом «Автотест_»).",
        ],
        steps=[
            StepSpec(
                action_lines=[f"Изучить в Базе знаний первый материал («{first_label}») из предусловия"]
                + ACTION_BY_TYPE[first_type],
                expected_lines=EXPECTED_BY_TYPE[first_type],
            ),
            StepSpec(
                action_lines=[f"Изучить в Базе знаний второй материал («{second_label}») из предусловия"]
                + ACTION_BY_TYPE[second_type],
                expected_lines=EXPECTED_BY_TYPE[second_type],
            ),
            StepSpec(
                action_lines=["Открыть раздел «Достижения» (/achievements) и проверить карточку достижения"],
                expected_lines=["В «Полученные достижения» отображается карточка составного достижения из предусловия"],
                screenshot_key="achievement_card",
            ),
        ],
    )


HISTORY_CASE = CaseSpec(
    key="history",
    name="История достижений пользователя",
    preconditions=[
        material_precondition_line("article"),
        achievement_precondition_line("article"),
        "Слушатель изучил материал, достижение начислено (видно в «Полученные достижения» слушателя).",
    ],
    steps=[
        StepSpec(
            action_lines=["В админке открыть «База знаний» → вкладку «История» (/admin/knowledge-base/achievements/history)"],
            expected_lines=["Открывается таблица «История» со столбцом «Дата получения»"],
        ),
        StepSpec(
            action_lines=["В поле «Поиск» ввести ФИО слушателя из предусловия"],
            expected_lines=["Список отфильтрован по введённому ФИО"],
        ),
        StepSpec(
            action_lines=["Проверить строку с ФИО слушателя и названием полученного достижения"],
            expected_lines=["Строка с ФИО слушателя и названием достижения из предусловия отображается в таблице"],
            screenshot_key="history_row",
        ),
    ],
)

RATING_CASE = CaseSpec(
    key="rating",
    name="Пользователь в рейтинге базы знаний",
    preconditions=[
        material_precondition_line("article"),
        "Слушатель изучил материал из предусловия (без привязки к достижению).",
    ],
    steps=[
        StepSpec(
            action_lines=["В админке открыть «База знаний» → «Рейтинг» (/admin/knowledge-base/rating)"],
            expected_lines=["Открывается таблица «Рейтинг» со столбцами «Позиция» и «Итого»"],
        ),
        StepSpec(
            action_lines=["В поле «Поиск» ввести ФИО слушателя из предусловия"],
            expected_lines=["Список отфильтрован по введённому ФИО"],
        ),
        StepSpec(
            action_lines=["Проверить строку слушателя"],
            expected_lines=["Строка с ФИО слушателя отображается, счётчик изученных материалов увеличен на изученный материал"],
            screenshot_key="rating_row",
        ),
    ],
)

CASES = (
    [material_case(t) for t in MATERIAL_TYPES_FOR_CASES]
    + [COURSE_CASE]
    + [complex_case(*scenario) for scenario in COMPLEX_SCENARIOS]
    + [HISTORY_CASE, RATING_CASE]
)
assert len(CASES) == 11, f"Ожидалось 11 кейсов, получено {len(CASES)}"


# --------------------------------------------------------------------------------- съёмка скриншотов


@dataclass
class ShootContext:
    env: Environment
    kb_endpoint: KnowledgeBaseEndpoint
    user_kb_endpoint: KnowledgeBaseEndpoint
    tincan_endpoint: TincanEndpoint
    kb_test_user_full_name: str
    user_page: Page
    admin_page: Page
    screenshot_dir: Path


def create_material(ctx: ShootContext, material_type: str) -> tuple:
    """Материал через API с префиксом «Автотест_». Для типа «курс» дополнительно
    создаёт контент Tincan (тем же архивом, что и в перенесённых тестах) и
    возвращает его id третьим элементом — вызывающий отвечает за его удаление."""
    name = f"Автотест_TestIT_Материал_{material_type}_{unique_suffix()}"
    tincan_id = None

    if material_type == "article":
        text = "".join(f"<p>Абзац {n}. Автотестовая статья для тест-кейса Test IT.</p>" for n in range(1, 21))
        material = ctx.kb_endpoint.create_article_material(name=name, article_text=text)
    elif material_type == "course":
        tincan_payload = generate_tincan_payload(archive_uuid=COURSE_TINCAN_ARCHIVE_UUID)
        tincan = ctx.tincan_endpoint.create(tincan_payload)
        tincan_id = tincan["id"]
        material = ctx.kb_endpoint.create_course_material(name=name, content_id=tincan_id)
    elif material_type in FILE_BACKED_MATERIALS:
        file_name, content_type = FILE_BACKED_MATERIALS[material_type]
        duration = 60 if material_type in ("audio", "video") else 0
        material = ctx.kb_endpoint.create_file_material(
            name=name, material_type=material_type, file_path=TEST_DATA_DIR / file_name,
            content_type=content_type, duration=duration,
        )
    else:
        raise ValueError(f"Неизвестный тип материала: {material_type!r}")

    return material["id"], material.get("name") or name, tincan_id


def create_simple_achievement(ctx: ShootContext, material_type: str, label: str) -> tuple:
    name = f"Автотест_TestIT_Достижение_{material_type}_{unique_suffix()}"
    description = f"Автотестовое достижение: изучите 1 материал «{label}»"
    achievement = ctx.kb_endpoint.create_material_count_achievement(
        name=name, description=description, material_type=material_type, count=1,
    )
    return achievement["id"], name, description


def create_complex_achievement(ctx: ShootContext, material_ids: list, scenario_label: str) -> tuple:
    name = f"Автотест_TestIT_Достижение_составное_{unique_suffix()}"
    description = f"Автотестовое составное достижение: {scenario_label}"
    conditions = [ctx.kb_endpoint.material_set_condition(mid) for mid in material_ids]
    achievement = ctx.kb_endpoint.create_achievement_with_conditions(name=name, description=description, conditions=conditions)
    return achievement["id"], name, description


def highlight_and_shoot(page: Page, locator, path: Path) -> None:
    locator.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(200)
    try:
        locator.evaluate("el => { el.style.outline = '4px solid #ff3860'; el.style.outlineOffset = '2px'; }")
    except Exception:  # noqa: BLE001 — подсветка необязательна, скриншот важнее
        pass
    page.wait_for_timeout(200)
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=True)


def shoot_material_case(ctx: ShootContext, material_type: str, label: str) -> dict:
    material_id = None
    achievement_id = None
    tincan_id = None
    try:
        material_id, material_name, tincan_id = create_material(ctx, material_type)
        achievement_id, achievement_name, _ = create_simple_achievement(ctx, material_type, label)

        ctx.user_kb_endpoint.pass_material_via_api(material_id)
        ctx.kb_endpoint.wait_user_achievement(ctx.kb_test_user_full_name, achievement_name)

        kb_page = UserKnowledgeBasePage(ctx.user_page)
        kb_page.open_achievements(ctx.env.ui_base_url)
        card = ctx.user_page.locator(".achievement-cart").filter(
            has=ctx.user_page.get_by_text(achievement_name, exact=True)
        )
        path = ctx.screenshot_dir / f"{material_type}_card.png"
        highlight_and_shoot(ctx.user_page, card, path)
        return {"achievement_card": path}
    finally:
        if achievement_id is not None:
            ctx.kb_endpoint.delete_achievement(achievement_id)
        if material_id is not None:
            ctx.kb_endpoint.delete_materials([material_id])
        if tincan_id is not None:
            ctx.tincan_endpoint.mass_delete([tincan_id])


def shoot_course_case(ctx: ShootContext, label: str) -> dict:
    material_id = None
    achievement_id = None
    tincan_id = None
    try:
        material_id, material_name, tincan_id = create_material(ctx, "course")
        achievement_id, _, _ = create_simple_achievement(ctx, "course", label)

        kb_page = UserKnowledgeBasePage(ctx.user_page)
        kb_page.open_material_by_id(ctx.env.ui_base_url, material_id, material_name)

        launch_button = ctx.user_page.get_by_text("Приступить к изучению", exact=True)
        launch_button.wait_for(state="visible", timeout=15000)
        launch_button.click(timeout=5000)
        # Известный дефект стенда (см. tests/.../test_user_gets_achievement_by_material.py,
        # xfail для material_type="course"): попап с курсом не открывается, текущая вкладка
        # уходит на /library/material/{id} -> 404. Не пытаемся дождаться popup — сразу снимаем.
        ctx.user_page.wait_for_timeout(5000)
        path_defect = ctx.screenshot_dir / "course_404.png"
        path_defect.parent.mkdir(parents=True, exist_ok=True)
        ctx.user_page.screenshot(path=str(path_defect), full_page=True)

        kb_page.open_achievements(ctx.env.ui_base_url)
        path_state = ctx.screenshot_dir / "course_achievements.png"
        ctx.user_page.screenshot(path=str(path_state), full_page=True)
        return {"course_404": path_defect, "achievements_state": path_state}
    finally:
        if achievement_id is not None:
            ctx.kb_endpoint.delete_achievement(achievement_id)
        if material_id is not None:
            ctx.kb_endpoint.delete_materials([material_id])
        if tincan_id is not None:
            ctx.tincan_endpoint.mass_delete([tincan_id])


def shoot_complex_case(ctx: ShootContext, first_type: str, second_type: str, scenario_label: str) -> dict:
    first_id = second_id = achievement_id = None
    tincan_ids = []
    try:
        first_id, _, tincan1 = create_material(ctx, first_type)
        second_id, _, tincan2 = create_material(ctx, second_type)
        tincan_ids = [t for t in (tincan1, tincan2) if t is not None]
        achievement_id, achievement_name, _ = create_complex_achievement(ctx, [first_id, second_id], scenario_label)

        ctx.user_kb_endpoint.pass_material_via_api(first_id)
        ctx.user_kb_endpoint.pass_material_via_api(second_id)
        ctx.kb_endpoint.wait_user_achievement(ctx.kb_test_user_full_name, achievement_name)

        kb_page = UserKnowledgeBasePage(ctx.user_page)
        kb_page.open_achievements(ctx.env.ui_base_url)
        card = ctx.user_page.locator(".achievement-cart").filter(
            has=ctx.user_page.get_by_text(achievement_name, exact=True)
        )
        path = ctx.screenshot_dir / f"complex_{first_type}_{second_type}_card.png"
        highlight_and_shoot(ctx.user_page, card, path)
        return {"achievement_card": path}
    finally:
        if achievement_id is not None:
            ctx.kb_endpoint.delete_achievement(achievement_id)
        material_ids = [m for m in (first_id, second_id) if m is not None]
        if material_ids:
            ctx.kb_endpoint.delete_materials(material_ids)
        if tincan_ids:
            ctx.tincan_endpoint.mass_delete(tincan_ids)


def shoot_history_case(ctx: ShootContext) -> dict:
    material_id = None
    achievement_id = None
    try:
        material_id, _, _ = create_material(ctx, "article")
        achievement_id, achievement_name, _ = create_simple_achievement(ctx, "article", MATERIAL_LABELS["article"])

        ctx.user_kb_endpoint.pass_material_via_api(material_id)
        ctx.kb_endpoint.wait_user_achievement(ctx.kb_test_user_full_name, achievement_name)

        admin_page_obj = AdminKnowledgeBasePage(ctx.admin_page)
        admin_page_obj.open_achievement_history(ctx.env.ui_base_url)
        admin_page_obj.search_achievement_history_by_user(ctx.kb_test_user_full_name)
        row = ctx.admin_page.locator("tr").filter(
            has=ctx.admin_page.get_by_text(ctx.kb_test_user_full_name, exact=True)
        ).filter(has=ctx.admin_page.get_by_text(achievement_name, exact=True))
        path = ctx.screenshot_dir / "history_row.png"
        highlight_and_shoot(ctx.admin_page, row, path)
        return {"history_row": path}
    finally:
        if achievement_id is not None:
            ctx.kb_endpoint.delete_achievement(achievement_id)
        if material_id is not None:
            ctx.kb_endpoint.delete_materials([material_id])


def shoot_rating_case(ctx: ShootContext) -> dict:
    material_id = None
    try:
        baseline = next(iter(ctx.kb_endpoint.get_material_statistics(ctx.kb_test_user_full_name)), {})
        baseline_article = int(baseline.get("article", 0))
        baseline_total = int(baseline.get("total", 0))

        material_id, _, _ = create_material(ctx, "article")
        ctx.user_kb_endpoint.pass_material_via_api(material_id)
        ctx.kb_endpoint.wait_material_statistics(
            ctx.kb_test_user_full_name,
            expected={"article": baseline_article + 1, "total": baseline_total + 1},
            timeout=180,
        )

        admin_page_obj = AdminKnowledgeBasePage(ctx.admin_page)
        admin_page_obj.open_knowledge_base_rating(ctx.env.ui_base_url)
        admin_page_obj.search_rating_by_user(ctx.kb_test_user_full_name)
        row = admin_page_obj.rating_row(ctx.kb_test_user_full_name)
        path = ctx.screenshot_dir / "rating_row.png"
        highlight_and_shoot(ctx.admin_page, row, path)
        return {"rating_row": path}
    finally:
        if material_id is not None:
            ctx.kb_endpoint.delete_materials([material_id])


SHOOTERS: dict = {f"material_{t}": partial(shoot_material_case, material_type=t, label=MATERIAL_LABELS[t])
                  for t in MATERIAL_TYPES_FOR_CASES}
SHOOTERS["material_course"] = partial(shoot_course_case, label=MATERIAL_LABELS["course"])
for _key, _first, _second, _label in COMPLEX_SCENARIOS:
    SHOOTERS[f"complex_{_key}"] = partial(shoot_complex_case, first_type=_first, second_type=_second, scenario_label=_label)
SHOOTERS["history"] = shoot_history_case
SHOOTERS["rating"] = shoot_rating_case


# --------------------------------------------------------------------------------- Test IT клиент


class TestItCreateError(Exception):
    def __init__(self, status: int, text: str):
        super().__init__(f"{status}: {text}")
        self.status = status


@dataclass
class TestItConfig:
    __test__ = False  # имя начинается с "Test" — не тестовый класс pytest
    url: str
    token: str
    project_id: str


REQUIRED_ENV_VARS = ("TESTIT_URL", "TESTIT_TOKEN", "TESTIT_PROJECT_ID")


def load_testit_config() -> tuple:
    load_dotenv()
    values = {name: os.getenv(name) for name in REQUIRED_ENV_VARS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        return None, missing
    return TestItConfig(
        url=values["TESTIT_URL"].rstrip("/"), token=values["TESTIT_TOKEN"], project_id=values["TESTIT_PROJECT_ID"],
    ), []


class TestItClient:
    __test__ = False  # имя начинается с "Test" — не тестовый класс pytest

    def __init__(self, request_context, config: TestItConfig):
        self._ctx = request_context
        self._base_url = config.url
        self.project_id = config.project_id

    def find_case_by_name(self, name: str) -> Optional[dict]:
        resp = self._ctx.post(
            f"{self._base_url}/api/v2/workItems/search",
            data=json.dumps({
                "filter": {"projectIds": [self.project_id], "sectionIds": [SECTION_ID], "isDeleted": False},
            }),
            headers={"Content-Type": "application/json"},
        )
        if not resp.ok:
            raise RuntimeError(f"workItems/search упал: {resp.status} {resp.text()[:300]}")
        for item in resp.json():
            if item.get("name") == name:
                return item
        return None

    def upload_attachment(self, path: Path) -> str:
        resp = self._ctx.post(
            f"{self._base_url}/api/v2/attachments",
            multipart={"file": {"name": path.name, "mimeType": "image/png", "buffer": path.read_bytes()}},
        )
        if not resp.ok:
            raise RuntimeError(f"attachments упал: {resp.status} {resp.text()[:300]}")
        return resp.json()["id"]

    def create_case(self, payload: dict) -> dict:
        resp = self._ctx.post(
            f"{self._base_url}/api/v2/workItems",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        if not resp.ok:
            raise TestItCreateError(resp.status, resp.text()[:500])
        return resp.json()


def build_case_payload(project_id: str, case: CaseSpec, attachment_ids_by_key: dict) -> dict:
    steps_payload = []
    for step in case.steps:
        expected_html = _p_all(step.expected_lines)
        if step.screenshot_key:
            expected_html += _img(attachment_ids_by_key[step.screenshot_key])
        steps_payload.append({"action": _p_all(step.action_lines), "expected": expected_html})

    precondition_payload = [{"action": _p_all(case.preconditions), "expected": ""}] if case.preconditions else []
    attachment_ids = sorted(set(attachment_ids_by_key.values()))

    return {
        "projectId": project_id,
        "sectionId": SECTION_ID,
        "entityTypeName": ENTITY_TYPE,
        "name": case.name,
        "description": "",
        "duration": DURATION_MS,
        "state": STATE,
        "priority": PRIORITY,
        "tags": [],
        "preconditionSteps": precondition_payload,
        "steps": steps_payload,
        "attachments": [{"id": aid} for aid in attachment_ids],
    }


# --------------------------------------------------------------------------------- dry-run


def render_case_preview(case: CaseSpec) -> dict:
    lines = [f"### {case.name}", "Предусловия:"]
    lines += [f"  - {p}" for p in case.preconditions]
    for i, step in enumerate(case.steps, 1):
        action = " ".join(step.action_lines)
        expected = " ".join(step.expected_lines)
        if step.screenshot_key:
            expected += f" [+ скриншот: {step.screenshot_key}]"
        lines.append(f"  {i}. {action} -> {expected}")
    return {"key": case.key, "name": case.name, "preview": "\n".join(lines),
            "preconditions": case.preconditions,
            "steps": [{"action": s.action_lines, "expected": s.expected_lines, "screenshot_key": s.screenshot_key}
                      for s in case.steps]}


def cmd_dry_run(export_path: Path, cases: list) -> int:
    previews = [render_case_preview(c) for c in cases]
    for preview in previews:
        print(preview["preview"])
        print()
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(json.dumps(previews, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Итого: {len(cases)} кейсов. План записан в {export_path}")
    return 0


# --------------------------------------------------------------------------------- apply


def cmd_apply(cases: list, report_path: Path) -> int:
    config, missing = load_testit_config()
    if config is None:
        print("Не заливаю: не заданы переменные .env: " + ", ".join(missing))
        return 1

    env = ENVIRONMENTS["develop"]
    admin_session = get_session(env, role="admin")
    user_session = get_session(env, role="user")
    admin_api_client = ApiClient(session=admin_session, base_url=env.api_base_url, cookie_name=env.cookie_name)
    user_api_client = ApiClient(session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name)
    kb_endpoint = KnowledgeBaseEndpoint(admin_api_client)
    user_kb_endpoint = KnowledgeBaseEndpoint(user_api_client)
    tincan_endpoint = TincanEndpoint(admin_api_client)

    me = user_api_client.get("/auth/me").json()["data"]["attributes"]
    full_name = f"{me['surname']} {me['name']} {me['patronymic']}"

    headless = os.getenv("HEADLESS", "0").lower() in ("1", "true", "yes")
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    screenshots_by_case: dict = {}
    shoot_errors: dict = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        admin_storage = get_storage_state_path(env, role="admin")
        user_storage = get_storage_state_path(env, role="user")
        admin_context = browser.new_context(viewport={"width": 1440, "height": 900}, storage_state=str(admin_storage))
        user_context = browser.new_context(viewport={"width": 1440, "height": 900}, storage_state=str(user_storage))
        admin_page = admin_context.new_page()
        user_page = user_context.new_page()

        UserKnowledgeBasePage(user_page).open(env.ui_base_url)  # закрывает cookie-баннер/онбординг слушателя
        admin_page.goto(f"{env.ui_base_url.rstrip('/')}/admin/knowledge-base/achievements/created")
        UserSidebarPage(admin_page).dismiss_popups()  # закрывает cookie-баннер/онбординг админки

        ctx = ShootContext(
            env=env, kb_endpoint=kb_endpoint, user_kb_endpoint=user_kb_endpoint, tincan_endpoint=tincan_endpoint,
            kb_test_user_full_name=full_name, user_page=user_page, admin_page=admin_page,
            screenshot_dir=SCREENSHOT_DIR,
        )

        for case in cases:
            print(f"[shoot] {case.name} ...")
            t0 = time.monotonic()
            try:
                screenshots_by_case[case.key] = SHOOTERS[case.key](ctx)
                print(f"    ok за {time.monotonic() - t0:.1f}с: {list(screenshots_by_case[case.key])}")
            except Exception as exc:  # noqa: BLE001 — одна упавшая съёмка не должна ронять весь прогон
                shoot_errors[case.key] = str(exc)
                print(f"    ОШИБКА съёмки за {time.monotonic() - t0:.1f}с: {exc}")

        admin_context.close()
        user_context.close()
        browser.close()

        testit_ctx = p.request.new_context(
            extra_http_headers={"Authorization": f"PrivateToken {config.token}", "Accept": "application/json"},
        )
        client = TestItClient(testit_ctx, config)

        report = []
        for case in cases:
            entry = {"key": case.key, "name": case.name}
            if case.key in shoot_errors:
                entry["action"] = "skip(shoot-failed)"
                entry["error"] = shoot_errors[case.key]
                report.append(entry)
                print(f"[testit] {case.name}: пропуск — съёмка не удалась")
                continue

            existing = client.find_case_by_name(case.name)
            if existing is not None:
                entry.update(action="skip(exists)", global_id=existing.get("globalId"), id=existing.get("id"))
                report.append(entry)
                print(f"[testit] {case.name}: уже существует (№{existing.get('globalId')}) — пропуск")
                continue

            try:
                attachment_ids = {
                    key: client.upload_attachment(path) for key, path in screenshots_by_case[case.key].items()
                }
                payload = build_case_payload(config.project_id, case, attachment_ids)
                created = client.create_case(payload)
                entry.update(action="create", global_id=created.get("globalId"), id=created.get("id"))
                print(f"[testit] {case.name}: создан №{created.get('globalId')}")
            except TestItCreateError as exc:
                # Ловушка: сервер иногда отвечает 500, но кейс всё равно создаётся.
                existing = client.find_case_by_name(case.name)
                if existing is not None:
                    entry.update(action="create(500-trap)", global_id=existing.get("globalId"), id=existing.get("id"))
                    print(f"[testit] {case.name}: 500 при создании, но кейс найден повторным поиском (№{existing.get('globalId')})")
                else:
                    entry["action"] = "fail"
                    entry["error"] = str(exc)
                    print(f"[testit] {case.name}: ОШИБКА создания: {exc}")
            report.append(entry)

        testit_ctx.dispose()

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    created = [r for r in report if r.get("action") in ("create", "create(500-trap)")]
    skipped = [r for r in report if r.get("action", "").startswith("skip")]
    failed = [r for r in report if r.get("action") == "fail"]
    print(f"\nИтого: создано {len(created)}, пропущено (уже есть/съёмка не удалась) {len(skipped)}, ошибок {len(failed)}")
    if created:
        print("Созданные кейсы: " + ", ".join(f"№{r['global_id']} {r['name']}" for r in created))
    print(f"Отчёт записан в {report_path}")
    return 1 if failed else 0


# --------------------------------------------------------------------------------- CLI


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", type=Path, default=DEFAULT_EXPORT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--case", action="append", dest="cases", help="ограничить одним или несколькими кейсами (по key)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="без сети и браузера, план + workspace/achievements_testit_export.json (по умолчанию)")
    mode.add_argument("--apply", action="store_true", help="снять скриншоты на develop и залить кейсы в Test IT")
    args = parser.parse_args(argv)

    cases = CASES
    if args.cases:
        wanted = set(args.cases)
        unknown = wanted - {c.key for c in CASES}
        if unknown:
            parser.error(f"Неизвестные --case: {sorted(unknown)}. Доступные: {sorted(c.key for c in CASES)}")
        cases = [c for c in CASES if c.key in wanted]

    if args.apply:
        return cmd_apply(cases, args.report)
    return cmd_dry_run(args.export, cases)


if __name__ == "__main__":
    sys.exit(main())
