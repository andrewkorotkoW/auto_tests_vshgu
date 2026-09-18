import time
import allure
import pytest
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("AOS API")
@allure.story("Create AOS")
class TestCreateAosAPI:
    """Тесты на создание АОС через API."""

    @allure.title("Создание и активация АОС с привязкой к schedule item")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_aos_with_schedule_item(self, created_aos, aos_endpoint):
        """Создание АОС, привязанного к элементу расписания, и его активация."""

        with allure.step("1. Создать АОС"):
            start = time.perf_counter()
            aos = created_aos()
            elapsed = time.perf_counter() - start

        with allure.step("2. Проверить ID"):
            assert aos["id"], "ID не должен быть пустым"
            allure.attach(str(aos["id"]), "AOS ID", allure.attachment_type.TEXT)

        with allure.step("3. Проверить название"):
            assert aos["name"], "Название не должно быть пустым"
            allure.attach(aos["name"], "Name", allure.attachment_type.TEXT)

        with allure.step("4. Проверить привязку к schedule item"):
            assert aos["schedule_item_id"], "schedule_item_id не должен быть пустым"
            allure.attach(str(aos["schedule_item_id"]), "Schedule Item ID", allure.attachment_type.TEXT)

        with allure.step("5. Активировать АОС"):
            program_id = aos["program_id"]
            stream_id = aos["stream_id"]
            success = aos_endpoint.activate(program_id, stream_id, aos["id"])
            assert success, f"Не удалось активировать АОС {aos['id']}"
            logger.info(f"✓ АОС активирован")

        with allure.step("6. Сохранить состояние в отчёт"):
            import json
            state = {
                "aos_id": aos["id"],
                "aos_name": aos["name"],
                "program_id": program_id,
                "stream_id": stream_id,
                "schedule_item_id": aos["schedule_item_id"],
                "active": True
            }
            allure.attach(
                json.dumps(state, indent=2, ensure_ascii=False),
                name="AOS_STATE",
                attachment_type=allure.attachment_type.JSON
            )

        allure.dynamic.description(f"""
        <h3>✅ АОС создан и активирован:</h3>
        <ul>
            <li><b>ID:</b> {aos['id']}</li>
            <li><b>Название:</b> {aos['name']}</li>
            <li><b>Schedule Item:</b> {aos['schedule_item_id']}</li>
            <li><b>Программа:</b> {program_id}</li>
            <li><b>Поток:</b> {stream_id}</li>
            <li><b>Время:</b> {elapsed:.2f} сек</li>
        </ul>
        """)

        logger.info(f"✅ АОС создан и активирован: ID={aos['id']}")
        logger.info(f"⏱ Время: {elapsed:.2f} сек")

    # ==================== НЕГАТИВНЫЕ ====================

    @allure.title("Создание АОС без названия")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_aos_without_name(self, aos_endpoint, api_client, created_schedule_item):
        """Попытка создать АОС без названия → 422."""
        from api.helpers.data_generator import generate_aos_payload

        with allure.step("1. Создать schedule item"):
            item = created_schedule_item()

        with allure.step("2. Отправить запрос без названия"):
            payload = generate_aos_payload(schedule_item_ids=[item["id"]])
            payload["name"] = None

            resp = api_client.post("/tests", json=payload)
            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Без названия отклонено: {resp.status_code}")