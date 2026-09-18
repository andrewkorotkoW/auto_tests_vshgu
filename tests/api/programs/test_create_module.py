import time
import allure
import pytest
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("Modules API")
@allure.story("Create module")
class TestCreateModuleAPI:
    """Тесты на создание модуля через API."""

    @allure.title("Создание модуля с валидными данными")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_module_success(self, created_module):
        """Позитивный кейс: создание модуля с корректными данными."""

        with allure.step("1. Создать модуль через API"):
            start = time.perf_counter()
            module = created_module()
            elapsed = time.perf_counter() - start

        with allure.step("2. Проверить ID модуля"):
            assert module["id"], "ID не должен быть пустым"
            allure.attach(str(module["id"]), "Module ID", allure.attachment_type.TEXT)

        with allure.step("3. Проверить название"):
            assert module["name"], "Название не должно быть пустым"
            allure.attach(module["name"], "Name", allure.attachment_type.TEXT)

        with allure.step("4. Проверить привязку к программе и потоку"):
            assert module["program_id"], "program_id не должен быть пустым"
            assert module["stream_id"], "stream_id не должен быть пустым"
            allure.attach(
                f"program={module['program_id']}, stream={module['stream_id']}",
                "Связи",
                allure.attachment_type.TEXT
            )

        allure.dynamic.description(f"""
        <h3>✅ Модуль создан:</h3>
        <ul>
            <li><b>ID:</b> {module['id']}</li>
            <li><b>Программа:</b> {module['program_id']}</li>
            <li><b>Поток:</b> {module['stream_id']}</li>
            <li><b>Название:</b> {module['name']}</li>
            <li><b>Время:</b> {elapsed:.2f} сек</li>
        </ul>
        """)

        logger.info(f"✅ Модуль создан: ID={module['id']}, Name={module['name']}")
        logger.info(f"⏱ Время: {elapsed:.2f} сек")

    # ==================== НЕГАТИВНЫЕ КЕЙСЫ ====================

    @allure.title("Создание модуля с датами вне диапазона потока")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_module_dates_outside_stream(
            self, created_program, streams_endpoint, modules_endpoint, api_client
    ):
        """Модуль с датами, выходящими за даты потока → 422."""
        from api.helpers.data_generator import generate_stream_payload, generate_module_payload

        with allure.step("1. Создать программу"):
            program = created_program()
            logger.info(f"Программа: ID={program['id']}")

        with allure.step("2. Создать поток с датами 2026-06-01 → 2026-06-30"):
            stream_payload = generate_stream_payload(
                name="Stream_for_date_test",
                date_from="2026-06-01",
                date_to="2026-06-30"
            )
            stream_data = streams_endpoint.create(program["id"], stream_payload)
            stream_id = stream_data["id"]
            logger.info(f"Поток: ID={stream_id} (01.06.2026 – 30.06.2026)")

        with allure.step("3. Попытаться создать модуль с датами РАНЬШЕ потока"):
            module_payload = generate_module_payload(
                name="Module_before_stream",
                date_from="2026-05-01",
                date_to="2026-05-31"
            )
            resp = api_client.post(
                f"/programs/{program['id']}/streams/{stream_id}/modules",
                json=module_payload
            )
            allure.attach(str(resp.status_code), "Status (даты раньше)", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response (даты раньше)", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Даты раньше потока отклонены: {resp.status_code}")

        with allure.step("4. Попытаться создать модуль с датами ПОЗЖЕ потока"):
            module_payload2 = generate_module_payload(
                name="Module_after_stream",
                date_from="2026-07-01",
                date_to="2026-07-31"
            )
            resp2 = api_client.post(
                f"/programs/{program['id']}/streams/{stream_id}/modules",
                json=module_payload2
            )
            allure.attach(str(resp2.status_code), "Status (даты позже)", allure.attachment_type.TEXT)
            allure.attach(resp2.text, "Response (даты позже)", allure.attachment_type.TEXT)

            expect_status(resp2, 422)
            logger.info(f"✓ Даты позже потока отклонены: {resp2.status_code}")

    @allure.title("Создание модуля без региона при must_use_module_region=True")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_module_without_region(
            self, created_program, streams_endpoint, modules_endpoint, api_client
    ):
        """Обновление модуля с must_use_module_region=True, но без region → 422."""
        from api.helpers.data_generator import generate_module_payload, generate_module_update_payload

        with allure.step("1. Создать программу → поток → модуль"):
            program = created_program()
            stream_payload = __import__('api.helpers.data_generator',
                                        fromlist=['generate_stream_payload']).generate_stream_payload()
            stream_data = streams_endpoint.create(program["id"], stream_payload)
            stream_id = stream_data["id"]

            module_payload = generate_module_payload(name="Module_region_test")
            module_data = modules_endpoint.create(program["id"], stream_id, module_payload)
            module_id = module_data["id"]
            logger.info(f"Модуль создан: ID={module_id}")

        with allure.step("2. Обновить модуль: must_use_module_region=True, но без region"):
            update_payload = {
                "data": {
                    "attributes": {
                        "name": "Module_no_region",
                        "location": "Москва",
                        "date_from": "2026-06-01",
                        "date_to": "2026-06-30",
                        "must_use_module_region": True
                        # region отсутствует
                    }
                }
            }
            resp = api_client.put(
                f"/programs/{program['id']}/streams/{stream_id}/modules/{module_id}",
                json=update_payload
            )
            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Отсутствие region отклонено: {resp.status_code}")

    @allure.title("Создание модуля без названия")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_module_without_name(
            self, created_program, streams_endpoint, api_client
    ):
        """Попытка создать модуль без названия → 422."""
        from api.helpers.data_generator import generate_stream_payload, generate_module_payload

        with allure.step("1. Создать программу → поток"):
            program = created_program()
            stream_payload = generate_stream_payload()
            stream_data = streams_endpoint.create(program["id"], stream_payload)
            stream_id = stream_data["id"]

        with allure.step("2. Попытаться создать модуль без названия"):
            module_payload = generate_module_payload()
            module_payload["data"]["attributes"]["name"] = None

            resp = api_client.post(
                f"/programs/{program['id']}/streams/{stream_id}/modules",
                json=module_payload
            )
            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Без названия отклонено: {resp.status_code}")

    @allure.title("Создание модуля без даты начала")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_module_without_date_from(
            self, created_program, streams_endpoint, api_client
    ):
        """Попытка создать модуль без date_from → 422."""
        from api.helpers.data_generator import generate_stream_payload, generate_module_payload

        with allure.step("1. Создать программу → поток"):
            program = created_program()
            stream_payload = generate_stream_payload()
            stream_data = streams_endpoint.create(program["id"], stream_payload)
            stream_id = stream_data["id"]

        with allure.step("2. Попытаться создать модуль без date_from"):
            module_payload = generate_module_payload()
            del module_payload["data"]["attributes"]["date_from"]

            resp = api_client.post(
                f"/programs/{program['id']}/streams/{stream_id}/modules",
                json=module_payload
            )
            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Без date_from отклонено: {resp.status_code}")