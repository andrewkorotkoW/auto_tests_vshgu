import allure
import pytest

from utils.logger import logger


@pytest.fixture
def register_practical_homework(homework_endpoint):
    """Регистрирует ПЗ, созданные через API для UI-сценария, для cleanup."""
    homework_ids = []

    def _register(homework_id: int) -> None:
        homework_ids.append(homework_id)

    yield _register

    if homework_ids:
        try:
            homework_endpoint.mass_delete(homework_ids)
        except Exception as exc:  # noqa: BLE001 - cleanup не должен скрывать исходный фейл
            allure.attach(
                str(exc),
                name="practical_homework_cleanup_error",
                attachment_type=allure.attachment_type.TEXT,
            )
            logger.warning(f"Failed to delete UI-scenario homeworks {homework_ids}: {exc}")


@pytest.fixture
def register_practical_program(programs_endpoint):
    """Регистрирует программы, созданные через UI, для best-effort cleanup."""
    program_ids = []

    def _register(program_id: int) -> None:
        program_ids.append(program_id)

    yield _register

    if program_ids:
        try:
            programs_endpoint.mass_delete(program_ids)
        except Exception as exc:  # noqa: BLE001 - cleanup не должен скрывать исходный фейл
            allure.attach(
                str(exc),
                name="practical_program_cleanup_error",
                attachment_type=allure.attachment_type.TEXT,
            )
            logger.warning(f"Failed to delete UI-created programs {program_ids}: {exc}")
