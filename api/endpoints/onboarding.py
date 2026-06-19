from api.client import ApiClient
from utils.logger import logger


class OnboardingEndpoint:
    """Методы для работы с онбордингом."""

    def __init__(self, client: ApiClient):
        self.client = client

    def complete(self, name: str = "sidebar") -> bool:
        """Завершить онбординг."""
        resp = self.client.post("/onboarding", json={"name": name})
        success = resp.status_code in (200, 201, 204)
        if success:
            logger.info(f"Onboarding completed: {name}")
        else:
            logger.warning(f"Onboarding failed: {resp.status_code}")
        return success