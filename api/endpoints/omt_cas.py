from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class OmtCasEndpoint:
    """Методы для работы с OMT CAS."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create_tenant_org_location(self, payload: dict) -> Dict:
        resp = self.client.post("/cas/tenant-org-locations", json=payload)
        if resp.status_code == 422 and "уже существует" in resp.text:
            logger.info("CAS связь уже существует")
            return resp.json()
        assert resp.status_code in (200, 201), (
            f"CAS create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json().get("data", resp.json())
        logger.info(f"CAS tenant-org-location created: {data}")
        return data

    def delete_tenant_org_location(self, location_id: int) -> bool:
        """Удаление tenant-org-location."""
        resp = self.client.delete(f"/cas/tenant-org-locations/{location_id}")
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"CAS tenant-org-location deleted: ID={location_id}")
        else:
            logger.warning(f"CAS delete failed: {resp.status_code}")
        return success


