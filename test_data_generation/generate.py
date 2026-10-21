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
    banner_and_partners,
    buk,
    cas,
    certificates,
    courses,
    demo,
    homework,
    learner_progress,
    lpd,
    materials,
    program_full,
    tests_polls,
    users,
)

# Порядок регистрации = порядок в --list и в селекте test_hub: сценарии идут подряд по
# категориям (см. CATEGORIES ниже), чтобы группы не чередовались.
SCENARIOS = {
    "users": users,
    "program_full": program_full,
    "learner_progress": learner_progress,
    "activities": activities,
    "tests_polls": tests_polls,
    "homework": homework,
    "courses": courses,
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
    "activities": ("Активности", "Все типы активностей в модуле"),
    "tests_polls": ("Активности", "Тесты и опросы"),
    "homework": ("Активности", "Практические задания (3 типа оценки)"),
    "courses": ("Активности", "Курсы Tincan + материал БЗ"),
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
        "cas_assignment": lambda id_: ext_ep.dismiss_assignments(id_[0], [id_[1]]) is not None,
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

    print(f"{'сущность':22} {'id':30} результат")
    ok, failed, skipped = 0, 0, 0
    results = []
    for entry in reversed(manifest.created):
        entity, id_, note = entry["entity"], entry["id"], entry["how_to_delete"]
        handler = handlers.get(entity)
        if handler is None:
            print(f"{entity:22} {str(id_):30} пропущено — нет DELETE-метода ({note})")
            skipped += 1
            results.append({"entity": entity, "id": id_, "status": "skipped", "note": note})
            continue
        try:
            success = bool(handler(id_))
        except Exception as exc:  # noqa: BLE001 — репортим и продолжаем удалять остальное
            success = False
            note = f"{note}; ошибка: {exc}"
        if success:
            ok += 1
            print(f"{entity:22} {str(id_):30} удалено")
            results.append({"entity": entity, "id": id_, "status": "deleted", "note": None})
        else:
            failed += 1
            print(f"{entity:22} {str(id_):30} НЕ удалено ({note})")
            results.append({"entity": entity, "id": id_, "status": "failed", "note": note})

    print(f"\nУдалено: {ok}, не удалено: {failed}, пропущено (нет DELETE): {skipped}")
    emit_result(args, {
        "ok": failed == 0, "dry_run": False, "deleted": ok, "failed": failed, "skipped": skipped,
        "results": results, "manifest_path": str(manifest_path),
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

    if not args.scenario:
        parser.error("нужен --scenario NAME, --list или --cleanup MANIFEST.json")

    return run_scenario(args)


if __name__ == "__main__":
    sys.exit(main())
