import allure
import pytest
from utils.logger import logger
from api.helpers.data_generator import get_next_lpd_id


@allure.feature("E2E Flow")
@allure.story("Program → Stream → Module → User → LPD → Assign → Detach")
class TestE2ELpdFlow:
    """End-to-end: создание LPD и назначение пользователя."""

    @allure.title("E2E: Программа → Поток → Модуль → Пользователь → LPD → Назначение → Открепление")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("e2e", "api", "smoke")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_e2e_lpd_flow(self, api_client, created_program, created_stream, created_module, created_user, created_lpd, lpd_endpoint, assignments_endpoint):
        """Полный цикл LPD."""

        with allure.step("1. Создать программу"):
            program = created_program(name="E2E_LPD_Program")
            logger.info(f"Программа: ID={program['id']}")

        with allure.step("2. Создать поток"):
            stream = created_stream(program_id=program["id"])
            logger.info(f"Поток: ID={stream['id']}")

        with allure.step("3. Создать модуль"):
            module = created_module(program_id=program["id"], stream_id=stream["id"])
            logger.info(f"Модуль: ID={module['id']}")

        with allure.step("4. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: ID={user['id']}, Email={user['email']}")

        with allure.step("5. Назначить пользователя на поток"):
            assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])
            logger.info("Пользователь назначен на поток")

        with allure.step("6. Создать LPD"):
            lpd_id = get_next_lpd_id()
            lpd = created_lpd(lpd_id=lpd_id)
            logger.info(f"LPD: ID={lpd['id']}")

        with allure.step("7. Назначить LPD в модуль"):
            lpd_endpoint.assign_to_module(program["id"], stream["id"], module["id"], [lpd["id"]])
            logger.info("LPD назначен в модуль")

        with allure.step("8. Назначить пользователя на LPD"):
            lpd_endpoint.assign_users(module["id"], lpd["id"], stream["id"], [user["id"]])
            logger.info(f"Пользователь {user['id']} назначен на LPD")

        with allure.step("9. Открепить пользователя от LPD"):
            success = lpd_endpoint.detach_users(module["id"], lpd["id"], stream["id"], [user["id"]])
            assert success, "Не удалось открепить пользователя"
            logger.info("Пользователь откреплён от LPD")

        allure.dynamic.description(f"""
        <h3>E2E LPD Flow:</h3>
        <ol>
            <li>Программа: {program['id']}</li>
            <li>Поток: {stream['id']}</li>
            <li>Модуль: {module['id']}</li>
            <li>Пользователь: {user['id']} ({user['email']})</li>
            <li>LPD: {lpd['id']}</li>
            <li>Назначение в модуль ✅</li>
            <li>Назначение пользователя ✅</li>
            <li>Открепление пользователя ✅</li>
        </ol>
        """)