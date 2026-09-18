import allure
import pytest
import requests

from api.helpers.expectations import expect_status
from config.settings import settings


@allure.feature("Health")
@allure.story("Smoke: стенд доступен")
class TestHealth:

    @allure.title("Базовый URL окружения отвечает")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @pytest.mark.api
    def test_base_url_is_reachable(self, env):
        resp = requests.get(env.ui_base_url, timeout=settings.REQUEST_TIMEOUT)
        expect_status(resp, 200)

    @allure.title("/api/v1/auth/me с валидной сессией отвечает 200")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @pytest.mark.api
    def test_auth_me_returns_200(self, api_client):
        resp = api_client.get("/auth/me")
        expect_status(resp, 200)
