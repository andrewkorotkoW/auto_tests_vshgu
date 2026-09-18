import allure
import pytest
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("E2E Content API")
@allure.story("E2E Content to Module")
class TestE2EContentToModule:

    def _setup_program_flow(self, api_client, assignments_endpoint, name_prefix):
        """Общая часть: программа → поток → модуль → пользователь → назначение."""
        session = api_client.session
        base = api_client.base_url

        def post(path, json_data):
            r = session.post(f"{base}{path}", json=json_data)
            expect_status(r, (200, 201))
            return r.json()

        with allure.step("1. Создать программу"):
            from api.helpers.data_generator import generate_program_payload
            r = post("/programs", generate_program_payload(name=f"E2E_{name_prefix}"))
            prog_id = r["data"]["id"]
            logger.info(f"Программа: {prog_id}")

        with allure.step("2. Создать поток"):
            from api.helpers.data_generator import generate_stream_payload
            r = post(f"/programs/{prog_id}/streams", generate_stream_payload())
            stream_id = r["data"]["id"]
            logger.info(f"Поток: {stream_id}")

        with allure.step("3. Создать модуль"):
            from api.helpers.data_generator import generate_module_payload
            r = post(f"/programs/{prog_id}/streams/{stream_id}/modules", generate_module_payload())
            mod_id = r["data"]["id"]
            logger.info(f"Модуль: {mod_id}")

        with allure.step("4. Создать пользователя"):
            from api.helpers.data_generator import generate_user_payload
            r = post("/users", generate_user_payload())
            user_id = r["data"]["id"]
            logger.info(f"Пользователь: {user_id}")

        with allure.step("5. Назначить пользователя на поток"):
            assignments_endpoint.assign(prog_id, stream_id, [user_id])

        return {
            "session": session,
            "base": base,
            "post": post,
            "prog_id": prog_id,
            "stream_id": stream_id,
            "mod_id": mod_id,
            "user_id": user_id
        }

    def _cleanup(self, api_client, prog_id, stream_id, mod_id, user_id, content_ids=None):
        """Очистка данных."""
        from api.endpoints.tests import TestsEndpoint
        from api.endpoints.programs import ProgramsEndpoint
        from api.endpoints.streams import StreamsEndpoint
        from api.endpoints.modules import ModulesEndpoint
        from api.endpoints.users import UsersEndpoint

        if content_ids:
            TestsEndpoint(api_client).mass_delete(content_ids)
        ModulesEndpoint(api_client).delete(prog_id, stream_id, mod_id)
        StreamsEndpoint(api_client).delete(prog_id, stream_id)
        ProgramsEndpoint(api_client).mass_delete([prog_id])
        UsersEndpoint(api_client).delete(user_id)
        logger.info("Очистка завершена")

    # ==================== ТЕСТ 1: Тест ====================

    @allure.title("E2E: Программа → Поток → Модуль → Пользователь → Тест → Назначение в модуль")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("e2e", "api", "smoke")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_e2e_test_to_module(self, api_client, assignments_endpoint):
        from api.endpoints.tests import TestsEndpoint
        from api.endpoints.tincan import TincanEndpoint
        from api.helpers.data_generator import generate_test_payload, generate_question_payload

        ctx = self._setup_program_flow(api_client, assignments_endpoint, "Test")
        tests_ep = TestsEndpoint(api_client)

        with allure.step("6. Создать тест и вопросы"):
            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка: {cover_uuid}")

            test_data = tests_ep.create(generate_test_payload(cover_uuid=cover_uuid))
            test_id = test_data["id"]
            logger.info(f"Тест: {test_id}")

            for i in range(1, 4):
                q = generate_question_payload(order=i, text=f"Вопрос #{i}", question_type="single")
                tests_ep.create_question(test_id, q)
                logger.info(f"Вопрос #{i} добавлен")

        with allure.step("7. Назначить тест в модуль"):
            assignments_endpoint.assign_content_to_module(
                ctx["prog_id"], ctx["stream_id"], ctx["mod_id"], [test_id]
            )
            logger.info("Тест назначен в модуль")

        with allure.step("8. Очистка"):
            self._cleanup(api_client, ctx["prog_id"], ctx["stream_id"], ctx["mod_id"],
                          ctx["user_id"], content_ids=[test_id])

        logger.info("E2E Test → Module завершён!")

    # ==================== ТЕСТ 2: Опрос ====================

    @allure.title("E2E: Программа → Поток → Модуль → Пользователь → Опрос → Назначение в модуль")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("e2e", "api", "smoke")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_e2e_poll_to_module(self, api_client, assignments_endpoint):
        from api.endpoints.polls import PollsEndpoint
        from api.endpoints.tincan import TincanEndpoint
        from api.helpers.data_generator import generate_poll_payload, generate_question_payload

        ctx = self._setup_program_flow(api_client, assignments_endpoint, "Poll")
        polls_ep = PollsEndpoint(api_client)

        with allure.step("6. Создать опрос и вопросы"):
            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка: {cover_uuid}")

            poll_data = polls_ep.create(generate_poll_payload(cover_uuid=cover_uuid))
            poll_id = poll_data["id"]
            logger.info(f"Опрос: {poll_id}")

            for i in range(1, 4):
                q = generate_question_payload(order=i, text=f"Вопрос опроса #{i}", question_type="single")
                polls_ep.create_question(poll_id, q)
                logger.info(f"Вопрос #{i} добавлен")

        with allure.step("7. Назначить опрос в модуль"):
            assignments_endpoint.assign_content_to_module(
                ctx["prog_id"], ctx["stream_id"], ctx["mod_id"], [poll_id]
            )
            logger.info("Опрос назначен в модуль")

        with allure.step("8. Очистка"):
            self._cleanup(api_client, ctx["prog_id"], ctx["stream_id"], ctx["mod_id"],
                          ctx["user_id"], content_ids=[poll_id])

        logger.info("E2E Poll → Module завершён!")

    # ==================== ТЕСТ 3: Тест с прокторингом ====================

    @allure.title("E2E: Программа → Поток → Модуль → Пользователь → Тест+Прокторинг → Назначение в модуль")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("e2e", "api", "smoke")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_e2e_proctoring_to_module(self, api_client, assignments_endpoint):
        from api.endpoints.tests import TestsEndpoint
        from api.endpoints.tincan import TincanEndpoint
        from api.helpers.data_generator import generate_test_payload, generate_question_payload, generate_test_update_proctoring_payload

        ctx = self._setup_program_flow(api_client, assignments_endpoint, "Proctoring")
        tests_ep = TestsEndpoint(api_client)

        with allure.step("6. Создать тест и вопросы"):
            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка: {cover_uuid}")

            test_data = tests_ep.create(generate_test_payload(cover_uuid=cover_uuid))
            test_id = test_data["id"]
            logger.info(f"Тест: {test_id}")

            for i in range(1, 4):
                q = generate_question_payload(order=i, text=f"Вопрос #{i}", question_type="single")
                tests_ep.create_question(test_id, q)
                logger.info(f"Вопрос #{i} добавлен")

        with allure.step("7. Активировать прокторинг"):
            proctoring_payload = generate_test_update_proctoring_payload(
                content_id=test_id,
                name=test_data["name"],
                is_active=True
            )
            tests_ep.update(test_id, proctoring_payload)
            logger.info(f"Прокторинг активирован для теста ID={test_id}")

        with allure.step("8. Назначить тест в модуль"):
            assignments_endpoint.assign_content_to_module(
                ctx["prog_id"], ctx["stream_id"], ctx["mod_id"], [test_id]
            )
            logger.info("Тест с прокторингом назначен в модуль")

        with allure.step("9. Очистка"):
            self._cleanup(api_client, ctx["prog_id"], ctx["stream_id"], ctx["mod_id"],
                          ctx["user_id"], content_ids=[test_id])

        logger.info("E2E Proctoring → Module завершён!")