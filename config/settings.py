import os
from dotenv import load_dotenv

from config.environments import ENVIRONMENTS

load_dotenv()

_develop = ENVIRONMENTS["develop"]
_stage = ENVIRONMENTS["stage"]


class Settings:
    # Алиасы на develop/stage из слоя окружений (config/environments.py) —
    # оставлены, чтобы не ломать код, который уже импортирует settings.BASE_URL и т.п.
    BASE_URL = _develop.api_base_url
    UI_BASE_URL = _develop.ui_base_url
    DEVELOP_COOKIE = _develop.cookie
    GLOBAL_BASE_URL = _develop.global_base_url
    CAS_AUTH_TOKEN = _develop.cas_auth_token
    EXTERNAL_SYSTEM_CLIENT_TOKEN = _develop.external_system_client_token
    LPD_JWT_TOKEN = _develop.lpd_jwt_token or "токен_по_умолчанию"

    STAGE_BASE_URL = _stage.api_base_url
    STAGE_DEVELOP_COOKIE = _stage.cookie
    STAGE_UI_BASE_URL = _stage.ui_base_url

    DEFAULT_LOGIN = os.getenv("DEFAULT_LOGIN", "admin@example.com")
    DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "SecurePass123")
    DEFAULT_REGION_ID = int(os.getenv("DEFAULT_REGION_ID", "33"))
    DEFAULT_MUNICIPALITY_ID = int(os.getenv("DEFAULT_MUNICIPALITY_ID", "2310"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    UI_TIMEOUT = int(os.getenv("UI_TIMEOUT", "10000"))

    TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
    TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")


settings = Settings()
