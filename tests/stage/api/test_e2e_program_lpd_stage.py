import allure
import pytest
import requests
import time
import random
from utils.logger import logger
from config.settings import settings


@allure.feature("Stage Tests")
@allure.story("E2E LPD Stage")
class TestE2ELpdStage:

    @allure.title("E2E Stage: Программа → Поток → Модуль → Пользователь → 2 ЛПД → Назначение → Снятие")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.stage
    def test_e2e_lpd_stage(self):
        session = requests.Session()
        session.cookies.set("stage", settings.STAGE_DEVELOP_COOKIE)
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": settings.STAGE_UI_BASE_URL
        })
        base_url = settings.STAGE_BASE_URL
        ts = int(time.time() * 1000)

        # 1. Программа
        p = session.post(f"{base_url}/programs", json={
            "data": {"attributes": {"name": f"E2E_2LPD_{ts}", "tenant_organization_id": "",
                "description": f"<p>E2E_2LPD_{ts}</p>", "is_active": True,
                "color": "45ace1", "completed_color": "e3f3fb", "completed_text_color": "00385d"}}
        })
        assert p.status_code in (200, 201), f"Program failed: {p.status_code}"
        prog_id = p.json()["data"]["id"]
        logger.info(f"1. Программа создана: ID={prog_id}")

        # 2. Поток
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
        logger.info(f"2. Поток создан: ID={stream_id}")

        # 3. Модуль
        m = session.post(f"{base_url}/programs/{prog_id}/streams/{stream_id}/modules", json={
            "data": {"attributes": {"name": f"Module_{ts}", "location": "Москва",
                "date_from": time.strftime("%Y-%m-%d"),
                "date_to": time.strftime("%Y-%m-%d", time.localtime(ts/1000 + 30*86400))}}
        })
        assert m.status_code in (200, 201), f"Module failed: {m.status_code}"
        module_id = m.json()["data"]["id"]
        logger.info(f"3. Модуль создан: ID={module_id}")

        # 4. Пользователь
        name = random.choice(["Иван", "Пётр", "Сергей"])
        surname = random.choice(["Иванов", "Петров", "Сидоров"])
        email = f"e2e_2lpd_{ts}@mail.com"
        u = session.post(f"{base_url}/users", json={
            "data": {"attributes": {
                "fields": {"personal_phone_number": 0, "phone_number": 0, "email": 0, "position": 0, "position_level": 0, "organisation": 0, "car_brand": 0, "car_number": 0},
                "roles": None, "tags": [], "email": email, "surname": surname, "name": name,
                "login": email, "patronymic": "Автотестович", "system_password": "SecurePass123",
                "password": "SecurePass123", "date_of_birth": "1990-01-01", "region_id": 1, "municipality_id": 1}}
        })
        assert u.status_code in (200, 201), f"User failed: {u.status_code}"
        user_id = u.json()["data"]["id"]
        logger.info(f"4. Пользователь создан: ID={user_id}, email={email}")

        # 5. Назначить пользователя на поток
        session.post(f"{base_url}/programs/{prog_id}/streams/{stream_id}/assignments", json={
            "data": {"attributes": {"users_ids": [user_id]}}
        })
        logger.info(f"5. Пользователь {user_id} назначен на поток {stream_id}")

        # 6. Создать и назначить оба ЛПД
        lpd_ids = []
        for lpd_id_val, passing_type, prefix in [("236", "anonymous", "ANON"), ("235", "authorized", "AUTH")]:
            lpd_name = f"E2E_{prefix}_{ts}"
            l = session.post(f"{base_url}/content", json={
                "data": {"attributes": {"duration": "3", "content_type": "lpd", "lpd_id": lpd_id_val,
                    "name": lpd_name, "name_client": f"{lpd_name}_внешка", "activity_category_id": 2,
                    "description": f"<p>{lpd_name}</p>", "cover_uuid": "", "sub_files_uuids": "",
                    "passing_type": passing_type},
                "includes": {"archive":[],"image":[],"spreadsheet":[],"video":[],"pdf":[],"document":[],"offline":[],"webinar":[],"cover":[],"sub_files":[]},
                "permissions": []}
            })
            assert l.status_code in (200, 201), f"LPD {prefix} failed: {l.status_code}"
            lpd_id = l.json()["data"]["id"]
            lpd_ids.append(lpd_id)
            logger.info(f"6a. LPD {prefix} создан: ID={lpd_id}")

            # Назначить в модуль
            session.post(f"{base_url}/programs/{prog_id}/streams/{stream_id}/modules/{module_id}/mass-addition", json={
                "data": {"attributes": {"content_ids": [lpd_id], "stream_module_id": module_id}}
            })
            logger.info(f"6b. LPD {prefix} добавлен в модуль {module_id}")

            time.sleep(3)

            # Назначить пользователя на ЛПД
            session.cookies.set("stage", settings.STAGE_DEVELOP_COOKIE)
            session.headers["Referer"] = f"{settings.STAGE_UI_BASE_URL}/admin/programs/{prog_id}/streams/{stream_id}?i=1"
            resp = session.post(
                f"{base_url}/modules/{module_id}/contents/{lpd_id}/lpd/assignment?stream={stream_id}",
                json={"users": [user_id]}
            )
            assert resp.status_code in (200, 201), f"LPD {prefix} assign failed: {resp.status_code}"
            logger.info(f"6c. Пользователь {user_id} назначен на LPD {prefix}")

            time.sleep(3)

        # 7. Снять назначения
        for lpd_id in lpd_ids:
            session.cookies.set("stage", settings.STAGE_DEVELOP_COOKIE)
            session.headers["Referer"] = f"{settings.STAGE_UI_BASE_URL}/admin/programs/{prog_id}/streams/{stream_id}?i=1"
            resp_detach = session.delete(
                f"{base_url}/modules/{module_id}/contents/{lpd_id}/lpd/assignment?stream={stream_id}",
                json={"users": [user_id]}
            )
            assert resp_detach.status_code in (200, 204), f"LPD detach failed: {resp_detach.status_code}"
            logger.info(f"7. Назначение снято: LPD={lpd_id}")

        # 8. Очистка
        for lpd_id in lpd_ids:
            session.delete(f"{base_url}/content/{lpd_id}")
        session.delete(f"{base_url}/programs/{prog_id}/streams/{stream_id}/modules/{module_id}")
        session.delete(f"{base_url}/programs/{prog_id}/streams/{stream_id}")
        session.delete(f"{base_url}/programs/mass-delete", json={
            "data": {"attributes": {"programs_ids": [prog_id]}}
        })
        session.delete(f"{base_url}/users/{user_id}")
        logger.info("8. Очистка данных завершена")

        allure.attach(f"Program={prog_id}, Stream={stream_id}, Module={module_id}, User={user_id}, LPDs={lpd_ids}", "IDs", allure.attachment_type.TEXT)
        logger.info("E2E LPD Stage завершён!")