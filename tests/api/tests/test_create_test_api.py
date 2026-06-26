import allure
import pytest
from utils.logger import logger


@allure.feature("Develop Tests")
@allure.story("API Test Constructor")
class TestApiTestConstructor:

    @allure.title("API Develop: Полный цикл — создать → получить → вопросы → обновить → удалить")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    def test_full_cycle(self, api_client, created_test, tests_endpoint):
        """Сквозной тест: создать, получить, добавить 5 вопросов, обновить, удалить."""

        from api.endpoints.tincan import TincanEndpoint
        from api.helpers.data_generator import generate_question_payload, generate_test_update_payload

        # ========== 1. Загрузить обложку и создать тест ==========
        with allure.step("1. Загрузить обложку и создать тест"):
            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка загружена: {cover_uuid}")

            test = created_test(cover_uuid=cover_uuid)
            assert test["id"] is not None, "ID пустой"
            assert "Автотест_тест_админка" in test["name"], f"Неверное имя: {test['name']}"
            assert test["attributes"]["type"] == "test"
            allure.attach(str(test["id"]), "Test ID", allure.attachment_type.TEXT)
            logger.info(f"Создан: ID={test['id']}, name={test['name']}")

        # ========== 2. Получить тест ==========
        with allure.step("2. Получить тест"):
            fetched = tests_endpoint.get(test["id"])
            assert fetched["content_id"] == test["id"]
            assert fetched["name"] == test["name"]
            assert fetched["type"] == "test"
            logger.info(f"Получен: ID={fetched['content_id']}")

        # ========== 3. Добавить 5 вопросов ==========
        with allure.step("3. Добавить 5 вопросов"):
            question_texts = [
                "Первый вопрос",
                "Второй вопрос",
                "Третий вопрос",
                "Четвёртый вопрос",
                "Пятый вопрос"
            ]

            for i, text in enumerate(question_texts, start=1):
                with allure.step(f"Вопрос #{i}: {text}"):
                    question = generate_question_payload(
                        order=i,
                        text=text,
                        question_type="single" if i % 2 == 1 else "multi"
                    )
                    result = tests_endpoint.create_question(test["id"], question)
                    assert result is not None, f"Вопрос #{i} не создался"
                    allure.attach(str(result), f"Question #{i} response", allure.attachment_type.JSON)
                    logger.info(f"Вопрос #{i} добавлен: {text}")

        # ========== 4. Обновить тест ==========
        with allure.step("4. Обновить тест"):
            update_payload = generate_test_update_payload(
                content_id=test["id"],
                name=test["name"],
                topic="Новая тема",
                cover_uuid=cover_uuid,
                tries_active=False,
                shuffle_questions_active=False,
                shuffle_answers_active=False,
                is_allow_question_move_active=False
            )
            updated = tests_endpoint.update(test["id"], update_payload)
            assert updated["name"] == test["name"], f"Имя не должно меняться: {updated['name']}"
            assert updated["topic"] == "Новая тема"
            assert updated["settings"]["tries"]["is_active"] == False
            assert updated["settings"]["shuffle_questions"]["is_active"] == False
            assert updated["settings"]["shuffle_answers"]["is_active"] == False
            assert updated["settings"]["is_allow_question_move"]["is_active"] == False
            allure.attach(str(updated), "Updated Test", allure.attachment_type.JSON)
            logger.info(f"Обновлён: ID={updated['id']}, name={updated['name']}")

        # ========== 5. Повторно получить — проверить сохранение ==========
        with allure.step("5. Проверить сохранение изменений"):
            fetched_again = tests_endpoint.get(test["id"])
            assert fetched_again["name"] == test["name"]
            assert fetched_again["topic"] == "Новая тема"
            logger.info("Проверка сохранения изменений — OK")

        # ========== 6. Удалить тест ==========
        logger.info("Полный цикл завершён!")