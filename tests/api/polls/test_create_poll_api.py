import allure
import pytest
from utils.logger import logger


@allure.feature("Develop Tests")
@allure.story("API Poll Constructor")
class TestApiPollConstructor:

    @allure.title("API Develop: Полный цикл опроса — создать → получить → вопросы → обновить → удалить")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    def test_full_poll_cycle(self, api_client, created_poll, polls_endpoint):
        """Сквозной тест для опроса: создать, получить, добавить вопросы, обновить, удалить."""

        from api.endpoints.tincan import TincanEndpoint
        from api.helpers.data_generator import generate_question_payload, generate_test_update_payload

        # ========== 1. Загрузить обложку и создать опрос ==========
        with allure.step("1. Загрузить обложку и создать опрос"):
            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка загружена: {cover_uuid}")

            poll = created_poll(cover_uuid=cover_uuid)
            assert poll["id"] is not None, "ID пустой"
            assert "Автотест_опрос_админка" in poll["name"], f"Неверное имя: {poll['name']}"
            assert poll["attributes"]["type"] == "poll"
            allure.attach(str(poll["id"]), "Poll ID", allure.attachment_type.TEXT)
            logger.info(f"Создан опрос: ID={poll['id']}, name={poll['name']}")

        # ========== 2. Получить опрос ==========
        with allure.step("2. Получить опрос"):
            fetched = polls_endpoint.get(poll["id"])
            assert fetched["content_id"] == poll["id"], f"ID не совпадает: {fetched['content_id']} != {poll['id']}"
            assert fetched["name"] == poll["name"], f"Имя не совпадает: {fetched['name']} != {poll['name']}"
            assert fetched["type"] == "poll", f"Тип не совпадает: {fetched['type']}"
            logger.info(f"Получен опрос: ID={fetched['content_id']}, name={fetched['name']}")

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
                    result = polls_endpoint.create_question(poll["id"], question)
                    assert result is not None, f"Вопрос #{i} не создался"
                    allure.attach(str(result), f"Question #{i} response", allure.attachment_type.JSON)
                    logger.info(f"Вопрос #{i} добавлен: {text}")

        # ========== 4. Обновить опрос ==========
        with allure.step("4. Обновить опрос"):
            update_payload = generate_test_update_payload(
                content_id=poll["id"],
                name=poll["name"],
                topic="Новая тема опроса",
                cover_uuid=cover_uuid,
                tries_active=False,
                shuffle_questions_active=False,
                shuffle_answers_active=False,
                is_allow_question_move_active=False
            )
            updated = polls_endpoint.update(poll["id"], update_payload)
            assert updated["name"] == poll["name"], f"Имя не должно меняться: {updated['name']}"
            assert updated["topic"] == "Новая тема опроса", f"Тема не обновилась: {updated['topic']}"
            assert updated["settings"]["tries"]["is_active"] == False
            assert updated["settings"]["shuffle_questions"]["is_active"] == False
            assert updated["settings"]["shuffle_answers"]["is_active"] == False
            assert updated["settings"]["is_allow_question_move"]["is_active"] == False
            allure.attach(str(updated), "Updated Poll", allure.attachment_type.JSON)
            logger.info(f"Обновлён опрос: ID={updated['id']}, name={updated['name']}, topic={updated['topic']}")

        # ========== 5. Повторно получить — проверить сохранение ==========
        with allure.step("5. Проверить сохранение изменений"):
            fetched_again = polls_endpoint.get(poll["id"])
            assert fetched_again["name"] == poll["name"], f"Имя изменилось: {fetched_again['name']}"
            assert fetched_again["topic"] == "Новая тема опроса", f"Тема не сохранилась: {fetched_again['topic']}"
            logger.info("Проверка сохранения изменений — OK")

        # ========== 6. Удалить опрос ==========
        logger.info("Полный цикл опроса завершён!")