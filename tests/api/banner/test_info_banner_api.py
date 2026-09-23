import allure
import pytest
from utils.logger import logger


@allure.feature("Info Banner API")
@allure.story("Toggle banner")
class TestInfoBannerAPI:

    @pytest.fixture(autouse=True)
    def _banner_off_after(self, info_banner_endpoint):
        """Тесты включают баннер на общем стенде — после каждого гасим его независимо от исхода."""
        yield
        info_banner_endpoint.toggle(False)

    @allure.title("Включить инфо-баннер")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    def test_toggle_banner_on(self, info_banner_endpoint):
        success = info_banner_endpoint.toggle(True)
        assert success, "Не удалось включить баннер"
        logger.info("Баннер включён")

    @allure.title("Выключить инфо-баннер")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    def test_toggle_banner_off(self, info_banner_endpoint):
        success = info_banner_endpoint.toggle(False)
        assert success, "Не удалось выключить баннер"
        logger.info("Баннер выключен")