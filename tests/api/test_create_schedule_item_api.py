import time
import allure
import pytest
from utils.logger import logger


@allure.feature("Schedule Items API")
@allure.story("Create schedule item")
class TestCreateScheduleItemAPI:
    """Тесты на создание элемента расписания."""

    @allure.title("Создание элемента расписания с валидными данными")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_schedule_item_success(self, created_schedule_item):
        """Позитивный кейс: создание элемента расписания."""

        with allure.step("1. Создать элемент расписания"):
            start = time.perf_counter()
            item = created_schedule_item()
            elapsed = time.perf_counter() - start

        with allure.step("2. Проверить ID"):
            assert item["id"], "ID не должен быть пустым"
            allure.attach(str(item["id"]), "Item ID", allure.attachment_type.TEXT)

        with allure.step("3. Проверить название"):
            assert item["name"], "Название не должно быть пустым"
            allure.attach(item["name"], "Name", allure.attachment_type.TEXT)

        with allure.step("4. Проверить регион"):
            region = item["attributes"].get("region", {})
            if region:
                assert region.get("region_id") == 33
                allure.attach(str(region), "Region", allure.attachment_type.JSON)

        allure.dynamic.description(f"""
        <h3>✅ Элемент расписания создан:</h3>
        <ul>
            <li><b>ID:</b> {item['id']}</li>
            <li><b>Название:</b> {item['name']}</li>
            <li><b>Программа:</b> {item['program_id']}</li>
            <li><b>Поток:</b> {item['stream_id']}</li>
            <li><b>Модуль:</b> {item['module_id']}</li>
            <li><b>Время:</b> {elapsed:.2f} сек</li>
        </ul>
        """)

        logger.info(f"✅ Элемент расписания создан: ID={item['id']}, Name={item['name']}")
        logger.info(f"⏱ Время: {elapsed:.2f} сек")

    @allure.title("Создание элемента расписания без учителей")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_create_schedule_item_no_teacher(self, created_schedule_item):
        """Создание элемента расписания с пустым teacher_ids."""

        with allure.step("Создать элемент без учителей"):
            item = created_schedule_item(teacher_ids=[])

        with allure.step("Проверить, что создан"):
            assert item["id"], "ID должен быть"
            logger.info(f"✓ Элемент без учителей создан: ID={item['id']}")

    @allure.title("Создание элемента расписания с несколькими учителями")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_create_schedule_item_multiple_teachers(self, created_schedule_item):
        """Создание элемента расписания с teacher_ids=[4, 1]."""

        with allure.step("Создать элемент с двумя учителями"):
            item = created_schedule_item(teacher_ids=[4, 1])

        with allure.step("Проверить, что создан"):
            assert item["id"], "ID должен быть"
            logger.info(f"✓ Элемент с учителями [4, 1] создан: ID={item['id']}")

    # ==================== НЕГАТИВНЫЕ КЕЙСЫ ====================

    @allure.title("Создание элемента расписания без названия")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_schedule_item_without_name(
        self, created_program, streams_endpoint, modules_endpoint, api_client
    ):
        """Попытка создать элемент расписания без названия → 422."""
        from api.helpers.data_generator import (
            generate_stream_payload, generate_module_payload, generate_schedule_item_payload
        )

        with allure.step("1. Создать программу → поток → модуль"):
            program = created_program()
            stream = streams_endpoint.create(program["id"], generate_stream_payload())
            module = modules_endpoint.create(program["id"], stream["id"], generate_module_payload())

        with allure.step("2. Попытаться создать элемент без названия"):
            payload = generate_schedule_item_payload()
            payload["data"]["attributes"]["name"] = None

            resp = api_client.post(
                f"/programs/{program['id']}/streams/{stream['id']}/modules/{module['id']}/schedule-items",
                json=payload
            )
            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            assert resp.status_code == 422, (
                f"Ожидался 422, получен {resp.status_code}: {resp.text}"
            )
            logger.info(f"✓ Без названия отклонено: {resp.status_code}")

    @allure.title("Создание элемента расписания без региона")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_schedule_item_without_region(
        self, created_program, streams_endpoint, modules_endpoint, api_client
    ):
        """Попытка создать элемент расписания без region → 422."""
        from api.helpers.data_generator import (
            generate_stream_payload, generate_module_payload, generate_schedule_item_payload
        )

        with allure.step("1. Создать программу → поток → модуль"):
            program = created_program()
            stream = streams_endpoint.create(program["id"], generate_stream_payload())
            module = modules_endpoint.create(program["id"], stream["id"], generate_module_payload())

        with allure.step("2. Попытаться создать элемент без region"):
            payload = generate_schedule_item_payload()
            del payload["data"]["attributes"]["region"]

            resp = api_client.post(
                f"/programs/{program['id']}/streams/{stream['id']}/modules/{module['id']}/schedule-items",
                json=payload
            )
            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            assert resp.status_code == 422, (
                f"Ожидался 422, получен {resp.status_code}: {resp.text}"
            )
            logger.info(f"✓ Без region отклонено: {resp.status_code}")

    @allure.title("Создание элемента расписания с датами вне модуля")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_schedule_item_dates_outside_module(
        self, created_program, streams_endpoint, modules_endpoint, api_client
    ):
        """Элемент с датами, выходящими за даты модуля → 422."""
        from api.helpers.data_generator import (
            generate_stream_payload, generate_module_payload, generate_schedule_item_payload
        )

        with allure.step("1. Создать программу"):
            program = created_program()

        with allure.step("2. Создать поток с датами 2026-06-01 → 2026-06-30"):
            stream_payload = generate_stream_payload(
                name="Stream_dates_test",
                date_from="2026-06-01",
                date_to="2026-06-30"
            )
            stream = streams_endpoint.create(program["id"], stream_payload)

        with allure.step("3. Создать модуль с датами 2026-06-01 → 2026-06-30"):
            module_payload = generate_module_payload(
                name="Module_dates_test",
                date_from="2026-06-01",
                date_to="2026-06-30"
            )
            module = modules_endpoint.create(program["id"], stream["id"], module_payload)
            logger.info(f"Модуль: 01.06.2026 – 30.06.2026")

        with allure.step("4. Попытаться создать элемент с датами РАНЬШЕ модуля"):
            payload = generate_schedule_item_payload(
                name="Item_before_module",
                date_time_from="2026-05-01T10:05",
                date_time_to="2026-05-01T11:05"
            )
            resp = api_client.post(
                f"/programs/{program['id']}/streams/{stream['id']}/modules/{module['id']}/schedule-items",
                json=payload
            )
            allure.attach(str(resp.status_code), "Status (даты раньше)", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response (даты раньше)", allure.attachment_type.TEXT)

            assert resp.status_code == 422, (
                f"Ожидался 422 на даты раньше модуля, получен {resp.status_code}: {resp.text}"
            )
            logger.info(f"✓ Даты раньше модуля отклонены: {resp.status_code}")

        with allure.step("5. Попытаться создать элемент с датами ПОЗЖЕ модуля"):
            payload2 = generate_schedule_item_payload(
                name="Item_after_module",
                date_time_from="2026-07-01T10:05",
                date_time_to="2026-07-01T11:05"
            )
            resp2 = api_client.post(
                f"/programs/{program['id']}/streams/{stream['id']}/modules/{module['id']}/schedule-items",
                json=payload2
            )
            allure.attach(str(resp2.status_code), "Status (даты позже)", allure.attachment_type.TEXT)
            allure.attach(resp2.text, "Response (даты позже)", allure.attachment_type.TEXT)

            assert resp2.status_code == 422, (
                f"Ожидался 422 на даты позже модуля, получен {resp2.status_code}: {resp2.text}"
            )
            logger.info(f"✓ Даты позже модуля отклонены: {resp2.status_code}")