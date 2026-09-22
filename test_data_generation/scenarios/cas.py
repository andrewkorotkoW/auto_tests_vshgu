"""Сценарий CAS: связка организация+локация -> программа CAS -> поток -> синхронизация
-> модуль в потоке -> N пользователей CAS на каждый статус зачисления (enlisted/dismissed/
waiting) с паролем -> зачисление в поток.

Перенос test_data_generation/generate_cas_data.py на lib.py-хелперы (клиенты/Manifest/
dry-run) и на готовые методы api/endpoints/external_cas.py, api/endpoints/omt_cas.py,
api/endpoints/modules.py — без сырых requests там, где для них уже есть метод.
"""
import os

from api.endpoints.external_cas import ExternalCasEndpoint
from api.endpoints.modules import ModulesEndpoint
from api.endpoints.omt_cas import OmtCasEndpoint
from api.helpers.constants import CAS_LOCATIONS, CAS_ORGANIZATIONS
from api.helpers.data_generator import (
    generate_external_cas_program_payload,
    generate_external_cas_stream_payload,
    generate_external_cas_user_payload,
    generate_module_payload,
)
from utils.logger import logger

from lib import DEFAULT_PASSWORD, request_tolerant

DESCRIPTION = "программа CAS -> поток -> синхронизация -> модуль -> N пользователей на каждый статус зачисления"

STATUSES = {
    "enlisted": "Зачислен",
    "dismissed": "Отчислен",
    "waiting": "Ожидание приказа",
}


def run(ctx) -> None:
    omt_ep = OmtCasEndpoint(ctx.api_client)
    ext_ep = ExternalCasEndpoint(ctx.cas_client)
    modules_ep = ModulesEndpoint(ctx.api_client)

    org_uuid, org_name = CAS_ORGANIZATIONS[1]
    loc_uuid, loc_name = CAS_LOCATIONS[4]
    tenant = ctx.tenant or 2

    logger.info(f"1. Связка организация «{org_name}» + локация «{loc_name}» с тенантом {tenant} (OMT)...")
    tol = omt_ep.create_tenant_org_location({
        "cas_location_uuid": loc_uuid,
        "cas_organization_uuid": org_uuid,
        "tenant_organization_id": tenant,
    })
    tol_id = (tol.get("data") or tol).get("id") if isinstance(tol, dict) else None
    if tol_id is not None:
        ctx.manifest.record("cas_tenant_org_location", tol_id, "omt_cas.delete_tenant_org_location(id)")

    logger.info("2. Программа CAS...")
    program = ext_ep.create_program(generate_external_cas_program_payload(
        name=ctx.name("CAS_Prog"), organization_uuid=org_uuid, location_uuid=loc_uuid,
    ))
    program_id = program.get("program_id", program.get("id"))
    ctx.manifest.record("cas_program", program_id, "external_cas.delete_program(program_id)")

    logger.info("3. Поток CAS...")
    stream = ext_ep.create_stream(program_id, generate_external_cas_stream_payload())
    stream_id = stream.get("stream_id", stream.get("id"))
    ctx.manifest.record("cas_stream", [program_id, stream_id],
                         "external_cas.delete_stream(program_id, stream_id)")

    logger.info("4. Синхронизация программы и потока (при создании через external API синхронизация "
                "уже произошла — 400 «должен(-на) быть не синхронизирован(-а)» здесь ожидаем и не считаем "
                "ошибкой)... Вызываем напрямую через request_tolerant, а не ext_ep.sync_program/sync_stream: "
                "их проверка «уже синхронизирован» сравнивает с resp.text, где кириллица экранирована "
                "(\\uXXXX), поэтому не срабатывает и метод просто падает на этом самом 400."
                )
    for label, path in (
        ("программа", f"/external/cas/sync/programs/{program_id}"),
        ("поток", f"/external/cas/sync/programs/{program_id}/streams/{stream_id}"),
    ):
        resp = request_tolerant(ctx.cas_client, "post", path,
                                 conflict_substr="синхронизирован", conflict_statuses=(400,))
        logger.info(f"   {label}: {'синхронизирована' if resp.status_code != 400 else 'уже синхронизирована'}")

    logger.info("5. Модуль в потоке CAS (админ-API)...")
    module = modules_ep.create(program_id, stream_id, generate_module_payload(
        name=ctx.name("CAS_Module"),
    ))
    ctx.manifest.record("cas_module", [program_id, stream_id, module["id"]],
                         "modules.delete(program_id, stream_id, module_id)")

    created_users = []
    plan = [(status, i) for status in STATUSES for i in range(ctx.count)]
    for n, (status, i) in enumerate(plan, start=1):
        suffix = f"{ctx._ts}_{status}_{i}"
        email = f"cas_user_{ctx.env.name}_{suffix}@mail.com"
        logger.info(f"6. Пользователь CAS {n}/{len(plan)} [{STATUSES[status]}]: {email}")
        user = ext_ep.create_user(generate_external_cas_user_payload(
            email=email, organization_uuid=org_uuid, location_uuid=loc_uuid,
            cas_uuid=f"cas-{suffix}-{os.urandom(2).hex()}",
        ))
        user_id = user.get("user_id", user.get("id"))
        ctx.manifest.record("cas_user", user_id,
                             "users.delete(user_id) (полное удаление) / external_cas.delete_user(user_id) (только синк)")

        # Отдельного метода "обновить пароль" нет ни в UsersEndpoint, ни в ExternalCasEndpoint —
        # как и в исходном generate_cas_data.py, читаем текущие атрибуты и PUT'им их обратно с паролем.
        resp = ctx.api_client.get(f"/users/{user_id}")
        attrs = resp.json()["data"]["attributes"]
        attrs["tags"] = [t["id"] if isinstance(t, dict) else t for t in attrs.get("tags") or []]
        attrs["password"] = DEFAULT_PASSWORD
        attrs["system_password"] = DEFAULT_PASSWORD
        pwd_resp = ctx.api_client.put(f"/users/{user_id}", json={"data": {"attributes": attrs}})
        logger.info(f"   пароль: {'ok' if pwd_resp.ok else str(pwd_resp.status_code) + ' ' + pwd_resp.text[:200]}")

        if status == "waiting":
            # "Ожидание приказа" = зачисление без enlisted_text/enlisted_link. Метод
            # ExternalCasEndpoint.assign_users всегда проставляет их для status="enlisted",
            # поэтому для этого варианта нужен прямой запрос (готового метода под него нет).
            request_tolerant(ctx.cas_client, "post", "/external/cas/assignments", json={
                "user_ids": [{"user_id": user_id, "cas_application_uid": f"auto-{suffix}-{user_id}"}],
                "stream_id": stream_id,
                "status": "enlisted",
            })
        elif status == "dismissed":
            ext_ep.assign_users(stream_id, [{"user_id": user_id}], status="dismissed",
                                 dismissed_text="Отчислен по автотесту", dismissed_link="https://autotest.com")
        else:
            ext_ep.assign_users(stream_id, [{"user_id": user_id}], status="enlisted")
        ctx.manifest.record("cas_assignment", [stream_id, user_id],
                             "external_cas.dismiss_assignments(stream_id, [user_id])")
        created_users.append((user_id, email, STATUSES[status]))

    logger.info("Готово.")
    logger.info(f"  Программа: {program_id}, поток: {stream_id}, модуль: {module['id']}")
    for user_id, email, label in created_users:
        logger.info(f"  {label:16} {email} / {DEFAULT_PASSWORD} (id={user_id})")
