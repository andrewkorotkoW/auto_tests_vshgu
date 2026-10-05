"""Сценарий banner_and_partners: включение инфо-баннера (api/endpoints/info_banner.py) +
выдача доступа к Alpina/MIF N пользователям (api/endpoints/alpina.py, api/endpoints/mif.py).
"""
from api.endpoints.alpina import AlpinaEndpoint
from api.endpoints.info_banner import InfoBannerEndpoint
from api.endpoints.mif import MifEndpoint
from api.endpoints.users import UsersEndpoint
from api.helpers.data_generator import generate_user_payload
from utils.logger import logger

from lib import DEFAULT_PASSWORD

DESCRIPTION = "включение инфо-баннера + выдача доступа Alpina/MIF N пользователям"


def run(ctx) -> None:
    banner_ep = InfoBannerEndpoint(ctx.api_client)
    alpina_ep = AlpinaEndpoint(ctx.api_client)
    mif_ep = MifEndpoint(ctx.api_client)
    users_ep = UsersEndpoint(ctx.api_client)

    logger.info(f"1. {ctx.count} пользователей...")
    user_ids = []
    for i in range(ctx.count):
        user = users_ep.create(generate_user_payload(password=DEFAULT_PASSWORD))
        ctx.manifest.record("user", user["id"], "users.delete(user_id)")
        user_ids.append(user["id"])
        logger.info(f"   пользователь {i + 1}/{ctx.count}: ID={user['id']}, email={user['attributes']['email']}")

    logger.info("2. Включить инфо-баннер...")
    banner_ep.toggle(is_active=True)
    ctx.manifest.record("info_banner", "toggle", "info_banner.toggle(is_active=False)")

    logger.info(f"3. Доступ к Alpina для {len(user_ids)} пользователей...")
    alpina_ep.set_status(user_ids, status=True)
    ctx.manifest.record("alpina_access", user_ids, "alpina.set_status(user_ids, status=False)")

    logger.info(f"4. Доступ к MIF для {len(user_ids)} пользователей...")
    mif_ep.set_access(user_ids, access=True)
    ctx.manifest.record("mif_access", user_ids, "mif.set_access(user_ids, access=False)")

    logger.info("Готово.")
    logger.info(f"  Пользователи: {user_ids}")
