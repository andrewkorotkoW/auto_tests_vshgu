import pytest

from utils.logger import logger


@pytest.fixture
def individual_lpd(created_user, created_lpd, lpd_endpoint):
    """Создаёт пользователя + LPD и назначает его на индивидуальный трек.
    После теста снимает назначение (LPD и пользователь удаляются своими фикстурами)."""
    created = []

    def _setup(passing_type: str):
        user = created_user()
        lpd = created_lpd(passing_type=passing_type)
        lpd_endpoint.assign_activities([lpd["id"]], [user["id"]])
        created.append((user, lpd))
        return user, lpd

    yield _setup

    for user, lpd in created:
        try:
            lpd_endpoint.detach_activities([lpd["id"]], [user["id"]])
        except Exception as e:
            logger.warning(f"Failed to detach LPD {lpd['id']} from user {user['id']}: {e}")


@pytest.fixture
def program_lpd(created_program, created_stream, created_module, created_user, created_lpd,
                 assignments_endpoint, lpd_endpoint):
    """Создаёт программу → поток → модуль + пользователя, назначенного на поток, + LPD,
    назначенный в модуль и активированный на пользователя. После теста снимает назначение
    (программа/LPD/пользователь удаляются своими фикстурами)."""
    created = []

    def _setup(passing_type: str):
        program = created_program()
        stream = created_stream(program_id=program["id"])
        module = created_module(program_id=program["id"], stream_id=stream["id"])
        user = created_user()
        assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])
        lpd = created_lpd(passing_type=passing_type)
        lpd_endpoint.assign_to_module(program["id"], stream["id"], module["id"], [lpd["id"]])
        lpd_endpoint.assign_users_with_retry(module["id"], lpd["id"], stream["id"], [user["id"]])
        created.append((user, lpd, stream, module))
        return user, lpd, program, stream, module

    yield _setup

    for user, lpd, stream, module in created:
        try:
            lpd_endpoint.detach_users(module["id"], lpd["id"], stream["id"], [user["id"]])
        except Exception as e:
            logger.warning(f"Failed to detach LPD {lpd['id']} from user {user['id']}: {e}")
