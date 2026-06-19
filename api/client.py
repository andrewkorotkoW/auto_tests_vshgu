import requests
from config.settings import settings
from utils.logger import logger


class ApiClient:
    """Базовый клиент для API-запросов."""

    def __init__(self, cookie: str = None, base_url: str = None, auth_token: str = None):
        self.session = requests.Session()
        if cookie:
            # Добавляем куку через заголовок
            self.session.headers["Cookie"] = f"develop={cookie}"
        if auth_token:
            self.session.headers["Authorization"] = auth_token
        self.session.headers.update({
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json"
        })
        self.base_url = base_url or settings.BASE_URL
        self.timeout = settings.REQUEST_TIMEOUT

    def post(self, endpoint: str, json: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"POST {url}")
        resp = self.session.post(url, json=json, timeout=self.timeout)
        logger.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        return resp

    def get(self, endpoint: str) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"GET {url}")
        resp = self.session.get(url, timeout=self.timeout)
        logger.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        return resp

    def delete(self, endpoint: str, json: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"DELETE {url}")
        resp = self.session.delete(url, json=json, timeout=self.timeout)
        logger.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        return resp

    def patch(self, endpoint: str, json: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"PATCH {url}")
        resp = self.session.patch(url, json=json, timeout=self.timeout)
        logger.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        return resp

    def put(self, endpoint: str, json: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"PUT {url}")
        resp = self.session.put(url, json=json, timeout=self.timeout)
        logger.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        return resp

    def upload(self, endpoint: str, files: dict, data: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"UPLOAD {url}")
        # Для upload не задаём Content-Type — requests сам сформирует с boundary
        headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
        resp = self.session.post(url, files=files, data=data, headers=headers, timeout=self.timeout)
        logger.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        return resp
