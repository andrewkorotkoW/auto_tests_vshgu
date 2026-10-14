import allure
import pytest
import requests
import time
from config.settings import settings
from api.helpers.expectations import expect_status


@allure.feature("Stage Tests")
@allure.story("LPD Stage")
class TestLpdStage:

    @allure.title("Создание ЛПД на стейдже (anonymous)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.stage
    @pytest.mark.env("stage")
    def test_create_lpd_anonymous(self):
        session = requests.Session()
        session.cookies.set(settings.STAGE_COOKIE_NAME, settings.STAGE_DEVELOP_COOKIE)
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        })
        base_url = settings.STAGE_BASE_URL

        name = f"Автотесты_ЛПД_Авторизиваны{int(time.time())}"
        payload = {
            "data": {
                "attributes": {
                    "duration": "3",
                    "content_type": "lpd",
                    "lpd_id": "235",
                    "name": name,
                    "name_client": name,
                    "activity_category_id": 2,
                    "description": f"<p>{name}</p>",
                    "cover_uuid": "",
                    "sub_files_uuids": "",
                    "passing_type": "authorized"
                },
                "includes": {"archive": [], "image": [], "spreadsheet": [], "video": [], "pdf": [], "document": [],
                             "offline": [], "webinar": [], "cover": [], "sub_files": []},
                "permissions": []
            }
        }

         # Создать
        resp = session.post(f"{base_url}/content", json=payload)
        expect_status(resp, (200, 201))
        content_id = resp.json()["data"]["id"]
        allure.attach(str(content_id), "Content ID", allure.attachment_type.TEXT)

        # Удалить
        resp_del = session.delete(f"{base_url}/content/{content_id}")
        expect_status(resp_del, (200, 204))
        allure.attach("Deleted", "Status", allure.attachment_type.TEXT)