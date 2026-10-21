"""Единый CLI генератора тестовых данных.

    .venv/bin/python test_data_generation/generate.py --list
    .venv/bin/python test_data_generation/generate.py --scenario cas --env develop --dry-run
    .venv/bin/python test_data_generation/generate.py --scenario users --env develop --count 2
    .venv/bin/python test_data_generation/generate.py --cleanup test_data_generation/manifests/develop_cas_....json

Машинный режим (так CLI зовёт test_hub, вкладка «Данные» проекта): --list --json печатает
JSON-список сценариев; --json при --scenario/--cleanup добавляет в конце stdout строку
«__TH_DATAGEN_RESULT__ {json}» с манифестом/итогом удаления и не бросает исключение наружу
(код возврата 1); --manifest-out PATH кладёт манифест по заданному пути (и частичный при
сбое) вместо test_data_generation/manifests/<env>_<scenario>_<ts>.json.

Владелец задачи: --env stage должен корректно собираться и работать, но сам агент
не запускает ничего с --env stage — это прогоняется только вручную владельцем.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # repo root: api/, config/
sys.path.insert(0, os.path.dirname(__file__))  # test_data_generation/: lib, scenarios

from config.environments import ENVIRONMENTS  # noqa: E402
from utils.logger import logger  # noqa: E402

from lib import Ctx, Manifest, build_clients  # noqa: E402
from scenarios import (  # noqa: E402
    achievements,
    activities,
    aos,
    banner_and_partners,
    buk,
    cas,
    certificates,
    courses,
    demo,
    homework,
    individual_track,
    learner_progress,
    lpd,
    materials,
    polls,
    program_full,
    scorm,
    tests,
    users,
)

# Порядок регистрации = порядок в --list и в селекте test_hub: сценарии идут подряд по
# категориям (см. CATEGORIES ниже), чтобы группы не чередовались.
SCENARIOS = {
    "users": users,
    "program_full": program_full,
    "learner_progress": learner_progress,
    "individual_track": individual_track,
    "activities": activities,
    "tests": tests,
    "polls": polls,
    "aos": aos,
    "homework": homework,
    "courses": courses,
    "scorm": scorm,
    "lpd": lpd,
    "materials": materials,
    "achievements": achievements,
    "certificates": certificates,
    "cas": cas,
    "buk": buk,
    "banner_and_partners": banner_and_partners,
    "demo": demo,
}

# Что означает --count для сценариев, у модуля которых нет своей константы COUNT_HELP
# (новые сценарии объявляют её сами) — показывается в --list и в форме test_hub.
COUNT_HELP = {
    "cas": "пользователей на каждый статус зачисления",
    "users": "пользователей на каждую роль (шесть ролей)",
    "program_full": "слушателей в потоке",
    "activities": "активностей каждого типа",
    "learner_progress": "слушателей",
    "buk": "пользователей для сопоставления с БУК",
    "certificates": "не используется",
    "banner_and_partners": "пользователей с доступом Alpina/MIF",
    "demo": "не используется (count=1 на каждый шаг)",
}

# Категория и короткое человеческое название сценария — для группировки в --list и в
# селекте test_hub (вкладка «Данные»): по имени вроде program_full не всегда ясно, что получишь.
CATEGORIES = {
    "users": ("Пользователи и программы", "Пользователи по ролям"),
    "program_full": ("Пользователи и программы", "Программа с потоком, слушателями и сертификатом"),
    "learner_progress": ("Пользователи и программы", "Слушатели на программе с ДЗ"),
    "individual_track": ("Пользователи и программы", "Слушатели с активностями на инд. треке"),
    "activities": ("Активности", "Все типы активностей в модуле"),
    "tests": ("Активности", "Тесты"),
    "polls": ("Активности", "Опросы"),
    "aos": ("Активности", "Анкеты обратной связи (АОС)"),
    "homework": ("Активности", "Практические задания (3 типа оценки)"),
    "courses": ("Активности", "Курсы Tincan + материал БЗ"),
    "scorm": ("Активности", "Курсы SCORM"),
    "lpd": ("Активности", "LPD (только stage)"),
    "materials": ("База знаний", "Материалы всех типов"),
    "achievements": ("База знаний", "Достижения"),
    "certificates": ("Сертификаты", "Шаблоны сертификатов (поток и активность)"),
    "cas": ("Интеграции", "CAS: программа, поток, слушатели по статусам"),
    "buk": ("Интеграции", "БУК: пользователи на сопоставление"),
    "banner_and_partners": ("Интеграции", "Инфо-баннер + доступ Alpina/MIF"),
    "demo": ("Наборы", "Демо-наполнение стенда"),
}

# Маркер строки с JSON-итогом в stdout при --json: test_hub (app/core/datagen.py) читает
# объединённый stdout/stderr subprocess построчно и разбирает только строку с этим префиксом.
RESULT_MARKER = "__TH_DATAGEN_RESULT__"

MANIFESTS_DIR = Path(__file__).resolve().parent / "manifests"


def scenario_info(name: str, module) -> dict:
    category, title = CATEGORIES.get(name, (getattr(module, "CATEGORY", "Прочее"), getattr(module, "TITLE", name)))
    return {
        "name": name,
        "title": title,
        "category": category,
        "description": module.DESCRIPTION,
        "count_help": getattr(module, "COUNT_HELP", COUNT_HELP.get(name, "см. описание")),
    }


def list_scenarios(as_json: bool = False) -> None:
    infos = [scenario_info(name, module) for name, module in SCENARIOS.items()]
    if as_json:
        print(json.dumps(infos, ensure_ascii=False))
        return
    print("Зарегистрированные сценарии (по категориям):")
    current = None
    for info in infos:
        if info["category"] != current:
            current = info["category"]
            print(f"\n[{current}]")
        print(f"  {info['name']:18} {info['title']} — {info['description']}")
        print(f"  {'':18} --count: {info['count_help']}")


def _unescape(text: str) -> str:
    """Бэкенд экранирует кириллицу в JSON (\\u041f…) — в заметках манифеста и логе
    читаемее настоящие буквы."""
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)


def emit_result(args, payload: dict) -> None:
    """Последняя строка stdout при --json — «__TH_DATAGEN_RESULT__ {json}» (см. RESULT_MARKER)."""
    if getattr(args, "json", False):
        print(f"{RESULT_MARKER} {json.dumps(payload, ensure_ascii=False)}", flush=True)


def run_scenario(args) -> int:
    module = SCENARIOS.get(args.scenario)
    if module is None:
        print(f"Неизвестный сценарий: {args.scenario}. Доступны: {', '.join(SCENARIOS)}")
        return 2

    env = ENVIRONMENTS[args.env]
    logger.info(f"Сценарий: {args.scenario}, окружение: {env.name} ({env.api_base_url}), "
                f"count={args.count}, dry_run={args.dry_run}")

    api_client, cas_client, global_client = build_clients(env, dry_run=args.dry_run)
    manifest = Manifest(env.name, args.scenario)
    ctx = Ctx(
        env=env,
        api_client=api_client,
        cas_client=cas_client,
        global_client=global_client,
        count=args.count,
        tenant=args.tenant,
        prefix=args.prefix,
        manifest=manifest,
        dry_run=args.dry_run,
    )

    try:
        module.run(ctx)
    except Exception as exc:  # noqa: BLE001 — при --json сбой уходит в JSON-итог, иначе наружу как раньше
        logger.error(f"Сценарий {args.scenario} упал, создано до сбоя: {len(manifest.created)}")
        path = None
        if manifest.created and not args.dry_run:
            path = (Path(args.manifest_out) if args.manifest_out
                    else MANIFESTS_DIR / f"{env.name}_{args.scenario}_{int(time.time())}_partial.json")
            manifest.save(path)
            logger.error(f"Манифест частично созданных сущностей сохранён: {path}")
        if not args.json:
            raise
        emit_result(args, {
            "ok": False, "partial": True, "error": f"{type(exc).__name__}: {exc}",
            "manifest_path": str(path) if path else None, "manifest": manifest.to_dict(),
        })
        return 1

    print("\nИтог:")
    print(f"{'сущность':22} {'id':30} примечание")
    for entry in manifest.created:
        print(f"{entry['entity']:22} {str(entry['id']):30} {entry['how_to_delete']}")

    if manifest.skipped:
        print("\nОсознанно пропущено:")
        for entry in manifest.skipped:
            print(f"  {entry['entity']:22} {entry['reason']}")

    if args.dry_run:
        print("\ndry-run: манифест не сохраняется — сетевых вызовов не было, удалять нечего.")
        emit_result(args, {"ok": True, "dry_run": True, "manifest_path": None, "manifest": manifest.to_dict()})
        return 0

    path = Path(args.manifest_out) if args.manifest_out else MANIFESTS_DIR / f"{env.name}_{args.scenario}_{int(time.time())}.json"
    manifest.save(path)
    print(f"\nМанифест сохранён: {path}")
    emit_result(args, {"ok": True, "dry_run": False, "manifest_path": str(path), "manifest": manifest.to_dict()})
    return 0


def _cleanup_handlers(api_client, cas_client, env):
    """entity -> функция(id) -> bool|None. None означает «нет DELETE-метода»."""
    from api.endpoints.alpina import AlpinaEndpoint
    from api.endpoints.aos import AosEndpoint
    from api.endpoints.assignments import AssignmentsEndpoint
    from api.endpoints.certificates import CertificatesEndpoint
    from api.endpoints.external_buk import ExternalBukEndpoint
    from api.endpoints.external_cas import ExternalCasEndpoint
    from api.endpoints.external_content import ExternalContentEndpoint
    from api.endpoints.homework import HomeworkEndpoint
    from api.endpoints.homework_pass_fail import HomeworkPassFailEndpoint
    from api.endpoints.homework_ten_point import HomeworkTenPointEndpoint
    from api.endpoints.info_banner import InfoBannerEndpoint
    from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
    from api.endpoints.lpd import LpdEndpoint
    from api.endpoints.mif import MifEndpoint
    from api.endpoints.modules import ModulesEndpoint
    from api.endpoints.omt_cas import OmtCasEndpoint
    from api.endpoints.polls import PollsEndpoint
    from api.endpoints.programs import ProgramsEndpoint
    from api.endpoints.schedule_items import ScheduleItemsEndpoint
    from api.endpoints.streams import StreamsEndpoint
    from api.endpoints.tests import TestsEndpoint
    from api.endpoints.tincan import TincanEndpoint
    from api.endpoints.users import UsersEndpoint

    users_ep = UsersEndpoint(api_client)
    assignments_ep = AssignmentsEndpoint(api_client)
    programs_ep = ProgramsEndpoint(api_client)
    streams_ep = StreamsEndpoint(api_client)
    modules_ep = ModulesEndpoint(api_client)
    schedule_ep = ScheduleItemsEndpoint(api_client)
    certificates_ep = CertificatesEndpoint(api_client)
    omt_ep = OmtCasEndpoint(api_client)
    ext_ep = ExternalCasEndpoint(cas_client)
    tincan_ep = TincanEndpoint(api_client)
    ext_content_ep = ExternalContentEndpoint(api_client)
    hw_ep = HomeworkEndpoint(api_client)
    hw10_ep = HomeworkTenPointEndpoint(api_client)
    hwpf_ep = HomeworkPassFailEndpoint(api_client)
    tests_ep = TestsEndpoint(api_client)
    polls_ep = PollsEndpoint(api_client)
    aos_ep = AosEndpoint(api_client)
    lpd_ep = LpdEndpoint(api_client)
    kb_ep = KnowledgeBaseEndpoint(api_client)
    banner_ep = InfoBannerEndpoint(api_client)
    alpina_ep = AlpinaEndpoint(api_client)
    mif_ep = MifEndpoint(api_client)

    def _dismiss_cas(id_):
        """Снятие зачисления CAS. Два случая, когда 422 от dismiss — не провал:
        - пользователь уже удалён (повторный --cleanup после частичного: «Пользователь N
          должен быть синхронизирован», GET /users/{id} → 404) — назначения больше нет;
        - бэкенд отвечает «Удаление назначений невозможно: есть назначения со статусом …»
          (зачисление приказом нельзя снять через dismiss) — следующая запись манифеста
          удаляет самого пользователя, и назначение уходит вместе с ним."""
        stream_id, user_id = id_
        try:
            return ext_ep.dismiss_assignments(stream_id, [user_id]) is not None
        except AssertionError as exc:
            message = _unescape(str(exc))
            if api_client.get(f"/users/{user_id}").status_code == 404:
                logger.info(f"   пользователь {user_id} уже удалён — зачисление снято вместе с ним")
                return True
            if "невозможно" in message:
                logger.info(f"   dismiss отклонён ({message[:120]}…) — зачисление снимется при удалении пользователя")
                return True
            raise

    def _detach_individual(id_):
        """Снятие активностей с инд. трека. В манифесте individual_track запись стоит сразу
        после слушателей, поэтому к моменту detach сами активности уже удалены (см.
        комментарий в scenarios/individual_track.py) — если detach на удалённый контент
        отвечает ошибкой, но всех content_ids на стенде уже нет, назначений тоже нет."""
        content_ids, user_ids = id_
        if assignments_ep.detach_from_individual(content_ids, user_ids):
            return True
        return all(api_client.get(f"/content/{content_id}").status_code == 404 for content_id in content_ids)

    def _delete_buk_user(buk_user_id):
        if not env.buk_token:
            raise RuntimeError(f"нет модуля на этом окружении ({env.name.upper()}_BUK_TOKEN не задан в .env)")
        import requests
        from api.client import ApiClient

        session = requests.Session()
        session.headers["Authorization"] = env.buk_token
        buk_client = ApiClient(session=session, base_url=env.api_base_url)
        ExternalBukEndpoint(buk_client).delete_user(buk_user_id)
        return True

    return {
        "cas_tenant_org_location": lambda id_: omt_ep.delete_tenant_org_location(id_),
        "cas_program": lambda id_: ext_ep.delete_program(id_),
        "cas_stream": lambda id_: ext_ep.delete_stream(*id_),
        "cas_module": lambda id_: modules_ep.delete(*id_),
        "cas_user": lambda id_: users_ep.delete(id_),
        "cas_assignment": _dismiss_cas,
        "user": lambda id_: users_ep.delete(id_),
        # DELETE /programs/{id} отдаёт 405 (Supported methods: GET, HEAD, PUT) — рабочий способ
        # удалить одну программу это mass-delete с одним id.
        "program": lambda id_: programs_ep.mass_delete([id_]),
        "stream": lambda id_: streams_ep.delete(*id_),
        "module": lambda id_: modules_ep.delete(*id_),
        "schedule_item": lambda id_: schedule_ep.delete(*id_),
        "certificate_template": lambda id_: certificates_ep.delete_templates([id_]),
        "stream_assignment": None,
        "certificate_assignment": None,
        # id = [content_ids, user_ids]; detach идёт первым (манифест разбирается с конца),
        # затем удаляются сами активности и пользователи.
        "individual_assignment": _detach_individual,
        "tincan": lambda id_: tincan_ep.mass_delete([id_]),
        "scorm": lambda id_: tincan_ep.mass_delete([id_]),
        "external_content": lambda id_: ext_content_ep.delete(id_),
        "homework_five_point": lambda id_: hw_ep.mass_delete([id_]),
        "homework_ten_point": lambda id_: hw10_ep.mass_delete([id_]),
        "homework_pass_fail": lambda id_: hwpf_ep.mass_delete([id_]),
        "test": lambda id_: tests_ep.mass_delete([id_]),
        "poll": lambda id_: polls_ep.mass_delete([id_]),
        "aos": lambda id_: aos_ep.mass_delete([id_]),
        "lpd": lambda id_: lpd_ep.mass_delete([id_]),
        "knowledge_base_material": lambda id_: kb_ep.delete_materials([id_]),
        "achievement": lambda id_: kb_ep.delete_achievement(id_),
        "buk_user": _delete_buk_user,
        "info_banner": lambda id_: banner_ep.toggle(is_active=False),
        "alpina_access": lambda id_: bool(alpina_ep.set_status(id_, status=False)),
        "mif_access": lambda id_: bool(mif_ep.set_access(id_, access=False)),
    }


# Как проверить, что сущности уже нет на стенде (повторный --cleanup после частичного,
# ручное удаление в админке): GET по этому пути отвечает 404. entity -> шаблон пути по id
# (составной id подставляется позиционно). Для тестов/опросов/АОС отдельного GET нет.
_EXISTENCE_PROBES = {
    "user": "/users/{0}",
    "cas_user": "/users/{0}",
    "program": "/programs/{0}",
    "stream": "/programs/{0}/streams/{1}",
    "module": "/programs/{0}/streams/{1}/modules/{2}",
    "cas_module": "/programs/{0}/streams/{1}/modules/{2}",
    "tincan": "/content/{0}",
    "scorm": "/content/{0}",
    "external_content": "/content/{0}",
    "homework_five_point": "/content/{0}",
    "homework_ten_point": "/content/{0}",
    "homework_pass_fail": "/content/{0}",
    "lpd": "/content/{0}",
}


def _already_gone(entity: str, id_, api_client, cas_client, error: str) -> bool:
    """Провал удаления — не провал, если сущности уже нет: GET отвечает 404, либо для
    синхронизации CAS бэкенд говорит «должен(а) быть синхронизирован(а)» — синк уже снят
    (delete_program/delete_stream возвращают False без текста ответа, поэтому запрос
    повторяется напрямую, чтобы прочитать тело 400)."""
    if entity in ("cas_program", "cas_stream"):
        if "синхронизирован" in error:
            return True
        path = (f"/external/cas/sync/programs/{id_}" if entity == "cas_program"
                else f"/external/cas/sync/programs/{id_[0]}/streams/{id_[1]}")
        try:
            resp = cas_client.delete(path)
        except Exception:  # noqa: BLE001
            return False
        return resp.status_code == 400 and "синхронизирован" in _unescape(resp.text)
    template = _EXISTENCE_PROBES.get(entity)
    if template is None:
        return False
    parts = id_ if isinstance(id_, (list, tuple)) else [id_]
    try:
        return api_client.get(template.format(*parts)).status_code == 404
    except Exception:  # noqa: BLE001 — проверка вспомогательная, не должна ронять cleanup
        return False


def _delete_entries(entries, handlers, api_client, cas_client):
    """Удаляет записи манифеста в обратном порядке создания. Возвращает
    (ok, failed, skipped, results) — results в формате JSON-итога (--json)."""
    print(f"{'сущность':22} {'id':30} результат")
    ok, failed, skipped = 0, 0, 0
    results = []
    for entry in reversed(entries):
        entity, id_, note = entry["entity"], entry["id"], entry["how_to_delete"]
        handler = handlers.get(entity)
        if handler is None:
            print(f"{entity:22} {str(id_):30} пропущено — нет DELETE-метода ({note})")
            skipped += 1
            results.append({"entity": entity, "id": id_, "status": "skipped", "note": note})
            continue
        error = ""
        try:
            success = bool(handler(id_))
        except Exception as exc:  # noqa: BLE001 — репортим и продолжаем удалять остальное
            success = False
            error = _unescape(str(exc))
            note = f"{note}; ошибка: {error}"
        gone = False
        if not success and _already_gone(entity, id_, api_client, cas_client, error):
            success, gone = True, True
        if success:
            ok += 1
            print(f"{entity:22} {str(id_):30} {'уже отсутствует' if gone else 'удалено'}")
            results.append({"entity": entity, "id": id_, "status": "deleted",
                            "note": "уже отсутствовало на стенде" if gone else None})
        else:
            failed += 1
            print(f"{entity:22} {str(id_):30} НЕ удалено ({note})")
            results.append({"entity": entity, "id": id_, "status": "failed", "note": note})
    print(f"\nУдалено: {ok}, не удалено: {failed}, пропущено (нет DELETE): {skipped}")
    return ok, failed, skipped, results


def run_cleanup(args) -> int:
    manifest_path = Path(args.cleanup)
    manifest = Manifest.load(manifest_path)
    env = ENVIRONMENTS[manifest.env]
    logger.info(f"Cleanup манифеста {manifest_path} (env={env.name}, scenario={manifest.scenario}, "
                f"{len(manifest.created)} записей, в обратном порядке создания)")

    if args.dry_run:
        for entry in reversed(manifest.created):
            logger.info(f"[dry-run] был бы удалён {entry['entity']} id={entry['id']} ({entry['how_to_delete']})")
        emit_result(args, {"ok": True, "dry_run": True, "deleted": 0, "failed": 0, "skipped": 0, "results": []})
        return 0

    api_client, cas_client, _ = build_clients(env, dry_run=False)
    handlers = _cleanup_handlers(api_client, cas_client, env)

    if manifest.skipped:
        print("Ранее осознанно пропущено (нечего удалять):")
        for entry in manifest.skipped:
            print(f"  {entry['entity']:22} {entry['reason']}")
        print()

    ok, failed, skipped, results = _delete_entries(manifest.created, handlers, api_client, cas_client)
    emit_result(args, {
        "ok": failed == 0, "dry_run": False, "deleted": ok, "failed": failed, "skipped": skipped,
        "results": results, "manifest_path": str(manifest_path),
    })
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------- очистка после прогона автотестов

# Данные автотестов на стенде: имена сущностей (api/helpers/data_generator.py — «Автотест_…»,
# программы некоторых тестов — «API-test_…»/«E2E_…») и email пользователей (random_email —
# «auto_test_…», сценарий cas — «cas_user_…»).
AUTOTEST_NAME_PREFIXES = ("Автотест", "API-test", "E2E")
AUTOTEST_EMAIL_PREFIXES = ("auto_test_", "cas_user_")
CLEANUP_AFTER_RUN_SCENARIO = "cleanup_after_run"

# /activities отдаёт content_type; удаляются через те же обработчики, что и в манифестах
# сценариев. Неизвестный тип идёт в tincan.mass_delete — это общий /content mass-delete.
_ACTIVITY_ENTITY = {
    "course-tincan": "tincan",
    "scorm": "scorm",
    "homework": "homework_five_point",
    "external_content": "external_content",
    "lpd": "lpd",
}
_TEST_ENTITY = {"test": "test", "poll": "poll", "feedback": "aos"}


def _parse_since(value: str):
    """--since из test_hub — runs.started, локальное время машины без зоны (ISO)."""
    from datetime import datetime

    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.astimezone()  # naive = локальное время этой машины
    return dt


def _created_at(raw):
    """created_at стенда в aware-datetime: «2026-10-21 15:39:40» — локальное время сервера
    (совпадает с локальным временем машины, проверено на develop 21.10.2026),
    «2026-07-31T07:09:05.000000Z» — UTC (пользователи), «22.09.26» — только дата
    (материалы БЗ, берём полночь). None, если формат неизвестен."""
    from datetime import datetime

    if not raw:
        return None
    text = str(raw)
    try:
        if re.fullmatch(r"\d{2}\.\d{2}\.\d{2}", text):
            return datetime.strptime(text, "%d.%m.%y").astimezone()
        dt = datetime.fromisoformat(text.replace("Z", "+00:00").replace(" ", "T"))
        return dt if dt.tzinfo else dt.astimezone()
    except ValueError:
        return None


def _iter_pages(api_client, path: str, per_page: int = 100):
    """Все элементы пагинированного списка (meta.last_page), с & или ? по ситуации."""
    page = 1
    sep = "&" if "?" in path else "?"
    while True:
        resp = api_client.get(f"{path}{sep}per-page={per_page}&page={page}")
        if resp.status_code != 200:
            logger.warning(f"GET {path} page={page} -> {resp.status_code}: {resp.text[:200]}")
            return
        body = resp.json()
        data = body.get("data") or []
        if isinstance(data, dict):
            data = data.get("materials") or data.get("items") or []
        for item in data:
            yield item
        meta = body.get("meta") or {}
        if not data or page >= int(meta.get("last_page") or 1):
            return
        page += 1


def collect_autotest_leftovers(api_client, since) -> list:
    """Сущности автотестов, созданные на стенде не раньше since — в виде записей манифеста
    (entity/id/how_to_delete), в порядке «создания» (users → programs → БЗ → активности →
    тесты), чтобы _delete_entries удалял их в обратном: сначала контент, потом программы и
    пользователей. Сущности без разбираемого created_at пропускаются с предупреждением."""
    entries = []
    seen = set()

    def add(entity, id_, note, created_raw, label):
        created = _created_at(created_raw)
        if created is None:
            logger.warning(f"   {label}: created_at={created_raw!r} не разобран — пропущено")
            return
        if created < since or (entity, str(id_)) in seen:
            return
        seen.add((entity, str(id_)))
        entries.append({"entity": entity, "id": id_, "how_to_delete": note})
        logger.info(f"   + {entity} {id_} ({label}, {created_raw})")

    logger.info("1. Пользователи auto_test_* / cas_user_* ...")
    for prefix in AUTOTEST_EMAIL_PREFIXES:
        for item in _iter_pages(api_client, f"/users?filters[email]={prefix.rstrip('_')}"):
            attrs = item.get("attributes", item)
            email = str(attrs.get("email") or "")
            if email.startswith(prefix):
                add("user", item["id"], "users.delete(user_id)", attrs.get("created_at"), email)

    logger.info("2. Программы Автотест_* / API-test_* / E2E_* ...")
    for prefix in AUTOTEST_NAME_PREFIXES:
        for item in _iter_pages(api_client, f"/programs?filters[name]={prefix}"):
            attrs = item.get("attributes", item)
            name = str(attrs.get("name") or "")
            if name.startswith(prefix):
                add("program", item["id"], "programs.mass_delete([id])", attrs.get("created_at"), name)

    logger.info("3. База знаний: материалы и достижения Автотест* ...")
    for item in _iter_pages(api_client, "/knowledge-base/admin/materials?filters[name]=Автотест"):
        attrs = item.get("attributes", item)
        name = str(attrs.get("name") or "")
        if "Автотест" in name:
            add("knowledge_base_material", item["id"], "knowledge_base.delete_materials([id])", attrs.get("created_at"), name)
    for item in _iter_pages(api_client, "/admin/achievements?filters[name]=Автотест"):
        attrs = item.get("attributes", item)
        name = str(attrs.get("name") or "")
        if "Автотест" in name:
            add("achievement", item["id"], "knowledge_base.delete_achievement(id)", attrs.get("created_at"), name)

    logger.info("4. Активности Автотест* (курсы, ДЗ, внешний контент, LPD) ...")
    for item in _iter_pages(api_client, "/activities?filters[name]=Автотест"):
        attrs = item.get("attributes", item)
        name = str(attrs.get("name") or "")
        if "Автотест" not in name:
            continue
        entity = _ACTIVITY_ENTITY.get(str(attrs.get("content_type") or ""), "tincan")
        add(entity, item["id"], "tincan.mass_delete([id])" if entity in ("tincan", "scorm") else f"{entity}.mass_delete([id])",
            attrs.get("created_at"), f"{name} [{attrs.get('content_type')}]")

    logger.info("5. Тесты, опросы, АОС Автотест* ...")
    for item in _iter_pages(api_client, "/tests?filters[name]=Автотест"):
        attrs = item.get("attributes", item)
        name = str(attrs.get("name") or "")
        if "Автотест" not in name:
            continue
        entity = _TEST_ENTITY.get(str(attrs.get("type") or ""), "test")
        add(entity, item.get("id") or attrs.get("content_id"), f"{entity}s.mass_delete([id])" if entity != "aos" else "aos.mass_delete([id])",
            attrs.get("created_at"), f"{name} [{attrs.get('type')}]")

    return entries


def run_cleanup_autotests(args) -> int:
    """--cleanup-autotests --since <ISO>: найти на стенде данные автотестов, созданные
    не раньше since (старт прогона в test_hub), и удалить их. Итог — как у --cleanup,
    плюс manifest найденного (test_hub хранит его как партию «очистка после прогона»)."""
    env = ENVIRONMENTS[args.env]
    since = _parse_since(args.since)
    logger.info(f"Очистка данных автотестов на {env.name} ({env.api_base_url}), созданных с {since.isoformat()}")

    api_client, cas_client, _ = build_clients(env, dry_run=False)
    api_client.timeout = 120
    entries = collect_autotest_leftovers(api_client, since)
    manifest = Manifest(env.name, CLEANUP_AFTER_RUN_SCENARIO)
    manifest.created = entries
    logger.info(f"Найдено сущностей: {len(entries)}")

    manifest_path = None
    if args.manifest_out:
        manifest_path = manifest.save(args.manifest_out)

    if args.dry_run:
        for entry in reversed(entries):
            logger.info(f"[dry-run] был бы удалён {entry['entity']} id={entry['id']}")
        emit_result(args, {"ok": True, "dry_run": True, "since": since.isoformat(), "manifest": manifest.to_dict(),
                           "manifest_path": str(manifest_path) if manifest_path else None,
                           "deleted": 0, "failed": 0, "skipped": 0, "results": []})
        return 0

    handlers = _cleanup_handlers(api_client, cas_client, env)
    ok, failed, skipped, results = _delete_entries(entries, handlers, api_client, cas_client)
    emit_result(args, {
        "ok": failed == 0, "dry_run": False, "since": since.isoformat(), "manifest": manifest.to_dict(),
        "manifest_path": str(manifest_path) if manifest_path else None,
        "deleted": ok, "failed": failed, "skipped": skipped, "results": results,
    })
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Единый генератор тестовых данных")
    parser.add_argument("--env", default="develop", choices=sorted(ENVIRONMENTS))
    parser.add_argument("--scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--list", action="store_true", help="показать зарегистрированные сценарии и выйти")
    parser.add_argument("--dry-run", action="store_true", help="не делать сетевых вызовов, только план")
    parser.add_argument("--count", type=int, default=1, help="сколько сущностей на единицу плана (см. описание сценария)")
    parser.add_argument("--tenant", type=int, default=None, help="tenant_organization_id")
    parser.add_argument("--prefix", default=None, help="суффикс имён: 'Автотест_<prefix>_<ts>'")
    parser.add_argument("--cleanup", metavar="MANIFEST.json", help="удалить сущности из манифеста в обратном порядке")
    parser.add_argument("--cleanup-autotests", action="store_true",
                        help="удалить данные автотестов (Автотест_*/API-test_*/E2E_*, auto_test_*), созданные на стенде "
                             "не раньше --since (кнопка «Удалить данные прогона» в test_hub)")
    parser.add_argument("--since", metavar="ISO", default=None,
                        help="нижняя граница created_at для --cleanup-autotests (локальное время, как runs.started в test_hub)")
    parser.add_argument("--json", action="store_true",
                        help="машинный вывод: --list печатает JSON, --scenario/--cleanup добавляют строку "
                             f"'{RESULT_MARKER} {{json}}' с итогом (для test_hub)")
    parser.add_argument("--manifest-out", metavar="PATH", default=None,
                        help="куда сохранить манифест (по умолчанию test_data_generation/manifests/<env>_<scenario>_<ts>.json)")
    args = parser.parse_args()

    if args.list:
        list_scenarios(as_json=args.json)
        return 0

    if args.cleanup:
        return run_cleanup(args)

    if args.cleanup_autotests:
        if not args.since:
            parser.error("--cleanup-autotests требует --since <ISO>")
        return run_cleanup_autotests(args)

    if not args.scenario:
        parser.error("нужен --scenario NAME, --list, --cleanup MANIFEST.json или --cleanup-autotests --since ISO")

    return run_scenario(args)


if __name__ == "__main__":
    sys.exit(main())
