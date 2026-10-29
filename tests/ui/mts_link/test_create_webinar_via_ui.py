"""UI: Администратор создаёт программу → поток → модуль → мероприятие «МТС Линк»
полностью через UI — включая реальное мероприятие в прод-аккаунте МТС Линк.

ВАЖНО, сознательное отступление от общего правила «сценарий МТС Линк нельзя
автоматизировать» (см. docs/test_cases/mts_link/16_prod_safe_run.md, преамбула: «нет
тестового аккаунта и не будет»): этот тест реально создаёт мероприятие на единственном
прод-аккаунте организации при каждом запуске. Решение владельца 29.10.2026 — тест
существует, но держится за MTS_LINK_READY (см. conftest.py), не входит в обычный полный
прогон/CI сам по себе.

Безопасность прогона (правила того же протокола):
- мероприятие создаётся на ЗАВТРА (не сегодня) — сессия МТС Линк не успевает
  автостартовать за счёт окна `startsAtTimestamp = date_from − 10 мин`, поэтому её
  гарантированно можно удалить в теле же теста чисто, без 403 «stop it before deleting»
  (подтверждено разведкой 29.10.2026 — на вебинаре с датой на завтра
  `DELETE eventsessions` возвращает 204, не 403; см. защиту ниже).
- лектор — Вера (AdminEventMtsPage.select_teacher, VERA_EMAIL_FRAGMENT) — решение
  владельца 29.10.2026, её согласие на роль лектора тестовых вебинаров уже получено;
  ей уходит настоящее email-приглашение (sendEmail=true) при каждом прогоне.
- название с префиксом [ТЕСТ], явный cleanup элемента расписания в теле теста плюс
  регистрация программы на cleanup через register_mts_link_program (на случай, если
  явное удаление не дойдёт из-за фейла до него).
"""
import datetime as dt
import time

import allure
import pytest

from api.helpers.data_generator import unique_suffix
from ui.pages.user_sidebar_page import UserSidebarPage

# Направление/широкая тема — тенантский справочник, не связан с МТС Линк напрямую.
# Значения подтверждены разведкой 29.10.2026 на этом стенде; если дерево справочника
# изменится, тест упадёт явной ошибкой «элемент не найден» на select_direction.
DIRECTION = "Цифровая трансформация"
BROAD_TOPIC = "Мотивационные выступления"

# Синхронизация с МТС Линк занимает ~20-30 с опроса (подтверждено многократно в
# docs/test_cases/mts_link/16_prod_safe_run.md) — даём запас.
SYNC_POLL_TIMEOUT_S = 45
SYNC_POLL_INTERVAL_S = 3


@allure.feature("Интеграция МТС Линк")
@allure.story("Админка: программа → поток → модуль → мероприятие «МТС Линк»")
class TestCreateWebinarViaUi:

    @allure.title("UI: Администратор создаёт мероприятие «МТС Линк» (программа → поток → модуль → вебинар)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.mts_link
    def test_create_mts_webinar_via_ui(
        self,
        admin_page,
        env,
        admin_programs_page,
        admin_event_mts_page,
        schedule_items_endpoint,
        register_mts_link_program,
    ):
        suffix = unique_suffix()
        program_name = f"[ТЕСТ] программа МТС Линк {suffix}"
        stream_name = f"[ТЕСТ] поток МТС Линк {suffix}"
        module_name = f"[ТЕСТ] модуль МТС Линк {suffix}"
        webinar_name = f"[ТЕСТ] вебинар {suffix}"

        today = dt.date.today()
        tomorrow = today + dt.timedelta(days=1)
        date_from = today.strftime("%d.%m.%Y")
        date_to = (today + dt.timedelta(days=30)).strftime("%d.%m.%Y")
        module_date_from = today.strftime("%d.%m.%Y")
        module_date_to = (today + dt.timedelta(days=2)).strftime("%d.%m.%Y")
        webinar_date = tomorrow.strftime("%d.%m.%Y")

        with allure.step("1. Создать программу"):
            admin_programs_page.open_list(env.ui_base_url)
            # storage_state логинит без формы, онбординг-тур ещё не пройден —
            # закрываем его, иначе затемнение перехватывает клики по форме.
            UserSidebarPage(admin_page).dismiss_popups()
            admin_programs_page.create_program(program_name)

        with allure.step("2. Открыть программу и получить её ID"):
            program_id = admin_programs_page.open_program(program_name)
            register_mts_link_program(program_id)

        with allure.step("3. Создать поток со всеми обязательными селектами и новым полем порога МТС Линк"):
            admin_programs_page.open_create_stream_form()
            stream_id = admin_programs_page.create_stream(
                name=stream_name,
                place="Москва",
                date_from=date_from,
                date_to=date_to,
                mts_webinar_threshold="70",
            )

        with allure.step("4. Создать модуль"):
            admin_programs_page.open_schedule_tab()
            module_id = admin_programs_page.create_module(
                name=module_name,
                place="Москва",
                start_date=module_date_from,
                finish_date=module_date_to,
            )

        with allure.step("5. Задать регион модуля (нужен для очных мероприятий)"):
            admin_programs_page.set_module_region_and_save("Москва")

        with allure.step("6. Переключить модуль на «О» (очно) и создать мероприятие «МТС Линк»"):
            admin_event_mts_page.switch_to_offline_tab()
            schedule_item_id = admin_event_mts_page.create_mts_webinar(
                name=webinar_name,
                date=webinar_date,
                time_from="11:00",
                time_to="11:10",
                location="Москва",
                direction=DIRECTION,
                broad_topic=BROAD_TOPIC,
            )

        try:
            with allure.step("7. Дождаться синхронизации с МТС Линк (webinar_status: synced)"):
                mts_link_data = self._wait_for_sync(
                    schedule_items_endpoint, program_id, stream_id, module_id, schedule_item_id
                )
                allure.attach(
                    str(mts_link_data), name="mts_link_block", attachment_type=allure.attachment_type.TEXT
                )
                assert mts_link_data is not None, "Блок mts_link не появился в элементе расписания"
                assert mts_link_data.get("webinar_status") == "synced", (
                    f"Вебинар не синхронизировался с МТС Линк: {mts_link_data}"
                )
        finally:
            with allure.step("8. Удалить мероприятие (вебинар на завтра, ещё не стартовал — должно пройти чисто)"):
                deleted = schedule_items_endpoint.delete(program_id, stream_id, module_id, schedule_item_id)
                assert deleted, "Не удалось удалить элемент расписания с мероприятием «МТС Линк»"

    @staticmethod
    def _wait_for_sync(schedule_items_endpoint, program_id: int, stream_id: int, module_id: int, item_id: int):
        deadline = time.monotonic() + SYNC_POLL_TIMEOUT_S
        mts_link_data = None
        while time.monotonic() < deadline:
            item = schedule_items_endpoint.get(program_id, stream_id, module_id, item_id)
            mts_link_data = item["attributes"].get("mts_link")
            if mts_link_data and mts_link_data.get("webinar_status") in ("synced", "error"):
                return mts_link_data
            time.sleep(SYNC_POLL_INTERVAL_S)
        return mts_link_data
