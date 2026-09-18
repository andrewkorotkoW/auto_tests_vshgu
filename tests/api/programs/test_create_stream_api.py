import time
import allure
import pytest
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("Streams API")
@allure.story("Create stream")
class TestCreateStreamAPI:
    """Тесты на создание потока через API."""

    @allure.title("Создание потока с валидными данными")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_stream_success(self, created_stream):
        """Позитивный кейс: создание потока с корректными данными."""

        with allure.step("1. Создать поток через API"):
            start = time.perf_counter()
            stream = created_stream()
            elapsed = time.perf_counter() - start

        with allure.step("2. Проверить ID потока"):
            assert stream["id"], "ID не должен быть пустым"
            allure.attach(str(stream["id"]), "Stream ID", allure.attachment_type.TEXT)

        with allure.step("3. Проверить название"):
            assert stream["name"], "Название не должно быть пустым"
            allure.attach(stream["name"], "Name", allure.attachment_type.TEXT)

        with allure.step("4. Проверить program_id"):
            assert stream["program_id"], "program_id не должен быть пустым"
            allure.attach(str(stream["program_id"]), "Program ID", allure.attachment_type.TEXT)

        allure.dynamic.description(f"""
        <h3>✅ Поток создан:</h3>
        <ul>
            <li><b>ID потока:</b> {stream['id']}</li>
            <li><b>ID программы:</b> {stream['program_id']}</li>
            <li><b>Название:</b> {stream['name']}</li>
            <li><b>Время:</b> {elapsed:.2f} сек</li>
        </ul>
        """)

        logger.info(f"✅ Поток создан: ID={stream['id']}, Name={stream['name']}")
        logger.info(f"⏱ Время: {elapsed:.2f} сек")

    @allure.title("Создание потока с кастомными параметрами")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_create_stream_custom(self, created_stream):
        """Создание потока с заданным названием и локацией."""

        with allure.step("Создать поток с кастомными данными"):
            stream = created_stream(
                name="Кастомный поток",
                location="Санкт-Петербург",
                date_from="2026-06-01",
                date_to="2026-07-15",
                duration="200"
            )

        with allure.step("Проверить название"):
            assert stream["name"] == "Кастомный поток"
            logger.info(f"✓ Название: {stream['name']}")

        with allure.step("Проверить атрибуты"):
            attrs = stream["attributes"]
            assert attrs["location"] == "Санкт-Петербург"
            assert attrs["duration"] == "200"
            logger.info(f"✓ Локация: {attrs['location']}, Длительность: {attrs['duration']}")

    # ==================== НЕГАТИВНЫЕ КЕЙСЫ ====================

    @allure.title("Создание потока без названия")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_stream_without_name(self, created_program, streams_endpoint, api_client):
        """Попытка создать поток с пустым названием."""
        from api.helpers.data_generator import generate_stream_payload

        with allure.step("1. Создать программу"):
            program = created_program()
            logger.info(f"Программа создана: ID={program['id']}")

        with allure.step("2. Попытаться создать поток без названия"):
            payload = generate_stream_payload()
            payload["data"]["attributes"]["name"] = None

            resp = api_client.post(f"/programs/{program['id']}/streams", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Пустое название отклонено: статус {resp.status_code}")

    @allure.title("Создание потока без даты начала")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_stream_without_date_from(self, created_program, streams_endpoint, api_client):
        """Попытка создать поток без date_from."""
        from api.helpers.data_generator import generate_stream_payload

        with allure.step("1. Создать программу"):
            program = created_program()
            logger.info(f"Программа создана: ID={program['id']}")

        with allure.step("2. Попытаться создать поток без date_from"):
            payload = generate_stream_payload()
            del payload["data"]["attributes"]["date_from"]

            resp = api_client.post(f"/programs/{program['id']}/streams", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Без date_from отклонено: статус {resp.status_code}")

    @allure.title("Создание потока без academic_directors")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_stream_without_academic_directors(self, created_program, streams_endpoint, api_client):
        """Попытка создать поток с пустым списком academic_directors."""
        from api.helpers.data_generator import generate_stream_payload

        with allure.step("1. Создать программу"):
            program = created_program()
            logger.info(f"Программа создана: ID={program['id']}")

        with allure.step("2. Попытаться создать поток без academic_directors"):
            payload = generate_stream_payload()
            payload["data"]["attributes"]["academic_directors"] = []

            resp = api_client.post(f"/programs/{program['id']}/streams", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Пустые academic_directors отклонены: статус {resp.status_code}")

    @allure.title("Создание потока для несуществующей программы")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_stream_invalid_program(self, api_client):
        """Попытка создать поток для несуществующей программы."""
        from api.helpers.data_generator import generate_stream_payload

        with allure.step("Попытаться создать поток с несуществующим program_id"):
            payload = generate_stream_payload(name="Поток без программы")
            resp = api_client.post("/programs/999999/streams", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 404)
            logger.info(f"✓ Несуществующая программа отклонена: статус {resp.status_code}")