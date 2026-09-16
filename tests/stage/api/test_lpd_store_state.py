import allure
import pytest
import requests
import time
from config.settings import settings
from utils.logger import logger


@allure.feature("Stage LPD API")
@allure.story("Store State")
class TestLpdStoreState:

    @allure.title("Stage: Авторизованный ЛПД — store-state с stateId=5")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.stage
    @pytest.mark.api
    def test_store_state_authorized(self):
        session = requests.Session()
        session.cookies.set("stage", settings.STAGE_DEVELOP_COOKIE)
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://portal-stage.d7.devspark.ru"
        })
        base_url = settings.STAGE_BASE_URL or "https://portal-stage.d7.devspark.ru/api/v1"
        ts = int(time.time() * 1000)

        # 1. Программа
        with allure.step("1. Создать программу"):
            p = session.post(f"{base_url}/programs", json={
                "data": {"attributes": {"name": f"E2E_StoreState_{ts}", "tenant_organization_id": "",
                    "description": f"<p>E2E_StoreState_{ts}</p>", "is_active": True,
                    "color": "45ace1", "completed_color": "e3f3fb", "completed_text_color": "00385d"}}
            })
            assert p.status_code in (200, 201), f"Program failed: {p.status_code}"
            prog_id = p.json()["data"]["id"]
            logger.info(f"Программа создана: ID={prog_id}")

        # 2. Поток
        with allure.step("2. Создать поток"):
            s = session.post(f"{base_url}/programs/{prog_id}/streams", json={
                "data": {"attributes": {"name": f"Stream_{ts}", "location": "Москва",
                    "date_from": time.strftime("%Y-%m-%d"),
                    "date_to": time.strftime("%Y-%m-%d", time.localtime(ts/1000 + 30*86400)),
                    "is_active": True, "chats": [], "commentable": True, "duration": "123",
                    "passed_percent": 100, "project": 1, "is_registration_by_link_enabled": False,
                    "is_disciplines_required": False, "managers_ids": [], "external_managers": [],
                    "program_level": 4, "program_department": 8, "program_type": 10,
                    "learning_format": 13, "academic_directors": [1], "experts_entity_name": "13"}}
            })
            assert s.status_code in (200, 201), f"Stream failed: {s.status_code}"
            stream_id = s.json()["data"]["id"]
            logger.info(f"Поток создан: ID={stream_id}")

        # 3. Модуль
        with allure.step("3. Создать модуль"):
            m = session.post(f"{base_url}/programs/{prog_id}/streams/{stream_id}/modules", json={
                "data": {"attributes": {"name": f"Module_{ts}", "location": "Москва",
                    "date_from": time.strftime("%Y-%m-%d"),
                    "date_to": time.strftime("%Y-%m-%d", time.localtime(ts/1000 + 30*86400))}}
            })
            assert m.status_code in (200, 201), f"Module failed: {m.status_code}"
            module_id = m.json()["data"]["id"]
            logger.info(f"Модуль создан: ID={module_id}")

        # 4. Пользователь
        with allure.step("4. Создать пользователя"):
            email = f"e2e_store_{ts}@mail.com"
            u = session.post(f"{base_url}/users", json={
                "data": {"attributes": {
                    "fields": {"personal_phone_number": 0, "phone_number": 0, "email": 0, "position": 0, "position_level": 0, "organisation": 0, "car_brand": 0, "car_number": 0},
                    "roles": None, "tags": [], "email": email, "surname": "Иванов", "name": "Иван",
                    "login": email, "patronymic": "Автотестович", "system_password": "SecurePass123",
                    "password": "SecurePass123", "date_of_birth": "1990-01-01", "region_id": 1, "municipality_id": 1}}
            })
            assert u.status_code in (200, 201), f"User failed: {u.status_code}"
            user_id = u.json()["data"]["id"]
            logger.info(f"Пользователь создан: ID={user_id}, email={email}")

        # 5. Назначить пользователя на поток
        with allure.step("5. Назначить пользователя на поток"):
            session.post(f"{base_url}/programs/{prog_id}/streams/{stream_id}/assignments", json={
                "data": {"attributes": {"users_ids": [user_id]}}
            })
            logger.info(f"Пользователь {user_id} назначен на поток {stream_id}")

        # 6. Создать авторизованный ЛПД (235)
        with allure.step("6. Создать ЛПД 235"):
            lpd_name = f"LPD_Auth_{ts}"
            l = session.post(f"{base_url}/content", json={
                "data": {"attributes": {"duration": "3", "content_type": "lpd", "lpd_id": "235",
                    "name": lpd_name, "name_client": f"{lpd_name}_внешка", "activity_category_id": 2,
                    "description": f"<p>{lpd_name}</p>", "cover_uuid": "", "sub_files_uuids": "",
                    "passing_type": "authorized"},
                "includes": {"archive":[],"image":[],"spreadsheet":[],"video":[],"pdf":[],"document":[],"offline":[],"webinar":[],"cover":[],"sub_files":[]},
                "permissions": []}
            })
            assert l.status_code in (200, 201), f"LPD failed: {l.status_code}"
            lpd_id = l.json()["data"]["id"]
            logger.info(f"ЛПД создан: ID={lpd_id}")

        # 7. Назначить ЛПД в модуль и активировать пользователя
        with allure.step("7. Назначить ЛПД в модуль и активировать пользователя"):
            session.post(f"{base_url}/programs/{prog_id}/streams/{stream_id}/modules/{module_id}/mass-addition", json={
                "data": {"attributes": {"content_ids": [lpd_id], "stream_module_id": module_id}}
            })
            logger.info(f"ЛПД {lpd_id} добавлен в модуль {module_id}")

            time.sleep(3)

            session.headers["Referer"] = f"https://portal-stage.d7.devspark.ru/admin/programs/{prog_id}/streams/{stream_id}?i=1"
            resp = session.post(
                f"{base_url}/modules/{module_id}/contents/{lpd_id}/lpd/assignment?stream={stream_id}",
                json={"users": [user_id]}
            )
            assert resp.status_code in (200, 201), f"LPD assign failed: {resp.status_code}"
            invite_id = resp.json()["data"][0]["invite_id"]
            logger.info(f"Пользователь активирован, invite_id={invite_id}")

        # 8. Вызвать store-state с stateId=5
        with allure.step("8. Вызвать store-state"):
            # Явно задаём рабочий JWT, чтобы избежать проблем с .env
            jwt_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3BvcnRhbC1zdGFnZS5kNy5kZXZzcGFyay5ydSIsInN1YiI6ImxwZC1jbGllbnQiLCJpYXQiOjE3ODAzMDM3NDMuOTQyMTU3LCJhdWQiOiJ2c2hndS1hcGkifQ.n90exTuPJf3TdT8A35V7oUILurJyE1qjJu-pOBJxSak"
            invite_encoded = requests.utils.quote(invite_id, safe='')
            store_url = f"{base_url}/lpd/result/store-state?userId={user_id}&inviteId={invite_encoded}&stateId=5"
            store_resp = session.get(
                store_url,
                headers={"Authorization": jwt_token, "Accept": "application/json"}
            )
            assert store_resp.status_code == 200, f"store-state failed: {store_resp.status_code} {store_resp.text}"
            result = store_resp.json()
            assert "changes" in result
            assert result["changes"]["status"] == 5
            logger.info("store-state успешно отработал")
            allure.attach(str(result), "StoreState Response", allure.attachment_type.JSON)

        # 9. Очистка
        with allure.step("9. Очистить данные"):
            session.delete(f"{base_url}/content/{lpd_id}")
            session.delete(f"{base_url}/programs/{prog_id}/streams/{stream_id}/modules/{module_id}")
            session.delete(f"{base_url}/programs/{prog_id}/streams/{stream_id}")
            session.delete(f"{base_url}/programs/mass-delete", json={
                "data": {"attributes": {"programs_ids": [prog_id]}}
            })
            session.delete(f"{base_url}/users/{user_id}")
            logger.info("Очистка завершена")