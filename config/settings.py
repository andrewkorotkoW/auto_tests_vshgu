import os
from dotenv import load_dotenv

from config.environments import ENVIRONMENTS, active_env

load_dotenv()

_develop = ENVIRONMENTS["develop"]
_stage = ENVIRONMENTS["stage"]


class Settings:
    # Алиасы на develop/stage из слоя окружений (config/environments.py) —
    # оставлены, чтобы не ломать код, который уже импортирует settings.BASE_URL и т.п.
    # BASE_URL/UI_BASE_URL/GLOBAL_BASE_URL — адреса АКТИВНОГО окружения (--env), а не develop:
    # иначе LoginPage.login() без base_url и page.goto(f"{settings.UI_BASE_URL}…") в UI-тестах
    # уходили на develop даже при --env k8s (06.10.2026: 8 ложных падений на k8s v2).
    @property
    def BASE_URL(self):
        return active_env().api_base_url

    @property
    def UI_BASE_URL(self):
        return active_env().ui_base_url

    @property
    def GLOBAL_BASE_URL(self):
        return active_env().global_base_url

    DEVELOP_COOKIE = _develop.cookie
    CAS_AUTH_TOKEN = _develop.cas_auth_token
    EXTERNAL_SYSTEM_CLIENT_TOKEN = _develop.external_system_client_token
    LPD_JWT_TOKEN = _develop.lpd_jwt_token or "токен_по_умолчанию"

    STAGE_BASE_URL = _stage.api_base_url
    STAGE_DEVELOP_COOKIE = _stage.cookie
    STAGE_COOKIE_NAME = _stage.cookie_name
    STAGE_UI_BASE_URL = _stage.ui_base_url
    STAGE_LPD_JWT_TOKEN = _stage.lpd_jwt_token

    DEFAULT_LOGIN = os.getenv("DEFAULT_LOGIN", "admin@example.com")
    DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "SecurePass123")
    DEFAULT_REGION_ID = int(os.getenv("DEFAULT_REGION_ID", "33"))
    DEFAULT_MUNICIPALITY_ID = int(os.getenv("DEFAULT_MUNICIPALITY_ID", "2310"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    UI_TIMEOUT = int(os.getenv("UI_TIMEOUT", "10000"))

    TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
    TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")


settings = Settings()
