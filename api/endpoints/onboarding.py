from typing import Iterable, Optional

from api.client import ApiClient
from utils.logger import logger


class OnboardingEndpoint:
    """Методы для работы с онбордингом."""

    # Полный список историй онбординга (перенесён из DEFAULT_ONBOARDING_STORIES
    # коллеги, tests/api/helpers/user_prepare_api.py, репозиторий lms) — шире
    # прежнего дефолта "sidebar": главный онбординг, страница программы, личный
    # кабинет индивидуального обучения.
    DEFAULT_STORIES = [
        "sidebar",
        "main_education",
        "program_education_information",
        "program_education_schedule",
        "program_education_tabs",
        "program_education_activities",
        "individual_education_activities",
    ]

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

    def complete_all(self, stories: Optional[Iterable[str]] = None) -> None:
        """Завершить список историй онбординга (по умолчанию — DEFAULT_STORIES)."""
        for name in stories or self.DEFAULT_STORIES:
            self.complete(name)