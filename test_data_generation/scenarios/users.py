"""Сценарий users: N пользователей на каждую роль (--count N на роль), пароль
DEFAULT_PASSWORD, роль назначается через PUT /access-roles (UsersEndpoint.assign_roles),
согласие на ПД и онбординг закрываются через api/helpers/user_prepare_api.py.

role_id взяты из живого списка GET /access-roles на develop (см. api/endpoints/users.py):
1 admin, 2 tenant-admin, 3 manager, 4 teacher, 5 support, 6 content-manager,
7 external-manager, 8 helpdesk. У «слушателя» и «проверяющего» нет отдельной
access-role — слушатель это пользователь без ролей (roles=None в
generate_user_payload), проверяющий назначается по user_id в inspector_ids при
создании практического задания (см. tests/api/users/teacher/test_examine_by_teacher.py),
а не через access-roles.
"""
from api.endpoints.users import UsersEndpoint
from api.helpers.data_generator import generate_user_payload, random_email
from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from utils.logger import logger

from lib import DEFAULT_PASSWORD

DESCRIPTION = "N пользователей на каждую роль (слушатель/преподаватель/проверяющий/менеджер/контент-менеджер/админ тенанта)"

ROLES = {
    "listener": ("Слушатель", None),
    "teacher": ("Преподаватель", 4),
    "inspector": ("Проверяющий", None),
    "manager": ("Менеджер", 3),
    "content_manager": ("Контент-менеджер", 6),
    "tenant_admin": ("Администратор организации", 2),
}


def run(ctx) -> None:
    users_ep = UsersEndpoint(ctx.api_client)
    created = []

    for role_key, (title, role_id) in ROLES.items():
        for i in range(ctx.count):
            # domain без "_" — сервер валидирует email по формату, role_key вида
            # "content_manager" в домене даёт 422 "Электронная почта имеет ошибочный формат"
            email = random_email(domain=f"{role_key.replace('_', '-')}.autotest.com")
            payload = generate_user_payload(email=email, password=DEFAULT_PASSWORD)
            logger.info(f"Пользователь [{title}] {i + 1}/{ctx.count}: {email}")
            user = users_ep.create(payload)
            user_id = user["id"]
            ctx.manifest.record("user", user_id, "users.delete(user_id)")

            if role_id is not None:
                users_ep.assign_roles(user_id, [role_id])
                logger.info(f"   роль назначена: {title} (role_id={role_id})")
            else:
                logger.info(f"   без отдельной access-role ({title})")

            ctx.dry_or(
                f"prepare_user_for_tests_via_api(login={email})",
                None,
                lambda email=email: prepare_user_for_tests_via_api(ctx.env, email, DEFAULT_PASSWORD),
            )
            created.append((title, user_id, email))

    logger.info("Готово.")
    for title, user_id, email in created:
        logger.info(f"  {title:28} {email} / {DEFAULT_PASSWORD} (id={user_id})")
