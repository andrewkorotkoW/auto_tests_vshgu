import allure
import pytest
from utils.logger import logger


@allure.feature("Onboarding API")
@allure.story("Complete onboarding")
class TestOnboardingAPI:
    """Тесты на завершение онбординга."""

    @allure.title("Завершить онбординг через API (все страницы)")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_complete_all_onboarding(self, onboarding_endpoint):
        """Пройти онбординг для всех страниц."""

        pages = [
            "sidebar",
            "knowledge_base_library",
            "support",
            "individual_education_schedule",
            "individual_education_activities",
            "program_education_schedule"
        ]

        for page_name in pages:
            with allure.step(f"Завершить онбординг: {page_name}"):
                success = onboarding_endpoint.complete(name=page_name)
                assert success, f"Онбординг {page_name} не завершился"
                logger.info(f"✅ Онбординг {page_name} завершён")