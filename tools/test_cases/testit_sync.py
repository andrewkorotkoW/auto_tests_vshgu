"""Синхронизация `docs/test_cases/*.md` (формат `tools/test_cases/generate.py`) с Test IT.

Читает md-кейсы, для каждой области готовит секцию проекта Test IT, для каждого кейса —
work item типа «Test case» (шаги, приоритет, теги область/api-ui/роли, тег с путём
автотеста). Использует только `requests` (Test IT Public API v2, заголовок
`Authorization: PrivateToken <TESTIT_TOKEN>`) — новых зависимостей нет.

Схема запросов (`/api/v2/projects/{id}/sections`, `/api/v2/workItems`,
`/api/v2/workItems/search`) приведена по документации Test IT Public API v2; перед первым
реальным `--apply` стоит свериться со Swagger конкретного инстанса.

Режимы:
    --dry-run (по умолчанию) — без сети; печатает план и пишет `workspace/testit_export.json`
        с телами запросов (без токена — он никогда не попадает ни в payload, ни в печать).
    --apply — реальная заливка: создаёт/обновляет секции и work items, id найденного/
        созданного work item дописывает в md-файл кейса (`- Test IT: <id>`).
    --area <name> — ограничить одной областью (имя = имя файла без .md).

Идемпотентность: перед созданием work item ищется существующий по названию + тегу
`autotest:<node id>` (а если в кейсе уже записан `- Test IT: <id>` — используется он
напрямую). Повторный `--apply` обновляет найденный item, а не плодит дубли.
"""
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCS_DIR = REPO_ROOT / "docs" / "test_cases"
DEFAULT_EXPORT_PATH = REPO_ROOT / "workspace" / "testit_export.json"
TEMPLATE_FILE = "TEMPLATE.md"
# Тот же маркер, что tools/test_cases/generate.py ставит в заголовок кейса при
# рассинхроне steps-hash — дублируем строкой, чтобы `python tools/test_cases/testit_sync.py`
# работал и без repo root в PYTHONPATH (generate.py его не гарантирует при прямом запуске).
UPDATE_MARK = "<!-- обновить -->"

HEADING_RE = re.compile(r"^### (TC-[A-Za-z0-9_]+-\d+)\s+(.+)$")
AUTOTEST_RE = re.compile(r"^-\s*Автотест:\s*(\S+)\s*$")
META_RE = re.compile(r"^-\s*Приоритет:\s*(\S+)\s+Тип:\s*(\S+)\s+Роли:\s*(.*)$")
PRECONDITION_RE = re.compile(r"^-\s*Предусловия:\s*(.*)$")
TESTIT_ID_RE = re.compile(r"^-\s*Test IT:\s*(.*)$")
AREA_TITLE_RE = re.compile(r"^#\s*Тест-кейсы:\s*(.+)$")

PRIORITY_MAP = {"high": "High", "medium": "Medium", "low": "Low"}
DEFAULT_PRIORITY_API = "Medium"


# --------------------------------------------------------------------------------- парсинг


@dataclass
class CaseStep:
    action: str
    expected: str


@dataclass
class Case:
    tc_id: str
    title: str
    autotest: str
    priority: str
    type_: str
    roles: list[str]
    precondition: str
    steps: list[CaseStep]
    testit_id: str | None
    block: list[str] = field(repr=False)


@dataclass
class AreaFile:
    area: str
    title: str
    path: Path
    header: str
    cases: list[Case]


def _parse_table_row(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return None
    parts = [p.strip() for p in line[1:-1].split("|")]
    if len(parts) != 3 or not parts[0].isdigit():
        return None
    return parts[1].replace("\\|", "|"), parts[2].replace("\\|", "|")


def _parse_case_block(block: list[str]) -> Case:
    heading = HEADING_RE.match(block[0])
    tc_id = heading.group(1)
    title = heading.group(2).strip()
    if title.endswith(UPDATE_MARK):
        title = title[: -len(UPDATE_MARK)].strip()

    autotest = ""
    priority = "medium"
    type_ = "api"
    roles: list[str] = []
    precondition = "-"
    testit_id: str | None = None
    steps: list[CaseStep] = []

    for line in block[1:]:
        stripped = line.strip()
        m = AUTOTEST_RE.match(stripped)
        if m:
            autotest = m.group(1)
            continue
        m = META_RE.match(stripped)
        if m:
            priority, type_, roles_raw = m.groups()
            roles = [r.strip() for r in roles_raw.split(",") if r.strip() and r.strip() != "-"]
            continue
        m = PRECONDITION_RE.match(stripped)
        if m:
            precondition = m.group(1).strip() or "-"
            continue
        m = TESTIT_ID_RE.match(stripped)
        if m:
            testit_id = m.group(1).strip() or None
            continue
        row = _parse_table_row(stripped)
        if row:
            steps.append(CaseStep(action=row[0], expected=row[1]))

    return Case(
        tc_id=tc_id, title=title, autotest=autotest, priority=priority, type_=type_,
        roles=roles, precondition=precondition, steps=steps, testit_id=testit_id, block=block,
    )


def parse_area_file(path: Path) -> AreaFile:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    heading_idx = [i for i, l in enumerate(lines) if HEADING_RE.match(l)]
    header = "\n".join(lines[: heading_idx[0]]) if heading_idx else text

    area = path.stem
    title = area
    for line in header.splitlines():
        m = AREA_TITLE_RE.match(line.strip())
        if m:
            title = m.group(1).strip()
            break

    cases = []
    for pos, start in enumerate(heading_idx):
        end = heading_idx[pos + 1] if pos + 1 < len(heading_idx) else len(lines)
        block = lines[start:end]
        while block and block[-1].strip() == "":
            block.pop()
        cases.append(_parse_case_block(block))

    return AreaFile(area=area, title=title, path=path, header=header, cases=cases)


def iter_area_files(docs_dir: Path):
    if not docs_dir.exists():
        return
    for path in sorted(docs_dir.glob("*.md")):
        if path.name == TEMPLATE_FILE:
            continue
        yield parse_area_file(path)


def _render_area_file(area_file: AreaFile) -> str:
    body = "\n\n".join("\n".join(case.block) for case in area_file.cases)
    return area_file.header.rstrip() + "\n\n" + body + "\n"


def _set_block_testit_id(block: list[str], work_item_id: str) -> bool:
    """Дописывает/обновляет `- Test IT: <id>` в блоке кейса. True, если блок изменился."""
    new_line = f"- Test IT: {work_item_id}"
    for i, line in enumerate(block):
        if TESTIT_ID_RE.match(line.strip()):
            if line.strip() == new_line:
                return False
            block[i] = new_line
            return True
    insert_at = len(block)
    for i, line in enumerate(block):
        if PRECONDITION_RE.match(line.strip()):
            insert_at = i + 1
            break
    block.insert(insert_at, new_line)
    return True


# --------------------------------------------------------------------------------- payload


def autotest_tag(autotest: str) -> str:
    return f"autotest:{autotest}"


def case_tags(case: Case, area: str) -> list[str]:
    return [area, case.type_, *case.roles, autotest_tag(case.autotest)]


def build_section_payload(project_id: str | None, area_title: str) -> dict:
    return {"projectId": project_id, "name": area_title, "parentId": None}


def build_work_item_payload(project_id: str | None, section_id: str | None, case: Case, area: str) -> dict:
    return {
        "projectId": project_id,
        "sectionId": section_id,
        "entityTypeName": "TestCases",
        "name": case.title,
        "priority": PRIORITY_MAP.get(case.priority.lower(), DEFAULT_PRIORITY_API),
        "preconditionSteps": (
            [{"description": case.precondition}] if case.precondition and case.precondition != "-" else []
        ),
        "steps": [{"action": step.action, "expectedResult": step.expected} for step in case.steps],
        "tags": [{"name": tag} for tag in case_tags(case, area)],
    }


# --------------------------------------------------------------------------------- план


@dataclass
class PlannedItem:
    area: str
    tc_id: str
    name: str
    autotest: str
    action: str  # "create" | "update"
    payload: dict
    case: Case


@dataclass
class AreaPlan:
    area_file: AreaFile
    section_payload: dict
    items: list[PlannedItem]


def plan_area(area_file: AreaFile, project_id: str | None) -> AreaPlan:
    section_payload = build_section_payload(project_id, area_file.title)
    items = []
    for case in area_file.cases:
        if not case.autotest:
            continue
        action = "update" if case.testit_id else "create"
        payload = build_work_item_payload(project_id, None, case, area_file.area)
        items.append(PlannedItem(
            area=area_file.area, tc_id=case.tc_id, name=case.title, autotest=case.autotest,
            action=action, payload=payload, case=case,
        ))
    return AreaPlan(area_file=area_file, section_payload=section_payload, items=items)


def build_plan(docs_dir: Path, areas: set[str] | None, project_id: str | None) -> list[AreaPlan]:
    plans = []
    for area_file in iter_area_files(docs_dir):
        if areas and area_file.area not in areas:
            continue
        plans.append(plan_area(area_file, project_id))
    return plans


# ----------------------------------------------------------------------------- Test IT клиент


@dataclass
class TestItConfig:
    __test__ = False  # имя начинается с "Test" — не тестовый класс pytest

    url: str
    token: str
    project_id: str


REQUIRED_ENV_VARS = ("TESTIT_URL", "TESTIT_TOKEN", "TESTIT_PROJECT_ID")


def load_config() -> tuple[TestItConfig | None, list[str]]:
    """Конфиг из .env. Возвращает (config, missing) — missing непусто в сухом режиме."""
    load_dotenv()
    values = {name: os.getenv(name) for name in REQUIRED_ENV_VARS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        return None, missing
    return TestItConfig(
        url=values["TESTIT_URL"].rstrip("/"),
        token=values["TESTIT_TOKEN"],
        project_id=values["TESTIT_PROJECT_ID"],
    ), []


class TestItClient:
    __test__ = False  # имя начинается с "Test" — не тестовый класс pytest

    def __init__(self, config: TestItConfig, session: requests.Session | None = None):
        self.project_id = config.project_id
        self._base_url = f"{config.url}/api/v2"
        self._session = session or requests.Session()
        self._session.headers.update({
            "Authorization": f"PrivateToken {config.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def find_section(self, name: str) -> dict | None:
        resp = self._session.get(self._url(f"/projects/{self.project_id}/sections"))
        resp.raise_for_status()
        for section in resp.json() or []:
            if section.get("name") == name:
                return section
        return None

    def create_section(self, name: str) -> dict:
        resp = self._session.post(
            self._url(f"/projects/{self.project_id}/sections"),
            json=build_section_payload(self.project_id, name),
        )
        resp.raise_for_status()
        return resp.json()

    def ensure_section(self, name: str) -> dict:
        return self.find_section(name) or self.create_section(name)

    def find_work_item(self, name: str, tag: str) -> dict | None:
        resp = self._session.post(
            self._url("/workItems/search"),
            json={"filter": {"name": name, "projectIds": [self.project_id]}},
        )
        resp.raise_for_status()
        for item in resp.json() or []:
            tag_names = {t.get("name") for t in item.get("tags", [])}
            if tag in tag_names:
                return item
        return None

    def create_work_item(self, payload: dict) -> dict:
        resp = self._session.post(self._url("/workItems"), json=payload)
        resp.raise_for_status()
        return resp.json()

    def update_work_item(self, work_item_id: str, payload: dict) -> dict:
        resp = self._session.put(self._url(f"/workItems/{work_item_id}"), json={**payload, "id": work_item_id})
        resp.raise_for_status()
        return resp.json()


# --------------------------------------------------------------------------------- --apply


@dataclass
class AppliedItem:
    tc_id: str
    name: str
    action: str
    work_item_id: str


def apply_area(client: TestItClient, area_file: AreaFile) -> list[AppliedItem]:
    section = client.ensure_section(area_file.title)
    section_id = section.get("id")
    applied = []
    changed = False

    for case in area_file.cases:
        if not case.autotest:
            continue
        payload = build_work_item_payload(client.project_id, section_id, case, area_file.area)

        if case.testit_id:
            work_item = client.update_work_item(case.testit_id, payload)
            action = "update"
        else:
            existing = client.find_work_item(case.title, autotest_tag(case.autotest))
            if existing:
                work_item = client.update_work_item(existing["id"], payload)
                action = "update"
            else:
                work_item = client.create_work_item(payload)
                action = "create"

        work_item_id = str(work_item.get("id"))
        if _set_block_testit_id(case.block, work_item_id):
            changed = True
        applied.append(AppliedItem(tc_id=case.tc_id, name=case.title, action=action, work_item_id=work_item_id))

    if changed:
        area_file.path.write_text(_render_area_file(area_file), encoding="utf-8")

    return applied


# --------------------------------------------------------------------------------- CLI


def _print_dry_run_summary(plans: list[AreaPlan]) -> None:
    total_create = total_update = 0
    for plan in plans:
        create = sum(1 for item in plan.items if item.action == "create")
        update = sum(1 for item in plan.items if item.action == "update")
        total_create += create
        total_update += update
        print(f"{plan.area_file.area}: {len(plan.items)} кейсов (создать {create}, обновить {update})")
    print(f"Итого: {len(plans)} областей, создать {total_create}, обновить {total_update}")


def _export_payload(plans: list[AreaPlan]) -> dict:
    return {
        "areas": [
            {
                "area": plan.area_file.area,
                "section": plan.section_payload,
                "work_items": [
                    {
                        "tc_id": item.tc_id,
                        "action": item.action,
                        "autotest": item.autotest,
                        "existing_testit_id": item.case.testit_id,
                        "payload": item.payload,
                    }
                    for item in plan.items
                ],
            }
            for plan in plans
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument("--export", type=Path, default=DEFAULT_EXPORT_PATH)
    parser.add_argument("--area", action="append", dest="areas", help="ограничить одной или несколькими областями")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="без сети, план + workspace/testit_export.json (по умолчанию)")
    mode.add_argument("--apply", action="store_true", help="реальная заливка в Test IT")
    args = parser.parse_args(argv)

    areas = set(args.areas) if args.areas else None
    config, missing = load_config()

    if args.apply:
        if config is None:
            print("Не заливаю: не заданы переменные .env: " + ", ".join(missing))
            return 1
        client = TestItClient(config)
        for area_file in iter_area_files(args.docs_dir):
            if areas and area_file.area not in areas:
                continue
            applied = apply_area(client, area_file)
            created = sum(1 for a in applied if a.action == "create")
            updated = sum(1 for a in applied if a.action == "update")
            print(f"{area_file.area}: {len(applied)} кейсов (создано {created}, обновлено {updated})")
        return 0

    if missing:
        print("Сухой режим: не заданы переменные .env: " + ", ".join(missing))

    plans = build_plan(args.docs_dir, areas, config.project_id if config else None)
    args.export.parent.mkdir(parents=True, exist_ok=True)
    args.export.write_text(
        json.dumps(_export_payload(plans), ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    _print_dry_run_summary(plans)
    print(f"План записан в {args.export}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
