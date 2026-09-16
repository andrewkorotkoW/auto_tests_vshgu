import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BASE_URL = os.getenv("BASE_URL", "https://portal-develop.d2.devspark.ru/api/v1")
    UI_BASE_URL = os.getenv("UI_BASE_URL", "https://portal-develop.d2.devspark.ru")
    DEFAULT_LOGIN = os.getenv("DEFAULT_LOGIN", "admin@example.com")
    DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "SecurePass123")
    DEFAULT_REGION_ID = int(os.getenv("DEFAULT_REGION_ID", "33"))
    DEFAULT_MUNICIPALITY_ID = int(os.getenv("DEFAULT_MUNICIPALITY_ID", "2310"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    UI_TIMEOUT = int(os.getenv("UI_TIMEOUT", "10000"))
    DEVELOP_COOKIE = os.getenv("DEVELOP_COOKIE", "")
    GLOBAL_BASE_URL = os.getenv("GLOBAL_BASE_URL", "https://global-develop.d2.devspark.ru/api/v1")
    CAS_AUTH_TOKEN = os.getenv("CAS_AUTH_TOKEN", "")
    EXTERNAL_SYSTEM_CLIENT_TOKEN = os.getenv("EXTERNAL_SYSTEM_CLIENT_TOKEN", "")
    STAGE_BASE_URL = os.getenv("STAGE_BASE_URL", "https://portal-stage.d7.devspark.ru/api/v1")
    STAGE_DEVELOP_COOKIE = os.getenv("STAGE_DEVELOP_COOKIE", "")
    STAGE_UI_BASE_URL = os.getenv("STAGE_UI_BASE_URL", "https://portal-stage.d7.devspark.ru")
    LPD_JWT_TOKEN = os.getenv("LPD_JWT_TOKEN", "токен_по_умолчанию")
    TEST_USER_EMAIL = os.getenv("admin3@org2.ru")
    TEST_USER_PASSWORD = os.getenv("SecurePass123")


settings = Settings()