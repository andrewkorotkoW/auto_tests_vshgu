"""Админка: создание группы потока вручную, добавление ПЗ в группу,
добавление двух слушателей в группу.

Перенос сценария test_14_create_group_for_stream.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2). Поток, модуль, ПЗ и слушатели подняты
через наши API-фикстуры (created_stream/created_user) и назначены на поток через
assignments_endpoint; предмет теста — сама форма создания группы и её наполнения
в админке (ui/pages/admin_stream_groups_page.py).
"""
from pathlib import Path

import allure
import pytest
from playwright.sync_api import expect

from ui.pages.admin_stream_groups_page import AdminStreamGroupsPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[4] / "test_data"


@allure.feature("Группы потока UI")
@allure.story("Админка: создание группы и её наполнение")
class TestCreateGroupForStream:

    @allure.title("UI: Администратор создаёт группу потока, добавляет в неё ПЗ и двух слушателей")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.groups
    def test_create_group_for_stream(
        self, admin_page, env, api_client, tincan_endpoint, assignments_endpoint,
        created_stream, created_module, created_homework, created_user, register_practical_homework,
    ):
        homework_id = None

        try:
            with allure.step("1. Подготовить поток, модуль, ПЗ и двух слушателей через API"):
                stream = created_stream()
                module = created_module(program_id=stream["program_id"], stream_id=stream["id"])

                cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
                archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
                sub_file_uuid = tincan_endpoint.upload_sub_file(str(TEST_DATA_DIR / "practical_task_additional_document.xlsx"))

                homework = created_homework(
                    cover_uuid=cover_uuid,
                    archive_uuid=archive_uuid,
                    sub_files_uuids=[sub_file_uuid],
                )
                homework_id = homework["id"]
                register_practical_homework(homework_id)

                assigned_ok = assignments_endpoint.assign_content_to_module(
                    stream["program_id"], stream["id"], module["id"], [homework_id]
                )
                assert assigned_ok, "Не удалось добавить ПЗ в модуль"

                user1 = created_user()
                user2 = created_user()
                assignments_endpoint.assign(stream["program_id"], stream["id"], [user1["id"], user2["id"]])

                group_name = f"autotest_group_{stream['id']}"
                logger.info(f"Поток: {stream['id']}, ПЗ: {homework['name_client']}, группа: {group_name}")

            with allure.step("2. Открыть поток в админке и вкладку «Группы»"):
                admin_page.goto(f"{env.ui_base_url}/admin/programs/{stream['program_id']}/streams/{stream['id']}")
                # storage_state логинит без формы, поэтому онбординг-тур ещё не пройден —
                # закрываем его, иначе затемнение перехватывает клики по вкладкам
                UserSidebarPage(admin_page).dismiss_popups()
                groups_page = AdminStreamGroupsPage(admin_page)
                groups_page.open_groups_tab()

            with allure.step(f"3. Создать группу '{group_name}' вручную"):
                groups_page.create_group_manually(group_name)

            with allure.step("4. Открыть созданную группу"):
                group_id = groups_page.open_group(group_name)
                logger.info(f"Группа создана: id={group_id}")

            with allure.step(f"5. Добавить ПЗ '{homework['name']}' в группу"):
                groups_page.add_practical_task(homework["name"])

            with allure.step("6. Перейти на вкладку «Слушатели» группы"):
                groups_page.open_listeners_tab()

            with allure.step("7. Добавить двух слушателей в группу"):
                groups_page.add_listener(user1["email"])
                groups_page.add_listener(user2["email"])

            with allure.step("8. Проверить, что оба слушателя добавлены в группу"):
                expect(groups_page.group_listener_row(user1["email"])).to_be_visible(timeout=15000)
                expect(groups_page.group_listener_row(user2["email"])).to_be_visible(timeout=15000)
        finally:
            pass
