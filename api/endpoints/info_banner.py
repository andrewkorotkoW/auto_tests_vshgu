from api.client import ApiClient
from utils.logger import logger


class InfoBannerEndpoint:
    def __init__(self, client: ApiClient):
        self.client = client

    def toggle(self, is_active: bool = True) -> bool:
        payload = {"is_active": is_active}
        resp = self.client.patch("/admin/info-banner/toggle", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Info banner toggled: is_active={is_active}")
        else:
            logger.warning(f"Toggle failed: {resp.status_code}")
        return success