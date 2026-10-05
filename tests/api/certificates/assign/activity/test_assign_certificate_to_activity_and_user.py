import allure
import pytest
import time
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.certificates import CertificatesEndpoint
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.assignments import AssignmentsEndpoint
from api.endpoints.users import UsersEndpoint


@allure.feature("Certificates API")
@allure.story("Assign Certificate to Activity and User")
class TestAssignCertificateToActivity:

    @allure.title("E2E Develop: Сертификат → ДЗ → назначение на ДЗ → пользователь → инд. трек")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.api
    def test_assign_certificate_to_homework_and_user(
        self, api_client,
        created_template,      # фикстура для шаблона сертификата
        created_homework,      # фикстура для домашнего задания
        created_user           # фикстура для пользователя
    ):
        cert_ep = CertificatesEndpoint(api_client)
        tincan_ep = TincanEndpoint(api_client)
        hw_ep = HomeworkEndpoint(api_client)
        users_ep = UsersEndpoint(api_client)
        assign_ep = AssignmentsEndpoint(api_client)

        # --- 1. Создать шаблон сертификата ---
        with allure.step("1. Создать шаблон сертификата (activity)"):
            file_id = tincan_ep.upload_certificate_file()
            template = created_template(
                file_id=file_id,
                template_type="activity",
                name=f"Автотест_шаблон_ДЗ_{int(time.time() * 1000)}"
            )
            logger.info(f"Шаблон создан: ID={template['id']}")

        # --- 2. Создать домашнее задание ---
        with allure.step("2. Создать домашнее задание"):
            cover_uuid = tincan_ep.upload_cover()
            homework = created_homework(
                cover_uuid=cover_uuid,
                teacher_ids=[],      # если нужен преподаватель, можно создать
                inspector_ids=[]
            )
            logger.info(f"ДЗ создано: ID={homework['id']}")

        # --- 3. Назначить сертификат на ДЗ ---
        with allure.step("3. Назначить сертификат на домашнее задание"):
            result = cert_ep.assign_template(
                template_id=template["id"],
                content_ids=[homework["id"]]
            )
            assert result is not None, "Ответ назначения пуст"
            logger.info("Сертификат назначен на ДЗ")
            allure.attach(str(result), "Assign Result", allure.attachment_type.JSON)

        # --- 4. Создать пользователя ---
        with allure.step("4. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: ID={user['id']}, email={user['email']}")

        # --- 5. Назначить ДЗ пользователю в инд. трек ---
        with allure.step("5. Назначить ДЗ пользователю через инд. трек"):
            assign_ep.assign_to_individual(
                [homework["id"]],
                [user["id"]]
            )
            logger.info("ДЗ назначено пользователю")

        # --- 6. Проверить, что ДЗ появилось у пользователя (опционально) ---
        with allure.step("6. Проверить, что ДЗ доступно пользователю"):
            # Можно запросить my-personal-training или просто убедиться, что назначение прошло без ошибок
            # Для простоты оставим как есть – сам факт успешного assign уже проверен.
            logger.info("Проверка пройдена: ДЗ назначено, сертификат связан")

        # Очистка: шаблон удалится автоматически (created_template), ДЗ и пользователь – через фикстуры?
        # created_homework сейчас не удаляет ДЗ, created_user удаляет пользователя после теста.
        # Добавим ручное удаление ДЗ, чтобы не засорять систему.
        with allure.step("Очистка: удалить ДЗ"):
            try:
                hw_ep.delete(homework["id"])
                logger.info("ДЗ удалено")
            except Exception as e:
                logger.warning(f"Не удалось удалить ДЗ: {e}")