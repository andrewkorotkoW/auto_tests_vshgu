"""Юнит-тесты tools/test_cases/testit_sync.py: без сети и без --env.

Парсер md -> payload проверяется на маленьком фикстурном docs/test_cases/<area>.md.
--dry-run гоняется через main() на временной директории (без .env-переменных —
скрипт обязан остаться сухим). --apply гоняется с подменённым TestItClient._session
(requests.Session-like double) — реальных HTTP-запросов ни разу не происходит.
"""
import json
from pathlib import Path

import pytest
import requests

from tools.test_cases.testit_sync import (
    TestItClient,
    TestItConfig,
    apply_area,
    autotest_tag,
    build_plan,
    build_section_payload,
    case_tags,
    load_config,
    main,
    parse_area_file,
    readable_area_title,
    tc_tag,
)

pytestmark = pytest.mark.tools

AREA_DOC = """# Тест-кейсы: widgets

| Параметр | Значение |
|---|---|
| Область | tests/api/widgets |
| Стенд | develop |
| Роли | admin |

### TC-WIDGETS-001 Админ создаёт виджет
- Автотест: tests/api/widgets/test_widgets_api.py::TestWidgetsApi::test_create_widget
- Приоритет: high   Тип: api   Роли: admin, user
- Предусловия: Нужен активный проект
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /widgets | Виджет создан |
| 2 | GET /widgets/{id} | Виджет найден |

### TC-WIDGETS-002 Виджет удаляется
- Автотест: tests/api/widgets/test_widgets_api.py::TestWidgetsApi::test_delete_widget
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | DELETE /widgets/{id} | 200 |
"""


def _write_doc(dir_path: Path, name: str = "widgets.md", content: str = AREA_DOC) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _no_real_dotenv(monkeypatch):
    """В этом репозитории .env реально существует и содержит настоящие TESTIT_* (симлинк на
    рабочий .env владельца) — без этой подмены `load_dotenv()` в testit_sync.py читал бы
    оттуда значения даже после monkeypatch.delenv, потому что python-dotenv ищет .env от
    расположения самого модуля testit_sync.py, а не от cwd теста. Тесты не должны трогать
    реальные значения ни разу — управляем окружением только через monkeypatch.setenv/delenv."""
    monkeypatch.setattr("tools.test_cases.testit_sync.load_dotenv", lambda *a, **k: None)


# --------------------------------------------------------------------------------- парсинг


def test_parse_area_file_reads_case_fields(tmp_path):
    doc_path = _write_doc(tmp_path)

    area_file = parse_area_file(doc_path)

    assert area_file.area == "widgets"
    assert area_file.title == "widgets"
    assert len(area_file.cases) == 2

    case = area_file.cases[0]
    assert case.tc_id == "TC-WIDGETS-001"
    assert case.title == "Админ создаёт виджет"
    assert case.autotest == "tests/api/widgets/test_widgets_api.py::TestWidgetsApi::test_create_widget"
    assert case.priority == "high"
    assert case.type_ == "api"
    assert case.roles == ["admin", "user"]
    assert case.precondition == "Нужен активный проект"
    assert case.testit_id is None
    assert [(s.action, s.expected) for s in case.steps] == [
        ("POST /widgets", "Виджет создан"),
        ("GET /widgets/{id}", "Виджет найден"),
    ]

    case2 = area_file.cases[1]
    assert case2.roles == []


def test_case_tags_include_area_type_roles_and_autotest(tmp_path):
    doc_path = _write_doc(tmp_path)
    area_file = parse_area_file(doc_path)
    case = area_file.cases[0]

    tags = case_tags(case, area_file.area)

    assert tags == [
        "widgets", "api", "admin", "user", f"tc:{case.tc_id}", autotest_tag(case.autotest),
    ]


def test_build_plan_maps_action_create_when_no_testit_id(tmp_path):
    doc_path = _write_doc(tmp_path)

    plans = build_plan(tmp_path, areas=None, project_id="42")

    assert len(plans) == 1
    plan = plans[0]
    assert plan.section_payload == {"projectId": "42", "name": "widgets", "parentId": None}
    assert [item.action for item in plan.items] == ["create", "create"]
    assert plan.items[0].payload["name"] == "Админ создаёт виджет"
    assert plan.items[0].payload["priority"] == "High"
    assert plan.items[0].payload["steps"] == [
        {"action": "POST /widgets", "expectedResult": "Виджет создан"},
        {"action": "GET /widgets/{id}", "expectedResult": "Виджет найден"},
    ]


def test_build_plan_maps_action_update_when_testit_id_present(tmp_path):
    doc_with_id = AREA_DOC.replace(
        "- Предусловия: Нужен активный проект",
        "- Предусловия: Нужен активный проект\n- Test IT: 777",
    )
    _write_doc(tmp_path, content=doc_with_id)

    plans = build_plan(tmp_path, areas=None, project_id="42")

    assert plans[0].items[0].action == "update"
    assert plans[0].items[1].action == "create"


def test_build_plan_filters_by_area(tmp_path):
    _write_doc(tmp_path, name="widgets.md")
    _write_doc(tmp_path, name="gadgets.md", content=AREA_DOC.replace("widgets", "gadgets"))

    plans = build_plan(tmp_path, areas={"gadgets"}, project_id=None)

    assert [p.area_file.area for p in plans] == ["gadgets"]


MANUAL_AREA_DOC = """# Тест-кейсы: mts_link — часть 13, ручные

| Параметр | Значение |
|---|---|
| Область | ручная проверка |
| Стенд | dev |
| Роли | см. кейсы ниже |

### TC-MTS-080 Настройка интеграции в карточке тенанта
- Приоритет: high   Тип: e2e   Роли: admin, tenant-admin
- Предусловия: Реальный валидный токен
- Требование: часть 13, файл.md, раздел «Прогон полного цикла», шаг 1
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Ввести токен | Токен проходит проверку |

### TC-WIDGETS-001 Автотестовый кейс с требованием
- Автотест: tests/api/widgets/test_widgets_api.py::TestWidgetsApi::test_create_widget
- Приоритет: high   Тип: api   Роли: admin
- Предусловия: Нужен активный проект
- Требование: часть 1, файл.md, раздел «Флоу»
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /widgets | Виджет создан |
"""


def test_parse_area_file_reads_manual_case_without_autotest(tmp_path):
    doc_path = _write_doc(tmp_path, name="mts.md", content=MANUAL_AREA_DOC)

    area_file = parse_area_file(doc_path)

    manual_case = area_file.cases[0]
    assert manual_case.tc_id == "TC-MTS-080"
    assert manual_case.autotest == ""
    assert manual_case.testit_id is None
    assert manual_case.requirement == "часть 13, файл.md, раздел «Прогон полного цикла», шаг 1"


def test_parse_area_file_reads_requirement_on_automated_case(tmp_path):
    doc_path = _write_doc(tmp_path, name="mts.md", content=MANUAL_AREA_DOC)

    area_file = parse_area_file(doc_path)

    automated_case = area_file.cases[1]
    assert automated_case.autotest
    assert automated_case.requirement == "часть 1, файл.md, раздел «Флоу»"


def test_case_tags_manual_case_gets_tc_tag_and_manual_instead_of_autotest(tmp_path):
    doc_path = _write_doc(tmp_path, name="mts.md", content=MANUAL_AREA_DOC)
    area_file = parse_area_file(doc_path)
    manual_case = area_file.cases[0]

    tags = case_tags(manual_case, area_file.area)

    assert tags == ["mts", "e2e", "admin", "tenant-admin", tc_tag("TC-MTS-080"), "manual"]


def test_build_plan_includes_manual_cases_without_skipping(tmp_path):
    doc_path = _write_doc(tmp_path, name="mts.md", content=MANUAL_AREA_DOC)

    plans = build_plan(tmp_path, areas=None, project_id="42")

    assert len(plans[0].items) == 2
    manual_item = plans[0].items[0]
    assert manual_item.autotest == ""
    assert manual_item.action == "create"


def test_build_work_item_payload_puts_requirement_before_precondition(tmp_path):
    doc_path = _write_doc(tmp_path, name="mts.md", content=MANUAL_AREA_DOC)

    plans = build_plan(tmp_path, areas=None, project_id="42")

    precondition_steps = plans[0].items[0].payload["preconditionSteps"]
    assert precondition_steps == [
        {"description": "Требование: часть 13, файл.md, раздел «Прогон полного цикла», шаг 1"},
        {"description": "Реальный валидный токен"},
    ]


# --------------------------------------------------------------------------------- читаемое имя секции


def test_readable_area_title_strips_numeric_prefix_and_underscores_but_keeps_order():
    assert readable_area_title("00_tenant_settings") == "00. Tenant settings"
    assert readable_area_title("13_dev_real_e2e") == "13. Dev real e2e"


def test_readable_area_title_passes_through_names_without_numeric_prefix():
    assert readable_area_title("widgets") == "widgets"


def test_parse_area_file_uses_readable_title_when_no_header_title(tmp_path):
    doc_without_header = "### TC-WIDGETS-001 Кейс без заголовка области\n- Автотест: x\n"
    doc_path = _write_doc(tmp_path, name="00_tenant_settings.md", content=doc_without_header)

    area_file = parse_area_file(doc_path)

    assert area_file.area == "00_tenant_settings"
    assert area_file.title == "00. Tenant settings"


# --------------------------------------------------------------------------------- --parent-section


def test_build_section_payload_with_parent_id():
    payload = build_section_payload("42", "mts_link — часть 0.1", parent_id="777")

    assert payload == {"projectId": "42", "name": "mts_link — часть 0.1", "parentId": "777"}


def test_build_plan_wires_parent_id_into_section_payload(tmp_path):
    doc_path = _write_doc(tmp_path)

    plans = build_plan(tmp_path, areas=None, project_id="42", parent_id="<parent-section:МТС Линк>")

    assert plans[0].section_payload == {
        "projectId": "42", "name": "widgets", "parentId": "<parent-section:МТС Линк>",
    }


def test_dry_run_with_parent_section_shows_nesting_in_export_and_stdout(tmp_path, monkeypatch, capsys):
    for name in ("TESTIT_URL", "TESTIT_TOKEN", "TESTIT_PROJECT_ID"):
        monkeypatch.delenv(name, raising=False)
    docs_dir = tmp_path / "docs" / "test_cases"
    _write_doc(docs_dir)
    export_path = tmp_path / "workspace" / "testit_export.json"

    exit_code = main([
        "--docs-dir", str(docs_dir), "--export", str(export_path),
        "--parent-section", "МТС Линк",
    ])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "МТС Линк" in captured.out
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert payload["parent_section"] == {"projectId": None, "name": "МТС Линк", "parentId": None}
    assert payload["areas"][0]["section"]["parentId"] == "<parent-section:МТС Линк>"


def test_apply_with_parent_section_creates_area_section_nested_under_parent(tmp_path, fake_client):
    client, session = fake_client
    docs_dir = tmp_path / "docs" / "test_cases"
    doc_path = _write_doc(docs_dir)
    area_file = parse_area_file(doc_path)

    parent_section = client.ensure_section("МТС Линк")
    parent_id = parent_section["id"]
    apply_area(client, area_file, parent_section_id=parent_id)

    section_posts = [body for method, url, body in session.calls if method == "POST" and url.endswith("/sections")]
    assert section_posts == [
        {"projectId": "42", "name": "МТС Линк", "parentId": None},
        {"projectId": "42", "name": "widgets", "parentId": parent_id},
    ]


def test_apply_area_section_lookup_scoped_by_parent_id_does_not_merge_same_named_sections(tmp_path, fake_client):
    """Одинаковое имя секции области в разных родителях (mts_link/p2p) не должно склеиваться."""
    client, session = fake_client
    docs_dir = tmp_path / "docs" / "test_cases"
    doc_path = _write_doc(docs_dir)
    area_file = parse_area_file(doc_path)

    section_under_other_parent = {"id": 999, "name": "widgets", "parentId": "other-parent"}
    session.sections.append(section_under_other_parent)

    apply_area(client, area_file, parent_section_id="my-parent")

    section_posts = [url for method, url, _ in session.calls if method == "POST" and url.endswith("/sections")]
    assert len(section_posts) == 1  # секция под "my-parent" не найдена среди чужих -> создана новая


# --------------------------------------------------------------------------------- --dry-run


def test_dry_run_writes_export_without_network_when_env_missing(tmp_path, monkeypatch, capsys):
    for name in ("TESTIT_URL", "TESTIT_TOKEN", "TESTIT_PROJECT_ID"):
        monkeypatch.delenv(name, raising=False)
    docs_dir = tmp_path / "docs" / "test_cases"
    _write_doc(docs_dir)
    export_path = tmp_path / "workspace" / "testit_export.json"

    exit_code = main(["--docs-dir", str(docs_dir), "--export", str(export_path)])

    assert exit_code == 0
    assert export_path.exists()
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert payload["areas"][0]["area"] == "widgets"
    assert len(payload["areas"][0]["work_items"]) == 2
    assert payload["areas"][0]["work_items"][0]["action"] == "create"

    # md-файл кейсов не тронут в сухом режиме
    assert "Test IT:" not in (docs_dir / "widgets.md").read_text(encoding="utf-8")

    captured = capsys.readouterr()
    assert "Сухой режим" in captured.out
    assert "TESTIT_URL" in captured.out  # имя недостающей переменной — можно называть


def test_dry_run_never_prints_or_exports_token_value(tmp_path, monkeypatch, capsys):
    secret = "sekret-private-token-value"
    monkeypatch.setenv("TESTIT_URL", "https://testit.example")
    monkeypatch.setenv("TESTIT_TOKEN", secret)
    monkeypatch.setenv("TESTIT_PROJECT_ID", "42")
    docs_dir = tmp_path / "docs" / "test_cases"
    _write_doc(docs_dir)
    export_path = tmp_path / "workspace" / "testit_export.json"

    exit_code = main(["--docs-dir", str(docs_dir), "--export", str(export_path)])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in export_path.read_text(encoding="utf-8")


def test_dry_run_rerun_gives_identical_plan(tmp_path, monkeypatch):
    for name in ("TESTIT_URL", "TESTIT_TOKEN", "TESTIT_PROJECT_ID"):
        monkeypatch.delenv(name, raising=False)
    docs_dir = tmp_path / "docs" / "test_cases"
    _write_doc(docs_dir)
    export_path = tmp_path / "workspace" / "testit_export.json"

    main(["--docs-dir", str(docs_dir), "--export", str(export_path)])
    first = export_path.read_text(encoding="utf-8")

    main(["--docs-dir", str(docs_dir), "--export", str(export_path)])
    second = export_path.read_text(encoding="utf-8")

    assert first == second


def test_dry_run_never_touches_requests_even_when_config_is_present(tmp_path, monkeypatch):
    """--dry-run не должен звать сеть даже когда TESTIT_* заданы — в отличие от других
    dry-run тестов здесь env-переменные заполнены, поэтому единственная гарантия отсутствия
    сети — то, что дефолтный (без --apply) режим main() никогда не создаёт TestItClient."""
    monkeypatch.setenv("TESTIT_URL", "https://testit.example")
    monkeypatch.setenv("TESTIT_TOKEN", "secret-token")
    monkeypatch.setenv("TESTIT_PROJECT_ID", "42")
    docs_dir = tmp_path / "docs" / "test_cases"
    _write_doc(docs_dir)
    export_path = tmp_path / "workspace" / "testit_export.json"

    def _boom(self, url, *a, **k):
        raise AssertionError(f"дефолтный (dry-run) режим не должен звать сеть: {url}")

    for method in ("get", "post", "put"):
        monkeypatch.setattr(requests.Session, method, _boom)
        monkeypatch.setattr(requests, method, _boom)

    exit_code = main(["--docs-dir", str(docs_dir), "--export", str(export_path)])

    assert exit_code == 0
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert payload["areas"][0]["work_items"][0]["action"] == "create"
    assert payload["areas"][0]["section"] == {
        "projectId": "42", "name": "widgets", "parentId": None,
    }


def test_load_config_reports_missing_vars(monkeypatch):
    for name in ("TESTIT_URL", "TESTIT_TOKEN", "TESTIT_PROJECT_ID"):
        monkeypatch.delenv(name, raising=False)

    config, missing = load_config()

    assert config is None
    assert set(missing) == {"TESTIT_URL", "TESTIT_TOKEN", "TESTIT_PROJECT_ID"}


def test_apply_without_env_does_not_touch_network(tmp_path, monkeypatch, capsys):
    for name in ("TESTIT_URL", "TESTIT_TOKEN", "TESTIT_PROJECT_ID"):
        monkeypatch.delenv(name, raising=False)
    docs_dir = tmp_path / "docs" / "test_cases"
    _write_doc(docs_dir)

    exit_code = main(["--docs-dir", str(docs_dir), "--apply"])

    assert exit_code == 1
    assert "Не заливаю" in capsys.readouterr().out
    assert "Test IT:" not in (docs_dir / "widgets.md").read_text(encoding="utf-8")


# --------------------------------------------------------------------------------- --apply (мок)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Минимальный requests.Session-double: пишет тела запросов, никакой сети."""

    def __init__(self):
        self.headers = {}
        self.calls = []
        self.sections = []
        self._next_id = 100

    def _new_id(self):
        self._next_id += 1
        return self._next_id

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, None))
        assert url.endswith("/sections")
        return FakeResponse(self.sections)

    def post(self, url, json=None, **kwargs):
        self.calls.append(("POST", url, json))
        if url.endswith("/sections"):
            section = {"id": self._new_id(), "name": json["name"]}
            self.sections.append(section)
            return FakeResponse(section)
        if url.endswith("/workItems/search"):
            return FakeResponse([])
        if url.endswith("/workItems"):
            return FakeResponse({"id": self._new_id(), **json})
        raise AssertionError(f"unexpected POST {url}")

    def put(self, url, json=None, **kwargs):
        self.calls.append(("PUT", url, json))
        return FakeResponse(json)


@pytest.fixture
def fake_client():
    config = TestItConfig(url="https://testit.example", token="secret-token", project_id="42")
    session = FakeSession()
    client = TestItClient(config, session=session)
    return client, session


def test_apply_creates_section_and_work_items_then_writes_id_back(tmp_path, fake_client):
    client, session = fake_client
    docs_dir = tmp_path / "docs" / "test_cases"
    doc_path = _write_doc(docs_dir)
    area_file = parse_area_file(doc_path)

    applied = apply_area(client, area_file)

    assert [a.action for a in applied] == ["create", "create"]
    assert all(a.work_item_id for a in applied)

    post_urls = [url for method, url, _ in session.calls if method == "POST"]
    assert any(u.endswith("/sections") for u in post_urls)
    assert sum(u.endswith("/workItems") for u in post_urls) == 2

    text = doc_path.read_text(encoding="utf-8")
    assert f"- Test IT: {applied[0].work_item_id}" in text
    assert f"- Test IT: {applied[1].work_item_id}" in text

    # токен не попадает ни в один payload запроса
    for _, _, body in session.calls:
        assert body is None or "secret-token" not in json.dumps(body)


def test_apply_rerun_updates_existing_by_stored_id_without_duplicate_create(tmp_path, fake_client):
    client, session = fake_client
    docs_dir = tmp_path / "docs" / "test_cases"
    doc_path = _write_doc(docs_dir)
    area_file = parse_area_file(doc_path)

    first = apply_area(client, area_file)
    assert [a.action for a in first] == ["create", "create"]

    # повторный запуск на файле, куда уже записаны id
    area_file_2 = parse_area_file(doc_path)
    second = apply_area(client, area_file_2)

    assert [a.action for a in second] == ["update", "update"]
    assert [a.work_item_id for a in second] == [a.work_item_id for a in first]

    post_work_item_calls = [url for method, url, _ in session.calls if method == "POST" and url.endswith("/workItems")]
    assert len(post_work_item_calls) == 2  # только из первого прогона, второй не создал дублей

    # секция создаётся один раз, второй прогон её находит через GET
    section_posts = [url for method, url, _ in session.calls if method == "POST" and url.endswith("/sections")]
    assert len(section_posts) == 1


SINGLE_CASE_DOC = AREA_DOC.split("### TC-WIDGETS-002")[0]


def test_apply_finds_existing_work_item_by_name_and_autotest_tag_when_id_not_stored(tmp_path, fake_client):
    client, session = fake_client
    docs_dir = tmp_path / "docs" / "test_cases"
    doc_path = _write_doc(docs_dir, content=SINGLE_CASE_DOC)
    area_file = parse_area_file(doc_path)
    case = area_file.cases[0]
    assert len(area_file.cases) == 1

    # work item уже существует в Test IT (например, залит другим прогоном), но в md id не сохранён
    remote_item = {
        "id": 555,
        "name": case.title,
        "tags": [{"name": autotest_tag(case.autotest)}],
    }
    original_search = session.post

    def post_with_existing(url, json=None, **kwargs):
        if url.endswith("/workItems/search"):
            session.calls.append(("POST", url, json))
            return FakeResponse([remote_item])
        return original_search(url, json=json, **kwargs)

    session.post = post_with_existing

    applied = apply_area(client, area_file)

    assert applied[0].action == "update"
    assert applied[0].work_item_id == "555"
    create_calls = [url for method, url, _ in session.calls if method == "POST" and url.endswith("/workItems")]
    assert create_calls == []  # не создан дубль — найден и обновлён существующий


# ------------------------------------------------------------ --apply через CLI, requests замокан на уровне класса


class _FakeTestItBackend:
    """Состояние Test IT сервера для теста ниже. В отличие от FakeSession (внедряется через
    TestItClient(session=...)), здесь requests.Session.get/post/put патчатся на уровне класса —
    так что через них проходит even the real requests.Session(), созданная внутри main()/
    TestItClient без переданного session. Так проверяется путь --apply целиком через CLI."""

    def __init__(self):
        self.sections = []
        self.work_items = {}
        self._next_id = 100
        self.calls = []

    def _new_id(self):
        self._next_id += 1
        return self._next_id

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        assert url.endswith("/sections")
        return FakeResponse(self.sections)

    def post(self, url, json=None, **kwargs):
        self.calls.append(("POST", url, json))
        if url.endswith("/sections"):
            section = {"id": self._new_id(), "name": json["name"]}
            self.sections.append(section)
            return FakeResponse(section)
        if url.endswith("/workItems/search"):
            return FakeResponse([])
        if url.endswith("/workItems"):
            item = {"id": self._new_id(), **json}
            self.work_items[item["id"]] = item
            return FakeResponse(item)
        raise AssertionError(f"unexpected POST {url}")

    def put(self, url, json=None, **kwargs):
        self.calls.append(("PUT", url, json))
        return FakeResponse(json)


def test_apply_via_cli_with_requests_session_monkeypatched_updates_on_rerun_without_duplicate(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("TESTIT_URL", "https://testit.example")
    monkeypatch.setenv("TESTIT_TOKEN", "secret-token")
    monkeypatch.setenv("TESTIT_PROJECT_ID", "42")
    docs_dir = tmp_path / "docs" / "test_cases"
    doc_path = _write_doc(docs_dir)

    backend = _FakeTestItBackend()
    monkeypatch.setattr(requests.Session, "get", lambda self, url, **k: backend.get(url, **k))
    monkeypatch.setattr(requests.Session, "post", lambda self, url, json=None, **k: backend.post(url, json=json, **k))
    monkeypatch.setattr(requests.Session, "put", lambda self, url, json=None, **k: backend.put(url, json=json, **k))

    exit_code = main(["--docs-dir", str(docs_dir), "--apply"])
    assert exit_code == 0

    create_calls_after_first = [c for c in backend.calls if c[0] == "POST" and c[1].endswith("/workItems")]
    assert len(create_calls_after_first) == 2  # по одному work item на каждый из 2 кейсов фикстуры

    text_after_first = doc_path.read_text(encoding="utf-8")
    assert text_after_first.count("- Test IT: ") == 2  # id обоих кейсов дописан в md

    # повторный --apply: id уже в md, второй прогон обязан обновить, а не создать заново
    exit_code_2 = main(["--docs-dir", str(docs_dir), "--apply"])
    assert exit_code_2 == 0

    create_calls_total = [c for c in backend.calls if c[0] == "POST" and c[1].endswith("/workItems")]
    assert len(create_calls_total) == 2  # второй прогон не добавил новых POST /workItems

    update_calls = [c for c in backend.calls if c[0] == "PUT" and "/workItems/" in c[1]]
    assert len(update_calls) == 2  # второй прогон ушёл именно в PUT /workItems/{id}

    section_create_calls = [c for c in backend.calls if c[0] == "POST" and c[1].endswith("/sections")]
    assert len(section_create_calls) == 1  # секция создана единожды, второй прогон нашёл её через GET
