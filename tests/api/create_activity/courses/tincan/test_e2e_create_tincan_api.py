import allure
import pytest
from utils.logger import logger


@allure.feature("Tincan API")
@allure.story("E2E Tincan Full Flow")
class TestE2ETincan:

    @allure.title("E2E: Программа → Поток → Модуль → Пользователь → Курс Tincan → Назначение")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("e2e", "api", "smoke")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_e2e_tincan_full_flow(self, api_client, assignments_endpoint):
        from api.endpoints.tincan import TincanEndpoint

        session = api_client.session
        base = api_client.base_url

        def post(path, json_data):
            r = session.post(f"{base}{path}", json=json_data)
            assert r.status_code in (200, 201), f"POST {path} failed: {r.status_code} {r.text}"
            return r.json()

        tincan_ep = TincanEndpoint(api_client)

        with allure.step("1. Создать программу"):
            from api.helpers.data_generator import generate_program_payload
            r = post("/programs", generate_program_payload(name="E2E_Tincan"))
            prog_id = r["data"]["id"]

        with allure.step("2. Создать поток"):
            from api.helpers.data_generator import generate_stream_payload
            r = post(f"/programs/{prog_id}/streams", generate_stream_payload())
            stream_id = r["data"]["id"]

        with allure.step("3. Создать модуль"):
            from api.helpers.data_generator import generate_module_payload
            r = post(f"/programs/{prog_id}/streams/{stream_id}/modules", generate_module_payload())
            mod_id = r["data"]["id"]

        with allure.step("4. Создать пользователя"):
            from api.helpers.data_generator import generate_user_payload
            r = post("/users", generate_user_payload())
            user_id = r["data"]["id"]

        with allure.step("5. Назначить пользователя на поток"):
            assignments_endpoint.assign(prog_id, stream_id, [user_id])

        with allure.step("6. Загрузить файлы и создать курс"):
            cover = tincan_ep.upload_cover()
            archive = tincan_ep.upload_archive()
            sub = tincan_ep.upload_sub_file()
            from api.helpers.data_generator import generate_tincan_payload
            r = post("/content", generate_tincan_payload(
                archive_uuid=archive, cover_uuid=cover, sub_files_uuids=[sub]))
            course_id = r["data"]["id"]

        with allure.step("7. Назначить курс в модуль"):
            tincan_ep.assign_to_module(prog_id, stream_id, mod_id, [course_id])

        with allure.step("8. Удалить курс"):
            tincan_ep.mass_delete([course_id])

        with allure.step("9. Очистка"):
            from api.endpoints.programs import ProgramsEndpoint
            from api.endpoints.streams import StreamsEndpoint
            from api.endpoints.modules import ModulesEndpoint
            from api.endpoints.users import UsersEndpoint

            ModulesEndpoint(api_client).delete(prog_id, stream_id, mod_id)
            StreamsEndpoint(api_client).delete(prog_id, stream_id)
            ProgramsEndpoint(api_client).mass_delete([prog_id])
            UsersEndpoint(api_client).delete(user_id)
            logger.info("Очистка завершена")

        logger.info("E2E Tincan завершён!")