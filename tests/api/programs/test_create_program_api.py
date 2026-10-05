import time
import allure
import pytest
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("Programs API")
@allure.story("Create program")
class TestCreateProgramAPI:
    """Тесты на создание программы через API."""

    @allure.title("Создание программы с валидными данными")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_program_success(self, created_program):
        """Позитивный кейс: создание программы с корректными данными."""

        with allure.step("1. Создать программу через API"):
            start = time.perf_counter()
            program = created_program()
            elapsed = time.perf_counter() - start

        with allure.step("2. Проверить ID программы"):
            assert program["id"], "ID не должен быть пустым"
            allure.attach(str(program["id"]), "Program ID", allure.attachment_type.TEXT)

        with allure.step("3. Проверить название"):
            assert program["name"], "Название не должно быть пустым"
            allure.attach(program["name"], "Name", allure.attachment_type.TEXT)

        with allure.step("4. Проверить статус активности"):
            assert program["attributes"]["is_active"] == True
            allure.attach(str(program["attributes"]["is_active"]), "is_active", allure.attachment_type.TEXT)

        allure.dynamic.description(f"""
        <h3>✅ Программа создана:</h3>
        <ul>
            <li><b>ID:</b> {program['id']}</li>
            <li><b>Название:</b> {program['name']}</li>
            <li><b>Время:</b> {elapsed:.2f} сек</li>
        </ul>
        """)

        logger.info(f"✅ Программа создана: ID={program['id']}, Name={program['name']}")
        logger.info(f"⏱ Время: {elapsed:.2f} сек")

    @allure.title("Создание программы с кастомным названием и цветом")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_create_program_custom(self, created_program):
        """Создание программы с заданными параметрами."""

        with allure.step("Создать программу с кастомными данными"):
            program = created_program(
                name="Моя программа",
                description="<p>Тестовое описание</p>",
                color="ff0000",
                completed_color="cc0000",
                completed_text_color="ffffff"
            )

        with allure.step("Проверить название"):
            assert program["name"] == "Моя программа"
            logger.info(f"✓ Название: {program['name']}")

        with allure.step("Проверить цвета"):
            attrs = program["attributes"]
            assert attrs["color"] == "ff0000"
            logger.info(f"✓ Цвета сохранены: {attrs['color']}")

    @allure.title("Создание неактивной программы")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_create_program_inactive(self, created_program):
        """Создание программы с is_active = False."""

        with allure.step("Создать неактивную программу"):
            program = created_program(is_active=False)

        with allure.step("Проверить статус"):
            assert program["attributes"]["is_active"] == False
            logger.info(f"✓ is_active = False")

    @allure.title("Массовое удаление программ")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "delete", "mass")
    @pytest.mark.api
    def test_mass_delete_programs(self, api_client, programs_endpoint):
        """Создать 3 программы, удалить массово, проверить что удалены."""
        from api.helpers.data_generator import generate_program_payload

        program_ids = []

        with allure.step("1. Создать 3 программы"):
            for i in range(3):
                payload = generate_program_payload(name=f"MassDelete_Test_{i+1}")
                data = programs_endpoint.create(payload)
                program_ids.append(data["id"])
                logger.info(f"  Создана программа #{i+1}: ID={data['id']}")

        allure.attach(str(program_ids), "IDs для удаления", allure.attachment_type.JSON)

        with allure.step("2. Массово удалить через /programs/mass-delete"):
            success = programs_endpoint.mass_delete(program_ids)
            logger.info(f"Mass delete response success={success}")

        with allure.step("3. Проверить, что программы реально удалены"):
            for pid in program_ids:
                resp = api_client.get(f"/programs/{pid}")
                logger.info(f"  Проверка программы {pid}: статус={resp.status_code}")

                if resp.status_code == 200:
                    logger.error(f"  ❌ Программа {pid} НЕ удалена! Всё ещё существует.")
                    pytest.fail(f"Программа {pid} не удалена. Статус 200, программа существует.")
                else:
                    logger.info(f"  ✓ Программа {pid} удалена (статус {resp.status_code})")

    # ==================== НЕГАТИВНЫЕ КЕЙСЫ ====================

    @allure.title("Создание программы без названия")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_program_without_name(self, api_client):
        """Попытка создать программу с пустым названием (name = None)."""
        from api.helpers.data_generator import generate_program_payload

        with allure.step("Отправить запрос без name"):
            payload = generate_program_payload()
            payload["data"]["attributes"]["name"] = None

            resp = api_client.post("/programs", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Пустое название отклонено: статус {resp.status_code}")

    @allure.title("Создание программы с пустым payload")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_program_empty_payload(self, api_client):
        """Попытка создать программу вообще без атрибутов."""

        with allure.step("Отправить запрос с пустыми attributes"):
            payload = {"data": {"attributes": {}}}

            resp = api_client.post("/programs", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"✓ Пустой payload отклонён: статус {resp.status_code}")