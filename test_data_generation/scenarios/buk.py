"""Сценарий buk: N пользователей -> входящий REST БУК (POST /external/buk/users) с
ожиданием сопоставления по email с уже созданным пользователем (см. README раздел 8,
ExternalBukEndpoint.wait_for_match). БУК есть только на stage (conftest.external_buk_endpoint
делает pytest.skip без <ENV>_BUK_TOKEN) — на develop сценарий сам определяет отсутствие
токена и завершается с явной пометкой, а не падает на 401/403.
"""
import requests

from api.client import ApiClient
from api.endpoints.external_buk import ExternalBukEndpoint
from api.endpoints.users import UsersEndpoint
from api.helpers.data_generator import generate_buk_user_payload, generate_user_payload
from utils.logger import logger

from lib import DEFAULT_PASSWORD

DESCRIPTION = "N пользователей -> входящий REST БУК (POST /external/buk/users) с ожиданием сопоставления по email"

NO_BUK_MODULE_REASON = "нет модуля на этом окружении ({env}_BUK_TOKEN не задан в .env — БУК есть только на stage, см. README раздел 8)"


def run(ctx) -> None:
    if not ctx.env.buk_token:
        reason = NO_BUK_MODULE_REASON.format(env=ctx.env.name.upper())
        logger.info(reason)
        ctx.manifest.skip("buk", reason)
        return

    users_ep = UsersEndpoint(ctx.api_client)

    buk_ep = None
    if not ctx.dry_run:
        session = requests.Session()
        session.cookies.update(ctx.api_client.session.cookies)
        session.headers["Authorization"] = ctx.env.buk_token
        buk_client = ApiClient(session=session, base_url=ctx.env.api_base_url)
        buk_ep = ExternalBukEndpoint(buk_client)

    logger.info(f"{ctx.count} пользователей на сопоставление с БУК "
                f"(email должен совпасть с ранее созданным пользователем)...")
    for i in range(ctx.count):
        user = users_ep.create(generate_user_payload(password=DEFAULT_PASSWORD))
        ctx.manifest.record("user", user["id"], "users.delete(user_id)")
        email = user["attributes"]["email"]
        logger.info(f"   пользователь {i + 1}/{ctx.count}: ID={user['id']}, email={email}")

        buk_payload = generate_buk_user_payload(email=email, user_id=user["id"])
        ctx.manifest.record("buk_user", buk_payload["buk_user_id"], "external_buk.delete_user(buk_user_id)")

        def _post(payload=buk_payload):
            buk_ep.post_user(payload)
            matched = buk_ep.wait_for_match(payload)
            status = (matched.get("user") or {}).get("sync_status")
            logger.info(f"   BUK {payload['buk_user_id']}: sync_status={status}")

        ctx.dry_or(f"POST /external/buk/users ({buk_payload['buk_user_id']}) + wait_for_match", None, _post)

    logger.info("Готово.")
