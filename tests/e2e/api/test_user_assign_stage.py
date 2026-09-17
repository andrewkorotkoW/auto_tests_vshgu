import allure
import pytest
import requests
import time
import random
from config.settings import settings


@allure.feature("Stage Tests")
@allure.story("User Assign Flow")
class TestUserAssignStage:

    @allure.title("Создание пользователя,создание ЛПД(Анононим), назначение на инд. трек, снятие, удаление")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.stage
    @pytest.mark.env("stage")
    def test_user_assign_flow(self):
        session = requests.Session()
        session.cookies.set("stage", settings.STAGE_DEVELOP_COOKIE)
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        })
        base_url = settings.STAGE_BASE_URL

        ts = int(time.time() * 1000)

        # 1. Создать пользователя (как в created_user)
        name = random.choice(["Иван", "Пётр", "Сергей", "Алексей", "Дмитрий"])
        surname = random.choice(["Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов"])
        patronymic = random.choice(["Иванович", "Петрович", "Сергеевич", "Алексеевич", "Дмитриевич"])
        email = f"auto_test_lpd{ts}@gmail.com"

        user_payload = {
            "data": {
                "attributes": {
                    "fields": {"personal_phone_number": 0, "phone_number": 0, "email": 0, "position": 0,
                               "position_level": 0, "organisation": 0, "car_brand": 0, "car_number": 0},
                    "roles": None, "tags": [],
                    "email": email, "surname": surname, "name": name, "login": email,
                    "patronymic": patronymic, "system_password": "SecurePass123", "password": "SecurePass123",
                    "date_of_birth": "1990-01-01", "region_id": 1, "municipality_id": 1
                }
            }
        }
        resp = session.post(f"{base_url}/users", json=user_payload)
        assert resp.status_code in (200, 201), f"User create failed: {resp.status_code} - {resp.text[:300]}"
        user_id = resp.json()["data"]["id"]
        allure.attach(str(user_id), "User ID", allure.attachment_type.TEXT)

        # 2. Создать ЛПД (имя как в генераторе)
        lpd_name = f"Автотест_ЛПД_{ts}"
        lpd_payload = {
            "data": {
                "attributes": {
                    "duration": "3", "content_type": "lpd", "lpd_id": "236",
                    "name": lpd_name, "name_client": f"{lpd_name}_внешка",
                    "activity_category_id": 2, "description": f"<p>{lpd_name}</p>",
                    "cover_uuid": "", "sub_files_uuids": "", "passing_type": "anonymous"
                },
                "includes": {"archive": [], "image": [], "spreadsheet": [], "video": [], "pdf": [], "document": [],
                             "offline": [], "webinar": [], "cover": [], "sub_files": []},
                "permissions": []
            }
        }
        resp_lpd = session.post(f"{base_url}/content", json=lpd_payload)
        assert resp_lpd.status_code in (200, 201), f"LPD create failed: {resp_lpd.status_code}"
        content_id = resp_lpd.json()["data"]["id"]

        # 3. Назначить на инд. трек
        assign_payload = {"data": {"attributes": {"content_ids": [content_id], "user_ids": [user_id]}}}
        resp_assign = session.post(f"{base_url}/users/content/distant/assign-activities", json=assign_payload)
        assert resp_assign.status_code in (200, 201), f"Assign failed: {resp_assign.status_code}"

        # 4. Снять назначение
        detach_payload = {"data": {"attributes": {"content_ids": [content_id], "user_ids": [user_id]}}}
        resp_detach = session.post(f"{base_url}/users/content/distant/detach-activities", json=detach_payload)
        assert resp_detach.status_code in (200, 201), f"Detach failed: {resp_detach.status_code}"
        allure.attach(f"User {user_id} -> LPD {content_id}", "Assignment", allure.attachment_type.TEXT)

        # 5. Удалить ЛПД
        session.delete(f"{base_url}/content/{content_id}")

        # 6. Удалить пользователя
        session.delete(f"{base_url}/users/{user_id}")

        allure.attach("All cleaned", "Status", allure.attachment_type.TEXT)