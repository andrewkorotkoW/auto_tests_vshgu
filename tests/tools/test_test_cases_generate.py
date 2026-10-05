"""Юнит-тесты tools/test_cases/generate.py: без сети, без --env, без .env/токенов.

Строит маленькое фикстурное дерево tests/ во временной директории (не тот
tests/, что в корне репозитория) и гоняет generate() как обычный вызов
функции — она сама поднимает pytest --collect-only на фикстурном дереве.
Тестовые тела внутри фикстур никогда не исполняются (--collect-only), так что
никакой сети/стенда/логина не требуется.
"""
import re
import sys
from pathlib import Path

import pytest

from tools.test_cases.generate import UPDATE_MARK, compute_area, generate

pytestmark = pytest.mark.tools

API_WIDGET_TEST = '''\
import allure
import pytest


@allure.feature("Виджеты")
@allure.story("CRUD")
class TestWidgetsApi:

    @allure.title("Админ создаёт виджет")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    def test_create_widget(self, admin_session):
        """Виджет создаётся через POST /widgets."""
        with allure.step("POST /widgets с валидным телом"):
            pass
        with allure.step("GET /widgets/{id} возвращает созданный виджет"):
            pass

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    def test_delete_widget(self, admin_session):
        with allure.step("DELETE /widgets/{id}"):
            pass
'''

API_WIDGET_TEST_STEP_CHANGED = API_WIDGET_TEST.replace(
    'with allure.step("POST /widgets с валидным телом"):',
    'with allure.step("POST /widgets с валидным телом и project_id"):',
)

UI_WIDGET_TEST = '''\
import allure
import pytest


@allure.feature("Виджеты")
class TestWidgetsUi:

    @pytest.mark.ui
    def test_widget_visible_to_user(self, user_page):
        pass
'''

UI_WIDGET_TEST_WITH_NEW_TEST = '''\
import allure
import pytest


@allure.feature("Виджеты")
class TestWidgetsUi:

    @pytest.mark.ui
    def test_widget_visible_to_user(self, user_page):
        pass

    @pytest.mark.ui
    def test_widget_hidden_for_guest(self, guest_page):
        with allure.step("Гость не видит виджет в списке"):
            pass
'''

HANDWRITTEN_DOC = """# Тест-кейсы: widgets

| Параметр | Значение |
|---|---|
| Область | tests/api/widgets, tests/ui/widgets |
| Стенд | develop |
| Роли | admin |

### TC-WIDGETS-001 Админ создаёт виджет (ручной кейс)
- Автотест: tests/api/widgets/test_widgets_api.py::TestWidgetsApi::test_create_widget
- Приоритет: custom   Тип: api   Роли: admin
- Предусловия: написано руками до генератора
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть админку | Форма создания виджета видна |
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _write(tmp_path / "tests" / "api" / "widgets" / "test_widgets_api.py", API_WIDGET_TEST)
    _write(tmp_path / "tests" / "ui" / "widgets" / "test_widgets_ui.py", UI_WIDGET_TEST)
    return tmp_path


def _run(repo: Path, **kwargs) -> dict:
    return generate(
        tests_dir=repo / "tests",
        docs_dir=repo / "docs" / "test_cases",
        repo_root=repo,
        python=sys.executable,
        **kwargs,
    )


def test_compute_area_merges_api_and_ui_zones_and_handles_edge_cases():
    assert compute_area(Path("api/notifications/test_x.py")) == "notifications"
    assert compute_area(Path("ui/notifications/admin/test_x.py")) == "notifications"
    assert compute_area(Path("e2e/api/test_x.py")) == "e2e"
    assert compute_area(Path("e2e/ui/test_x.py")) == "e2e"
    assert compute_area(Path("api/test_health.py")) == "misc"
    assert compute_area(Path("tools/test_lib.py")) == "tools"


@pytest.mark.xfail(
    strict=False,
    reason="дефект generate.py: для теста прямо в корне tests/ (не в подпапке api/ui/e2e/...) "
    "compute_area возвращает имя файла с расширением '.py' как область (сейчас в реальном "
    "tests/ таких файлов нет, поэтому дефект не проявляется на боевом дереве)",
)
def test_compute_area_for_root_level_test_file_has_no_py_suffix():
    assert compute_area(Path("test_smoke.py")) == "test_smoke"


def test_generates_file_per_area_with_expected_case_ids_and_fields(repo):
    report = _run(repo)

    doc_path = repo / "docs" / "test_cases" / "widgets.md"
    assert doc_path.exists()
    text = doc_path.read_text(encoding="utf-8")

    assert "### TC-WIDGETS-001 Админ создаёт виджет" in text
    assert "### TC-WIDGETS-002" in text
    assert "### TC-WIDGETS-003" in text
    assert "- Автотест: tests/api/widgets/test_widgets_api.py::TestWidgetsApi::test_create_widget" in text
    assert "- Автотест: tests/api/widgets/test_widgets_api.py::TestWidgetsApi::test_delete_widget" in text
    assert "- Автотест: tests/ui/widgets/test_widgets_ui.py::TestWidgetsUi::test_widget_visible_to_user" in text
    assert "- Приоритет: high   Тип: api   Роли: admin" in text  # CRITICAL -> high
    assert "- Приоритет: medium   Тип: api   Роли: admin" in text  # NORMAL -> medium
    assert "- Приоритет: medium   Тип: ui   Роли: user" in text  # без severity -> дефолт
    assert "- Предусловия: Виджет создаётся через POST /widgets." in text  # из докстринга
    assert "| 1 | POST /widgets с валидным телом | — |" in text
    assert "| 2 | GET /widgets/{id} возвращает созданный виджет | — |" in text

    assert report["widgets"].new == 3
    assert report["widgets"].updated == 0
    assert report["widgets"].unchanged == 0


def test_idempotent_rerun_without_source_changes(repo):
    _run(repo)
    doc_path = repo / "docs" / "test_cases" / "widgets.md"
    first = doc_path.read_text(encoding="utf-8")

    report = _run(repo)

    assert doc_path.read_text(encoding="utf-8") == first
    assert report["widgets"].new == 0
    assert report["widgets"].updated == 0
    assert report["widgets"].unchanged == 3


def test_manual_edits_to_text_fields_survive_rerun(repo):
    _run(repo)
    doc_path = repo / "docs" / "test_cases" / "widgets.md"
    text = doc_path.read_text(encoding="utf-8")
    edited = text.replace(
        "- Приоритет: high   Тип: api   Роли: admin",
        "- Приоритет: критично-для-релиза   Тип: api   Роли: admin, руководитель проекта",
    )
    assert edited != text
    doc_path.write_text(edited, encoding="utf-8")

    report = _run(repo)

    result = doc_path.read_text(encoding="utf-8")
    assert "критично-для-релиза" in result
    assert "Роли: admin, руководитель проекта" in result
    assert report["widgets"].unchanged == 3
    assert report["widgets"].new == 0


def test_changed_steps_flag_update_without_rewriting_manual_fields(repo):
    _run(repo)
    doc_path = repo / "docs" / "test_cases" / "widgets.md"
    text = doc_path.read_text(encoding="utf-8")
    edited = text.replace(
        "- Предусловия: Виджет создаётся через POST /widgets.",
        "- Предусловия: Виджет создаётся через POST /widgets. Нужен активный проект.",
    )
    doc_path.write_text(edited, encoding="utf-8")

    (repo / "tests" / "api" / "widgets" / "test_widgets_api.py").write_text(
        API_WIDGET_TEST_STEP_CHANGED, encoding="utf-8"
    )

    report = _run(repo)
    result = doc_path.read_text(encoding="utf-8")

    assert f"### TC-WIDGETS-001 Админ создаёт виджет {UPDATE_MARK}" in result
    assert "TC-WIDGETS-002" in result and not re.search(r"TC-WIDGETS-002[^\n]*" + re.escape(UPDATE_MARK), result)
    assert "TC-WIDGETS-003" in result and not re.search(r"TC-WIDGETS-003[^\n]*" + re.escape(UPDATE_MARK), result)
    # ручная правка предусловий не тронута
    assert "Нужен активный проект." in result
    # таблица шагов не перезаписывается автоматически — старый текст остаётся до правки человеком
    assert "| 1 | POST /widgets с валидным телом | — |" in result
    assert "POST /widgets с валидным телом и project_id" not in result

    assert report["widgets"].updated == 1
    assert report["widgets"].unchanged == 2
    assert report["widgets"].new == 0


def test_new_autotest_appends_next_number_without_reordering(repo):
    _run(repo)

    (repo / "tests" / "ui" / "widgets" / "test_widgets_ui.py").write_text(
        UI_WIDGET_TEST_WITH_NEW_TEST, encoding="utf-8"
    )

    report = _run(repo)
    result = (repo / "docs" / "test_cases" / "widgets.md").read_text(encoding="utf-8")

    assert "### TC-WIDGETS-004" in result
    assert "- Автотест: tests/ui/widgets/test_widgets_ui.py::TestWidgetsUi::test_widget_hidden_for_guest" in result
    assert result.index("TC-WIDGETS-003") < result.index("TC-WIDGETS-004")
    for n in ("001", "002", "003"):
        assert UPDATE_MARK not in result.split(f"TC-WIDGETS-{n}")[1].split("###")[0]

    assert report["widgets"].new == 1
    assert report["widgets"].updated == 0
    assert report["widgets"].unchanged == 3


def test_adopts_hand_authored_case_without_steps_hash_without_flagging_update(repo):
    doc_path = repo / "docs" / "test_cases" / "widgets.md"
    _write(doc_path, HANDWRITTEN_DOC)

    report = _run(repo)
    result = doc_path.read_text(encoding="utf-8")

    assert "### TC-WIDGETS-001 Админ создаёт виджет (ручной кейс)" in result
    assert UPDATE_MARK not in result.split("TC-WIDGETS-001")[1].split("###")[0]
    assert "custom" in result
    assert "написано руками до генератора" in result
    assert "<!-- steps-hash:" in result  # генератор впервые запомнил fingerprint шагов

    assert "### TC-WIDGETS-002" in result
    assert "### TC-WIDGETS-003" in result
    assert report["widgets"].new == 2
    assert report["widgets"].updated == 1  # добавление steps-hash к ручному кейсу
    assert report["widgets"].unchanged == 0
