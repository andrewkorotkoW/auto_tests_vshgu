"""Генератор черновиков тест-кейсов из allure-разметки автотестов.

Список тестов собирается через `pytest --collect-only` (без запуска и без импорта
тестовых файлов самим генератором); метаданные (feature/story/title/severity, маркеры,
докстринг, шаги `with allure.step(...)`) читаются статически через `ast` — файлы тестов
не импортируются и не исполняются.

Использование:
    .venv/bin/python tools/test_cases/generate.py
    .venv/bin/python tools/test_cases/generate.py --area notifications

Повторный запуск идемпотентен: кейсы ищутся по ключу `- Автотест: <node id>`, вручную
отредактированные поля (Приоритет/Роли/Предусловия/шаги) не перезаписываются. Если шаги
автотеста изменились с прошлой генерации — у заголовка кейса появляется пометка
`<!-- обновить -->`, а сам текст кейса остаётся как есть (правит человек).
"""
import argparse
import ast
import hashlib
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TESTS_DIR = REPO_ROOT / "tests"
DEFAULT_DOCS_DIR = REPO_ROOT / "docs" / "test_cases"

HEADING_RE = re.compile(r"^### (TC-([A-Za-z0-9_]+)-(\d+))\s+(.*)$")
AUTOTEST_RE = re.compile(r"^-\s*Автотест:\s*(\S+)\s*$")
STEPS_HASH_RE = re.compile(r"^<!--\s*steps-hash:\s*([0-9a-f]+)\s*-->$")
UPDATE_MARK = "<!-- обновить -->"

PRIORITY_BY_SEVERITY = {
    "BLOCKER": "high",
    "CRITICAL": "high",
    "NORMAL": "medium",
    "MINOR": "low",
    "TRIVIAL": "low",
}
DEFAULT_PRIORITY = "medium"


# --------------------------------------------------------------------------- сбор тестов


def _collect_args(tests_dir: Path) -> list[str]:
    """Аргументы для pytest --collect-only: непосредственные подкаталоги/файлы tests_dir.

    Отдельные подкаталоги вместо одного корня — чтобы в самом репозитории не сработала
    деселекция tests/tools (conftest.py прячет tools-тесты, если путь на них не указан
    явно в аргументах запуска)."""
    entries = sorted(tests_dir.iterdir(), key=lambda p: p.name)
    args = []
    for entry in entries:
        if entry.name.startswith((".", "__")):
            continue
        if entry.is_dir():
            args.append(str(entry))
        elif entry.is_file() and entry.name.startswith("test_") and entry.suffix == ".py":
            args.append(str(entry))
    return args or [str(tests_dir)]


def collect_test_node_ids(tests_dir: Path, repo_root: Path, python: str = sys.executable) -> list[str]:
    """Список node id тестов (`tests/.../test_x.py::Class::test_y`) через pytest --collect-only."""
    # -o addopts= сбрасывает -v/-q из ini конфигурации (репозиторий держит -v в addopts) —
    # иначе итоговая verbosity (ini + командная строка) непредсказуемо переключает формат
    # вывода между построчными node id и деревом/summary.
    cmd = [
        python, "-m", "pytest", "--collect-only", "-q", "-o", "addopts=",
        "-p", "no:cacheprovider", "--rootdir", str(repo_root),
    ]
    cmd += _collect_args(tests_dir)
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    node_ids = [
        line.strip()
        for line in proc.stdout.splitlines()
        if re.match(r"^\S+\.py::\S+$", line.strip())
    ]
    if not node_ids and proc.returncode not in (0, 5):
        raise RuntimeError(
            f"pytest --collect-only упал (код {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
        )
    return node_ids


# ------------------------------------------------------------------------------- область


def compute_area(rel_path: Path) -> str:
    """Область по пути теста: tests/api/<area>/... и tests/ui/<area>/... — одна область."""
    parts = rel_path.parts
    zone = parts[0]
    rest = parts[1:-1]
    if zone in ("api", "ui"):
        return rest[0] if rest else "misc"
    if zone == "e2e":
        return "e2e"
    return zone


# ------------------------------------------------------------------------- ast-разбор


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _decorator_info(dec: ast.AST) -> tuple[str, str | None] | None:
    """('ns.attr', первый строковый/атрибутный аргумент) для `ns.attr(...)` / `ns.attr`."""
    call = dec if isinstance(dec, ast.Call) else None
    target = call.func if call else dec
    dotted = _dotted_name(target)
    if dotted is None:
        return None
    arg = None
    if call and call.args:
        a0 = call.args[0]
        if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
            arg = a0.value
        elif isinstance(a0, ast.Attribute):
            arg = a0.attr
    return dotted, arg


@dataclass
class DecoratorMeta:
    feature: str | None = None
    story: str | None = None
    title: str | None = None
    severity: str | None = None
    markers: list[str] = field(default_factory=list)
    env: str | None = None


def _extract_meta(decorator_list: list[ast.AST]) -> DecoratorMeta:
    meta = DecoratorMeta()
    for dec in decorator_list:
        info = _decorator_info(dec)
        if not info:
            continue
        dotted, arg = info
        if dotted == "allure.feature":
            meta.feature = arg
        elif dotted == "allure.story":
            meta.story = arg
        elif dotted == "allure.title":
            meta.title = arg
        elif dotted == "allure.severity":
            meta.severity = arg
        elif dotted.startswith("pytest.mark."):
            name = dotted.rsplit(".", 1)[-1]
            if name == "parametrize":
                continue
            meta.markers.append(name)
            if name == "env" and arg:
                meta.env = arg
    return meta


def _extract_module_markers(tree: ast.Module) -> DecoratorMeta:
    meta = DecoratorMeta()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets):
            continue
        values = node.value.elts if isinstance(node.value, ast.List) else [node.value]
        sub = _extract_meta(values)
        meta.markers.extend(sub.markers)
        meta.env = meta.env or sub.env
    return meta


class _StepVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.steps: list[str] = []

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            ctx = item.context_expr
            if isinstance(ctx, ast.Call) and _dotted_name(ctx.func) == "allure.step" and ctx.args:
                arg = ctx.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    text = arg.value
                else:
                    try:
                        text = ast.unparse(arg)
                    except Exception:
                        text = "шаг"
                self.steps.append(" ".join(text.split()))
        self.generic_visit(node)


def _extract_steps(func_node: ast.AST) -> list[str]:
    visitor = _StepVisitor()
    visitor.visit(func_node)
    return visitor.steps


@dataclass
class TestMeta:
    title: str | None
    docstring: str | None
    severity: str | None
    markers: list[str]
    env: str | None
    steps: list[str]
    arg_names: list[str]


def parse_module(path: Path) -> dict[tuple[str | None, str], TestMeta]:
    """(class_name или None, func_name) -> TestMeta для всех test_*-функций модуля."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    module_meta = _extract_module_markers(tree)
    result: dict[tuple[str | None, str], TestMeta] = {}

    def handle_func(class_meta: DecoratorMeta, class_name: str | None, node: ast.AST) -> None:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
            return
        func_meta = _extract_meta(node.decorator_list)
        markers = list(dict.fromkeys(module_meta.markers + class_meta.markers + func_meta.markers))
        args = getattr(node.args, "args", [])
        arg_names = [a.arg for a in args if a.arg != "self"]
        result[(class_name, node.name)] = TestMeta(
            title=func_meta.title,
            docstring=ast.get_docstring(node),
            severity=func_meta.severity or class_meta.severity,
            markers=markers,
            env=func_meta.env or class_meta.env or module_meta.env,
            steps=_extract_steps(node),
            arg_names=arg_names,
        )

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            class_meta = _extract_meta(node.decorator_list)
            for item in node.body:
                handle_func(class_meta, node.name, item)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            handle_func(DecoratorMeta(), None, node)

    return result


# --------------------------------------------------------------------------- форматирование


def humanize(func_name: str) -> str:
    text = func_name[len("test_"):] if func_name.startswith("test_") else func_name
    text = text.replace("_", " ").strip()
    return text[:1].upper() + text[1:] if text else func_name


def guess_roles(arg_names: list[str]) -> str:
    roles: list[str] = []
    for arg in arg_names:
        low = arg.lower()
        if "admin" in low and "admin" not in roles:
            roles.append("admin")
        elif "teacher" in low and "teacher" not in roles:
            roles.append("teacher")
        elif "reviewer" in low and "reviewer" not in roles:
            roles.append("reviewer")
        elif "user" in low and "user" not in roles:
            roles.append("user")
    return ", ".join(roles) if roles else "-"


def guess_precondition(docstring: str | None, env: str | None) -> str:
    parts = []
    if docstring:
        parts.append(" ".join(docstring.split()))
    if env:
        parts.append(f"Требует env={env}")
    return " ".join(parts) if parts else "-"


def _esc_cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def steps_hash(steps: list[str]) -> str:
    payload = "\n".join(steps).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


@dataclass
class GeneratedCase:
    node_id: str
    area: str
    title: str
    priority: str
    type_: str
    roles: str
    precondition: str
    steps: list[str]

    def hash(self) -> str:
        return steps_hash(self.steps)

    def render_block(self, tc_id: str) -> list[str]:
        lines = [
            f"### {tc_id} {self.title}",
            f"<!-- steps-hash: {self.hash()} -->",
            f"- Автотест: {self.node_id}",
            f"- Приоритет: {self.priority}   Тип: {self.type_}   Роли: {self.roles}",
            f"- Предусловия: {self.precondition}",
            "| Шаг | Действие | Ожидаемый результат |",
            "|---|---|---|",
        ]
        steps = self.steps or ["Выполнить сценарий автотеста"]
        for i, step in enumerate(steps, 1):
            lines.append(f"| {i} | {_esc_cell(step)} | — |")
        return lines


def build_case(node_id: str, area: str, zone: str, meta: TestMeta) -> GeneratedCase:
    type_ = zone if zone in ("api", "ui", "e2e") else area
    title = meta.title or humanize(node_id.split("::")[-1].split("[")[0])
    priority = PRIORITY_BY_SEVERITY.get((meta.severity or "").upper(), DEFAULT_PRIORITY)
    roles = guess_roles(meta.arg_names)
    precondition = guess_precondition(meta.docstring, meta.env)
    return GeneratedCase(
        node_id=node_id,
        area=area,
        title=title,
        priority=priority,
        type_=type_,
        roles=roles,
        precondition=precondition,
        steps=meta.steps,
    )


# ------------------------------------------------------------------------ существующий файл


@dataclass
class ExistingCase:
    number: int
    lines: list[str]
    autotest: str | None
    steps_hash_value: str | None


def parse_existing_file(text: str) -> tuple[str, list[ExistingCase]]:
    lines = text.splitlines()
    heading_idx = [i for i, l in enumerate(lines) if HEADING_RE.match(l)]
    header = "\n".join(lines[: heading_idx[0]]) if heading_idx else text
    cases = []
    for pos, start in enumerate(heading_idx):
        end = heading_idx[pos + 1] if pos + 1 < len(heading_idx) else len(lines)
        block = lines[start:end]
        while block and block[-1].strip() == "":
            block.pop()
        m = HEADING_RE.match(block[0])
        number = int(m.group(3))
        autotest = None
        hash_value = None
        for l in block[1:]:
            am = AUTOTEST_RE.match(l.strip())
            if am:
                autotest = am.group(1)
            hm = STEPS_HASH_RE.match(l.strip())
            if hm:
                hash_value = hm.group(1)
        cases.append(ExistingCase(number=number, lines=block, autotest=autotest, steps_hash_value=hash_value))
    return header, cases


def _update_existing_block(existing: ExistingCase, fresh: GeneratedCase) -> tuple[list[str], bool]:
    """Возвращает (строки блока, изменился ли файл). Правки в тексте — только heading/hash."""
    new_hash = fresh.hash()
    lines = list(existing.lines)
    changed = False
    if existing.steps_hash_value is None:
        # Первое знакомство генератора с этим (возможно, рукописным) кейсом — просто
        # запоминаем текущий хэш, не считаем это «изменением».
        lines.insert(1, f"<!-- steps-hash: {new_hash} -->")
        changed = True
    elif existing.steps_hash_value != new_hash:
        if UPDATE_MARK not in lines[0]:
            lines[0] = f"{lines[0]} {UPDATE_MARK}"
        for i, l in enumerate(lines):
            if STEPS_HASH_RE.match(l.strip()):
                lines[i] = f"<!-- steps-hash: {new_hash} -->"
                break
        changed = True
    return lines, changed


def default_header(area: str, source_dirs: list[str]) -> str:
    dirs = ", ".join(source_dirs) if source_dirs else f"tests/api/{area}, tests/ui/{area}"
    return (
        f"# Тест-кейсы: {area}\n\n"
        "| Параметр | Значение |\n"
        "|---|---|\n"
        f"| Область | {dirs} |\n"
        "| Стенд | develop (см. README §13) |\n"
        "| Роли | см. кейсы ниже |\n\n"
        "<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей "
        "(Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->"
    )


# --------------------------------------------------------------------------------- generate


@dataclass
class AreaReport:
    new: int = 0
    updated: int = 0
    unchanged: int = 0

    @property
    def total(self) -> int:
        return self.new + self.updated + self.unchanged


def generate(tests_dir: Path = DEFAULT_TESTS_DIR, docs_dir: Path = DEFAULT_DOCS_DIR,
             repo_root: Path = REPO_ROOT, python: str = sys.executable,
             areas: set[str] | None = None) -> dict[str, AreaReport]:
    node_ids = collect_test_node_ids(tests_dir, repo_root, python=python)

    by_area: dict[str, list[tuple[str, str]]] = defaultdict(list)
    tests_rel_root = tests_dir.relative_to(repo_root)
    for node_id in node_ids:
        file_part = node_id.split("::", 1)[0]
        rel = Path(file_part).relative_to(tests_rel_root)
        area = compute_area(rel)
        if areas and area not in areas:
            continue
        by_area[area].append((node_id, rel.parts[0]))

    module_cache: dict[Path, dict[tuple[str | None, str], TestMeta]] = {}

    def meta_for(node_id: str) -> TestMeta:
        parts = node_id.split("::")
        file_part = parts[0]
        path = repo_root / file_part
        if path not in module_cache:
            module_cache[path] = parse_module(path)
        class_name, func_name = (None, parts[1]) if len(parts) == 2 else (parts[1], parts[2])
        func_name = func_name.split("[")[0]
        return module_cache[path][(class_name, func_name)]

    docs_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, AreaReport] = {}

    for area in sorted(by_area):
        area_report = AreaReport()
        doc_path = docs_dir / f"{area}.md"
        if doc_path.exists():
            header, existing_cases = parse_existing_file(doc_path.read_text(encoding="utf-8"))
        else:
            source_dirs = sorted({str(Path(nid.split("::")[0]).parent) for nid, _ in by_area[area]})
            header = default_header(area, source_dirs)
            existing_cases = []

        existing_by_autotest = {c.autotest: c for c in existing_cases if c.autotest}
        max_number = max((c.number for c in existing_cases), default=0)

        blocks: list[list[str]] = [existing.lines for existing in existing_cases]
        block_index_by_autotest = {
            c.autotest: i for i, c in enumerate(existing_cases) if c.autotest
        }

        area_code = re.sub(r"[^A-Za-z0-9]+", "_", area.upper()).strip("_")

        for node_id, zone in by_area[area]:
            meta = meta_for(node_id)
            fresh = build_case(node_id, area, zone, meta)
            existing = existing_by_autotest.get(node_id)
            if existing is None:
                max_number += 1
                tc_id = f"TC-{area_code}-{max_number:03d}"
                blocks.append(fresh.render_block(tc_id))
                area_report.new += 1
            else:
                new_lines, changed = _update_existing_block(existing, fresh)
                blocks[block_index_by_autotest[node_id]] = new_lines
                if changed:
                    area_report.updated += 1
                else:
                    area_report.unchanged += 1

        content = header.rstrip() + "\n\n" + "\n\n".join("\n".join(b) for b in blocks) + "\n"
        doc_path.write_text(content, encoding="utf-8")
        report[area] = area_report

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tests-dir", type=Path, default=DEFAULT_TESTS_DIR)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument("--area", action="append", dest="areas", help="ограничить одной или несколькими областями")
    args = parser.parse_args(argv)

    areas = set(args.areas) if args.areas else None
    report = generate(tests_dir=args.tests_dir, docs_dir=args.docs_dir, areas=areas)

    total_new = sum(r.new for r in report.values())
    total_updated = sum(r.updated for r in report.values())
    total_unchanged = sum(r.unchanged for r in report.values())
    for area, r in sorted(report.items()):
        print(f"{area}: {r.total} тестов (новых {r.new}, обновить {r.updated}, без изменений {r.unchanged})")
    print(f"Итого: {len(report)} областей, новых кейсов {total_new}, помечено <!-- обновить --> {total_updated}, "
          f"без изменений {total_unchanged}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
