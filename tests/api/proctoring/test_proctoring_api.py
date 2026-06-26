import allure
import pytest
from utils.logger import logger


@allure.feature("Develop Tests")
@allure.story("API Proctoring")
class TestApiProctoring:

    @allure.title("API Develop: Полный цикл с прокторингом — создать → вопросы → прокторинг → удалить")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    def test_proctoring_cycle(self, api_client, created_test, tests_endpoint):
        """Создать тест, добавить вопросы, активировать прокторинг, удалить."""

        from api.endpoints.tincan import TincanEndpoint
        from api.helpers.data_generator import generate_question_payload, generate_test_update_proctoring_payload

        # ========== 1. Загрузить обложку и создать тест ==========
        with allure.step("1. Загрузить обложку и создать тест"):
            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка загружена: {cover_uuid}")

            test = created_test(cover_uuid=cover_uuid)
            assert test["id"] is not None, "ID пустой"
            assert "Автотест_тест_админка" in test["name"], f"Неверное имя: {test['name']}"
            allure.attach(str(test["id"]), "Test ID", allure.attachment_type.TEXT)
            logger.info(f"Создан тест: ID={test['id']}, name={test['name']}")

        # ========== 2. Добавить 5 вопросов ==========
        with allure.step("2. Добавить 5 вопросов"):
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

        # ========== 3. Активировать прокторинг ==========
        with allure.step("3. Активировать прокторинг"):
            proctoring_payload = generate_test_update_proctoring_payload(
                content_id=test["id"],
                name=test["name"],
                is_active=True,
                mode="offline"
            )
            updated = tests_endpoint.update(test["id"], proctoring_payload)
            assert updated["settings"]["proctoring"]["is_active"] == True, "Прокторинг не активировался"
            assert updated["settings"]["proctoring"]["mode"] == "offline"
            assert updated["settings"]["proctoring"]["allow_to_use_websites"] == True
            assert updated["settings"]["proctoring"]["allow_to_use_books"] == True
            assert updated["settings"]["proctoring"]["allow_to_use_calculator"] == True
            allure.attach(str(updated), "Proctoring Activated", allure.attachment_type.JSON)
            logger.info(f"Прокторинг активирован для теста ID={test['id']}")

        # ========== 4. Проверить сохранение ==========
        with allure.step("4. Проверить сохранение прокторинга"):
            fetched = tests_endpoint.get(test["id"])
            assert fetched["settings"]["proctoring"]["is_active"] == True, "Прокторинг не сохранился"
            logger.info("Проверка сохранения прокторинга — OK")

        logger.info("Полный цикл с прокторингом завершён!")