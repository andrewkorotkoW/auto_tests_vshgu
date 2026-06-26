import time
import allure
import pytest
from utils.logger import logger


@allure.feature("E2E Flow")
@allure.story("Program → Stream → Module → Schedule Item → AOS → Assign → Activate")
class TestE2EProgramFlow:
    """End-to-end: полный цикл создания сущностей."""

    @allure.title("E2E: Полный цикл с назначением пользователя")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("e2e", "api", "smoke")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_full_e2e_flow(
        self, api_client, created_program, created_user,
        streams_endpoint, modules_endpoint, assignments_endpoint
    ):
        """Полный цикл: программа, поток, модуль, schedule item, АОС, пользователь, назначение, активация."""

        with allure.step("1. Создать программу"):
            program = created_program(name="E2E_Full_Program")
            logger.info(f"✅ Программа: ID={program['id']}")

        with allure.step("2. Создать поток"):
            from api.helpers.data_generator import generate_stream_payload
            stream_payload = generate_stream_payload(name="E2E_Full_Stream")
            stream_data = streams_endpoint.create(program["id"], stream_payload)
            stream_id = stream_data["id"]
            logger.info(f"✅ Поток: ID={stream_id}")

        with allure.step("3. Создать модуль"):
            from api.helpers.data_generator import generate_module_payload
            module_payload = generate_module_payload(name="E2E_Full_Module")
            module_data = modules_endpoint.create(program["id"], stream_id, module_payload)
            module_id = module_data["id"]
            logger.info(f"✅ Модуль: ID={module_id}")

        with allure.step("4. Создать элемент расписания"):
            from api.endpoints.schedule_items import ScheduleItemsEndpoint
            from api.helpers.data_generator import generate_schedule_item_payload

            schedule_endpoint = ScheduleItemsEndpoint(api_client)
            schedule_payload = generate_schedule_item_payload(name="E2E_Full_Schedule")
            schedule_data = schedule_endpoint.create(program["id"], stream_id, module_id, schedule_payload)
            schedule_id = schedule_data["id"]
            logger.info(f"✅ Элемент расписания: ID={schedule_id}")

        with allure.step("5. Создать АОС"):
            from api.endpoints.aos import AosEndpoint
            from api.helpers.data_generator import generate_aos_payload

            aos_endpoint = AosEndpoint(api_client)
            aos_payload = generate_aos_payload(name="E2E_Full_AOS", schedule_item_ids=[schedule_id])
            aos_data = aos_endpoint.create(aos_payload)
            aos_id = aos_data["content_id"]
            logger.info(f"✅ АОС создан: ID={aos_id}")

        with allure.step("6. Создать пользователя"):
            user = created_user()
            user_id = user["id"]
            logger.info(f"✅ Пользователь: ID={user_id}, Email={user['email']}")

        with allure.step("7. Назначить пользователя в поток"):
            assignments_endpoint.assign(program["id"], stream_id, [user_id])
            logger.info(f"✅ Пользователь {user_id} назначен в поток {stream_id}")

        with allure.step("8. Активировать АОС"):
            success = aos_endpoint.activate(program["id"], stream_id, aos_id)
            assert success, "Не удалось активировать АОС"
            logger.info(f"✅ АОС активирован")

        with allure.step("9. Проверить АОС"):
            aos_get = aos_endpoint.get(aos_id)
            assert aos_get["name"] == "E2E_Full_AOS"
            logger.info("✓ АОС подтвержден")

        with allure.step("10. Очистка"):
            schedule_endpoint.delete(program["id"], stream_id, module_id, schedule_id)
            logger.info(f"🗑️ Schedule Item удалён: {schedule_id}")
            modules_endpoint.delete(program["id"], stream_id, module_id)
            logger.info(f"🗑️ Модуль удалён: {module_id}")
            streams_endpoint.delete(program["id"], stream_id)
            logger.info(f"🗑️ Поток удалён: {stream_id}")

        allure.dynamic.description(f"""
        <h3>✅ E2E Full Flow:</h3>
        <ol>
            <li>Программа: {program['id']}</li>
            <li>Поток: {stream_id}</li>
            <li>Модуль: {module_id}</li>
            <li>Schedule Item: {schedule_id}</li>
            <li>АОС: {aos_id}</li>
            <li>Пользователь: {user_id} ({user['email']})</li>
            <li>Назначение в поток ✅</li>
            <li>Активация ✅</li>
            
        </ol>
        """)

