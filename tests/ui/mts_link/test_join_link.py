"""UI: слушатель заходит в «Моё обучение» и переходит по ссылке на вебинар «МТС Линк» —
ссылка реально ведёт в чужую систему (my.mts-link.ru), а не на заглушку/битую ссылку.

UI-аналог API-теста test_create.py::TestCreate::test_join_link_leads_to_real_mts_link_system
(та же проверка, но кликом в реальном браузере, как это сделал бы слушатель). Подтверждено
живьём 12.11.2026 на mts-link-release-main: карточка мероприятия в расписании модуля
слушателя содержит настоящий <a href="https://my.mts-link.ru/..." target="_blank">, обычный
клик (без force) открывает новую вкладку — см. ui/pages/education_schedule_page.py."""
import time

import allure
import pytest

from api.helpers.data_generator import MTS_LINK_SAFE_TEACHER_ID, generate_schedule_item_payload, \
    mts_link_safe_schedule_item_kwargs
from ui.pages.education_schedule_page import EducationSchedulePage
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Интеграция МТС Линк")
@allure.story("Слушатель переходит по ссылке на вебинар")
@pytest.mark.ui
@pytest.mark.mts_link
class TestJoinLinkUi:
    @allure.title("UI: ссылка на вебинар в «Моём обучении» реально ведёт в МТС Линк")
    @pytest.mark.smoke
    def test_listener_can_join_mts_link_webinar_via_link(
        self,
        page,
        mts_link_endpoint,
        created_program,
        created_stream,
        created_module,
        schedule_items_endpoint,
        assignments_endpoint,
        prepared_user,
        register_mts_link_program,
    ):
        with allure.step("1. Создать программу → поток → модуль"):
            program = created_program(name="[ТЕСТ] UI join link")
            register_mts_link_program(program["id"])
            stream = created_stream(program_id=program["id"])
            module = created_module(program_id=program["id"], stream_id=stream["id"])

        with allure.step("2. Создать и подготовить слушателя (prepared_user — без анкеты/тура при входе)"):
            user = prepared_user()
            assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])

        with allure.step("3. Создать мероприятие «МТС Линк» и зарегистрировать слушателя"):
            kwargs = mts_link_safe_schedule_item_kwargs(
                # Название НЕ должно совпадать с названием программы: оно тоже остаётся
                # на экране (хлебные крошки) после open_program, и text-локатор события
                # резолвится в крошку, а не в карточку мероприятия (live run #131,
                # 12.11.2026 — Locator.click timeout, резолвился в li.v-breadcrumbs-item).
                name="[ТЕСТ] вебинар UI join link", teacher_ids=[MTS_LINK_SAFE_TEACHER_ID]
            )
            payload = generate_schedule_item_payload(**kwargs)
            item = schedule_items_endpoint.create(program["id"], stream["id"], module["id"], payload)
            schedule_items_endpoint.register_user(item["id"], user["id"])
            ref = {
                "program_id": program["id"], "stream_id": stream["id"],
                "module_id": module["id"], "id": item["id"],
            }
            mts_link_endpoint.wait_for_part_status(ref, "creation")

        try:
            with allure.step("4. Логин слушателем, дойти до карточки мероприятия"):
                login_page = LoginPage(page)
                login_page.login(user["email"], user["password"])
                UserSidebarPage(page).dismiss_popups()

                schedule_page = EducationSchedulePage(page)
                schedule_page.open_program(program["name"])
                schedule_page.open_schedule_item(item["attributes"]["name"])

            with allure.step("5. Кликнуть по ссылке на вебинар и проверить, куда она ведёт"):
                new_page = schedule_page.click_join_link_and_get_new_page()
                new_page.wait_for_load_state("domcontentloaded", timeout=15000)
                assert "mts-link.ru" in new_page.url, (
                    f"Переход по ссылке увёл не в МТС Линк: {new_page.url}"
                )
                new_page.close()
        finally:
            with allure.step("6. Удалить мероприятие (grace-пауза перед сносом программы/потока/модуля)"):
                schedule_items_endpoint.delete(program["id"], stream["id"], module["id"], item["id"])
                time.sleep(60)
