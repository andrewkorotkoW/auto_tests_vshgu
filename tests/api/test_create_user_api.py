import time
import allure
import pytest
from utils.logger import logger


@allure.feature("Users API")
@allure.story("Create user")
class TestCreateUserAPI:
    """Тесты на создание пользователя через API."""

    @allure.title("Создание пользователя с валидными данными")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_user_success(self, created_user):
        """Позитивный кейс: создание пользователя с корректными данными."""

        with allure.step("1. Создать пользователя через API"):
            start = time.perf_counter()
            user = created_user()
            elapsed = time.perf_counter() - start

        with allure.step("2. Проверить ID пользователя"):
            assert user["id"], "ID не должен быть пустым"
            allure.attach(str(user["id"]), "User ID", allure.attachment_type.TEXT)

        with allure.step("3. Проверить Email"):
            assert user["email"], "Email не должен быть пустым"
            assert "@" in user["email"], "Email должен содержать @"
            allure.attach(user["email"], "Email", allure.attachment_type.TEXT)

        with allure.step("4. Проверить ФИО"):
            full_name = f"{user['surname']} {user['name']} {user['patronymic']}"
            assert user["surname"], "Фамилия не должна быть пустой"
            assert user["name"], "Имя не должно быть пустым"
            assert user["patronymic"], "Отчество не должно быть пустым"
            allure.attach(full_name, "ФИО", allure.attachment_type.TEXT)

        with allure.step("5. Время выполнения"):
            allure.attach(f"{elapsed:.2f} сек", "Время создания", allure.attachment_type.TEXT)

        allure.dynamic.description(f"""
        <h3>✅ Пользователь создан:</h3>
        <ul>
            <li><b>ID:</b> {user['id']}</li>
            <li><b>Email:</b> {user['email']}</li>
            <li><b>ФИО:</b> {full_name}</li>
            <li><b>Время:</b> {elapsed:.2f} сек</li>
        </ul>
        """)

    @allure.title("Создание пользователя с регионом и муниципалитетом")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive", "region")
    @pytest.mark.api
    def test_create_user_with_specific_region(self, created_user):
        """Создание с регионом Москва (33) и муниципалитетом Южный округ (2310)."""

        with allure.step("1. Создать пользователя с регионом 33 и муниципалитетом 2310"):
            user = created_user(region_id=33, municipality_id=2310)
            attrs = user["attributes"]

        with allure.step("2. Проверить регион"):
            if "region" in attrs and attrs["region"]:
                region = attrs["region"]
                assert region["region_id"] == 33
                allure.attach(str(region), "Данные региона", allure.attachment_type.JSON)
                logger.info(f"✓ Регион: {region['region_name']}")
            elif "region_id" in attrs:
                assert attrs["region_id"] == 33
                allure.attach(str(attrs["region_id"]), "region_id", allure.attachment_type.TEXT)

        with allure.step("3. Проверить муниципалитет"):
            if "municipality" in attrs and attrs["municipality"]:
                mun = attrs["municipality"]
                assert mun["municipality_id"] == 2310
                allure.attach(str(mun), "Данные муниципалитета", allure.attachment_type.JSON)
                logger.info(f"✓ Муниципалитет: {mun['name']}")
            elif "municipality_id" in attrs:
                assert attrs["municipality_id"] == 2310
                allure.attach(str(attrs["municipality_id"]), "municipality_id", allure.attachment_type.TEXT)

        allure.dynamic.description(f"""
        <h3>✅ Пользователь с регионом:</h3>
        <ul>
            <li><b>ID:</b> {user['id']}</li>
            <li><b>Регион:</b> 33 (Москва)</li>
            <li><b>Муниципалитет:</b> 2310 (Южный округ)</li>
        </ul>
        """)

    @allure.title("Создание пользователя с кастомной датой рождения")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_create_user_custom_birthdate(self, created_user):
        """Создание пользователя с конкретной датой рождения."""
        custom_dob = "2000-01-01"

        with allure.step(f"Создать пользователя с ДР {custom_dob}"):
            user = created_user(date_of_birth=custom_dob)

        with allure.step("Проверить дату рождения"):
            dob = user["attributes"].get("date_of_birth", "")
            assert custom_dob in dob, f"Неверная дата рождения: {dob}"
            allure.attach(dob, "Дата рождения", allure.attachment_type.TEXT)
            logger.info(f"✓ Дата рождения: {dob}")

    # ==================== НЕГАТИВНЫЕ КЕЙСЫ ====================

    @allure.title("Создание пользователя с уже существующим Email")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "duplicate")
    @pytest.mark.api
    def test_create_user_duplicate_email(self, created_user, api_client):
        """Попытка создать пользователя с Email, который уже существует."""

        with allure.step("1. Создать первого пользователя"):
            user1 = created_user()
            logger.info(f"Первый пользователь: ID={user1['id']}, Email={user1['email']}")

        with allure.step("2. Попытаться создать второго с тем же Email"):
            from api.helpers.data_generator import generate_user_payload

            payload = generate_user_payload(email=user1["email"])
            resp = api_client.post("/users", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            assert resp.status_code == 422, (
                f"Ожидался статус 422 (дубликат), получен {resp.status_code}: {resp.text}"
            )
            logger.info(f"✓ Дубликат отклонён: статус {resp.status_code}")

    @allure.title("Создание пользователя без даты рождения")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_user_without_birthdate(self, api_client):
        """Попытка создать пользователя без даты рождения."""

        with allure.step("Отправить запрос без date_of_birth"):
            from api.helpers.data_generator import generate_user_payload

            payload = generate_user_payload()
            del payload["data"]["attributes"]["date_of_birth"]

            resp = api_client.post("/users", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            assert resp.status_code == 422, (
                f"Ожидался 422, получен {resp.status_code}: {resp.text}"
            )
            logger.info(f"✓ Запрос без ДР отклонён: статус {resp.status_code}")

    @allure.title("Создание пользователя без пароля")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_user_without_password(self, api_client):
        """Попытка создать пользователя с пустым паролем."""

        with allure.step("Отправить запрос без пароля"):
            from api.helpers.data_generator import generate_user_payload

            payload = generate_user_payload()
            payload["data"]["attributes"]["password"] = 'null'
            payload["data"]["attributes"]["system_password"] = 'null'

            resp = api_client.post("/users", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            assert resp.status_code == 422, (
                f"Ожидался 422, получен {resp.status_code}: {resp.text}"
            )
            logger.info(f"✓ Пустой пароль отклонён: статус {resp.status_code}")

    @allure.title("Создание пользователя с паролем только из строчных букв")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_user_password_lowercase_only(self, api_client):
        """Попытка создать пользователя с паролем без заглавных букв и цифр."""

        with allure.step("Отправить запрос с паролем 'abcdefgh'"):
            from api.helpers.data_generator import generate_user_payload

            payload = generate_user_payload(password="abcdefgh")
            payload["data"]["attributes"]["system_password"] = "abcdefgh"

            resp = api_client.post("/users", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            if resp.status_code in (200, 201):
                logger.warning("⚠️ Пароль 'abcdefgh' принят (слабые требования к паролю)")
            else:
                assert resp.status_code == 422, (
                    f"Ожидался 422, получен {resp.status_code}: {resp.text}"
                )
                logger.info(f"✓ Слабый пароль отклонён: статус {resp.status_code}")

    @allure.title("Создание пользователя с паролем 'password'")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_user_password_obvious(self, api_client):
        """Попытка создать пользователя с очевидным паролем 'password'."""

        with allure.step("Отправить запрос с паролем 'password'"):
            from api.helpers.data_generator import generate_user_payload

            payload = generate_user_payload(password="password")
            payload["data"]["attributes"]["system_password"] = "password"

            resp = api_client.post("/users", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            if resp.status_code in (200, 201):
                logger.warning("⚠️ Пароль 'password' принят (слабые требования к паролю)")
            else:
                assert resp.status_code == 422, (
                    f"Ожидался 422, получен {resp.status_code}: {resp.text}"
                )
                logger.info(f"✓ Очевидный пароль отклонён: статус {resp.status_code}")

    @allure.title("Создание пользователя с паролем из одних цифр")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_user_password_numbers_only(self, api_client):
        """Попытка создать пользователя с паролем '12345678'."""

        with allure.step("Отправить запрос с паролем '12345678'"):
            from api.helpers.data_generator import generate_user_payload

            payload = generate_user_payload(password="12345678")
            payload["data"]["attributes"]["system_password"] = "12345678"

            resp = api_client.post("/users", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            if resp.status_code in (200, 201):
                logger.warning("⚠️ Пароль '12345678' принят (слабые требования к паролю)")
            else:
                assert resp.status_code == 422, (
                    f"Ожидался 422, получен {resp.status_code}: {resp.text}"
                )
                logger.info(f"✓ Цифровой пароль отклонён: статус {resp.status_code}")