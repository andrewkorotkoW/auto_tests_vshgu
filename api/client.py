import requests
from config.settings import settings
from utils.logger import logger


class ApiClient:
    """Базовый клиент для API-запросов.

    Паттерн возврата: методы api/endpoints/* сохраняют исторически сложившийся для
    каждого метода тип возврата (Dict/list/bool с распарсенными данными), а проверку
    статуса ответа выполняют через api.helpers.expectations.expect_status вместо
    голого assert внутри метода — она бросает AssertionError с resp.text при несовпадении.
    """

    def __init__(self, cookie: str = None, base_url: str = None, auth_token: str = None,
                 session: requests.Session = None, cookie_name: str = "develop"):
        self.session = session or requests.Session()
        if cookie:
            # Добавляем куку через заголовок
            self.session.headers["Cookie"] = f"{cookie_name}={cookie}"
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

    def get(self, endpoint: str, headers: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"GET {url}")
        resp = self.session.get(url, headers=headers, timeout=self.timeout)
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
        # Content-Type: None снимает session-заголовок application/json (выставлен в __init__) —
        # иначе requests не подставит multipart/form-data с boundary и файл не уйдёт
        # (тот же приём, что в api/endpoints/tincan.py, но через requests, а не curl).
        headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": None,
        }
        resp = self.session.post(url, files=files, data=data, headers=headers, timeout=self.timeout)
        logger.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        return resp
