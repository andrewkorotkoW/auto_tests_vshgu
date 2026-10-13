from typing import Iterable, Optional

from api.client import ApiClient
from utils.logger import logger


class OnboardingEndpoint:
    """Методы для работы с онбордингом."""

    # Полный список историй онбординга — enum в бандле портала (develop, 13.10.2026:
    # /assets/index-*.js, `e.SIDEBAR="sidebar", … e.HOMEWORK_TABS="homework_tabs"`).
    # Изначально перенесён из DEFAULT_ONBOARDING_STORIES коллеги (репозиторий lms);
    # 13.10 добавлены четыре истории, которых там не было: ЛПД в индивидуальном обучении и
    # программе, вкладки ДЗ, «program» — без них у подготовленного через API пользователя
    # тур всё равно всплывал на этих экранах. Админка (/admin, отдельный бандл) онбординга
    # не имеет вовсе. GET /onboarding отдаёт список уже закрытых историй.
    DEFAULT_STORIES = [
        "sidebar",
        "knowledge_base_library",
        "support",
        "main_education",
        "program",
        "program_education_information",
        "program_education_schedule",
        "program_education_tabs",
        "program_education_activities",
        "program_education_lpd",
        "individual_education_tabs",
        "individual_education_schedule",
        "individual_education_activities",
        "individual_education_lpd",
        "homework_tabs",
        "knowledge_base_tabs",
        "knowledge_base_favorite",
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
