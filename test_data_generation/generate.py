"""Единый CLI генератора тестовых данных.

    .venv/bin/python test_data_generation/generate.py --list
    .venv/bin/python test_data_generation/generate.py --scenario cas --env develop --dry-run
    .venv/bin/python test_data_generation/generate.py --scenario users --env develop --count 2
    .venv/bin/python test_data_generation/generate.py --cleanup test_data_generation/manifests/develop_cas_....json

Владелец задачи: --env stage должен корректно собираться и работать, но сам агент
не запускает ничего с --env stage — это прогоняется только вручную владельцем.
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # repo root: api/, config/
sys.path.insert(0, os.path.dirname(__file__))  # test_data_generation/: lib, scenarios

from config.environments import ENVIRONMENTS  # noqa: E402
from utils.logger import logger  # noqa: E402

from lib import Ctx, Manifest, build_clients  # noqa: E402
from scenarios import cas, program_full, users  # noqa: E402

SCENARIOS = {
    "cas": cas,
    "users": users,
    "program_full": program_full,
}

MANIFESTS_DIR = Path(__file__).resolve().parent / "manifests"


def list_scenarios() -> None:
    print("Зарегистрированные сценарии:")
    for name, module in SCENARIOS.items():
        print(f"  {name:14} {module.DESCRIPTION}")


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
    except Exception:
        logger.error(f"Сценарий {args.scenario} упал, создано до сбоя: {len(manifest.created)}")
        if manifest.created and not args.dry_run:
            path = MANIFESTS_DIR / f"{env.name}_{args.scenario}_{int(time.time())}_partial.json"
            manifest.save(path)
            logger.error(f"Манифест частично созданных сущностей сохранён: {path}")
        raise

    print("\nИтог:")
    print(f"{'сущность':22} {'id':30} примечание")
    for entry in manifest.created:
        print(f"{entry['entity']:22} {str(entry['id']):30} {entry['how_to_delete']}")

    if args.dry_run:
        print("\ndry-run: манифест не сохраняется — сетевых вызовов не было, удалять нечего.")
        return 0

    path = MANIFESTS_DIR / f"{env.name}_{args.scenario}_{int(time.time())}.json"
    manifest.save(path)
    print(f"\nМанифест сохранён: {path}")
    return 0


def _cleanup_handlers(api_client, cas_client):
    """entity -> функция(id) -> bool|None. None означает «нет DELETE-метода»."""
    from api.endpoints.certificates import CertificatesEndpoint
    from api.endpoints.external_cas import ExternalCasEndpoint
    from api.endpoints.modules import ModulesEndpoint
    from api.endpoints.omt_cas import OmtCasEndpoint
    from api.endpoints.programs import ProgramsEndpoint
    from api.endpoints.schedule_items import ScheduleItemsEndpoint
    from api.endpoints.streams import StreamsEndpoint
    from api.endpoints.users import UsersEndpoint

    users_ep = UsersEndpoint(api_client)
    programs_ep = ProgramsEndpoint(api_client)
    streams_ep = StreamsEndpoint(api_client)
    modules_ep = ModulesEndpoint(api_client)
    schedule_ep = ScheduleItemsEndpoint(api_client)
    certificates_ep = CertificatesEndpoint(api_client)
    omt_ep = OmtCasEndpoint(api_client)
    ext_ep = ExternalCasEndpoint(cas_client)

    return {
        "cas_tenant_org_location": lambda id_: omt_ep.delete_tenant_org_location(id_),
        "cas_program": lambda id_: ext_ep.delete_program(id_),
        "cas_stream": lambda id_: ext_ep.delete_stream(*id_),
        "cas_module": lambda id_: modules_ep.delete(*id_),
        "cas_user": lambda id_: users_ep.delete(id_),
        "cas_assignment": lambda id_: ext_ep.dismiss_assignments(id_[0], [id_[1]]) is not None,
        "user": lambda id_: users_ep.delete(id_),
        "program": lambda id_: programs_ep.delete(id_),
        "stream": lambda id_: streams_ep.delete(*id_),
        "module": lambda id_: modules_ep.delete(*id_),
        "schedule_item": lambda id_: schedule_ep.delete(*id_),
        "certificate_template": lambda id_: certificates_ep.delete_templates([id_]),
        "stream_assignment": None,
        "certificate_assignment": None,
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
        return 0

    api_client, cas_client, _ = build_clients(env, dry_run=False)
    handlers = _cleanup_handlers(api_client, cas_client)

    print(f"{'сущность':22} {'id':30} результат")
    ok, failed, skipped = 0, 0, 0
    for entry in reversed(manifest.created):
        entity, id_, note = entry["entity"], entry["id"], entry["how_to_delete"]
        handler = handlers.get(entity)
        if handler is None:
            print(f"{entity:22} {str(id_):30} пропущено — нет DELETE-метода ({note})")
            skipped += 1
            continue
        try:
            success = bool(handler(id_))
        except Exception as exc:  # noqa: BLE001 — репортим и продолжаем удалять остальное
            success = False
            note = f"{note}; ошибка: {exc}"
        if success:
            ok += 1
            print(f"{entity:22} {str(id_):30} удалено")
        else:
            failed += 1
            print(f"{entity:22} {str(id_):30} НЕ удалено ({note})")

    print(f"\nУдалено: {ok}, не удалено: {failed}, пропущено (нет DELETE): {skipped}")
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
    args = parser.parse_args()

    if args.list:
        list_scenarios()
        return 0

    if args.cleanup:
        return run_cleanup(args)

    if not args.scenario:
        parser.error("нужен --scenario NAME, --list или --cleanup MANIFEST.json")

    return run_scenario(args)


if __name__ == "__main__":
    sys.exit(main())
