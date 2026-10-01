"""Админка → «Конструктор тестов и опросов» (создание теста/опроса/АОС, вопросы,
доп. вопросы по теме, вопросы из банка, настройки последовательности, статистика).

Перенос src/ui/pages/test_constructor_admin_page.py коллеги (ветка
origin/feature/test-constructor-autotests, ConstructorAdminPage) в наш Page Object:
без allure.step внутри методов (в этом репозитории allure.step идёт в тестах, не в
Page Object — см. ui/pages/admin_knowledge_base_page.py/admin_programs_page.py), без
ручного логина/закрытия плашки «Технические работы» через LoginPage (у нас для этого
уже есть готовая авторизованная страница — фикстура admin_page в корневом conftest.py
и ui.pages.admin_page.AdminPage.close_tech_banner). ui_base_url передаётся в методы
навигации явно, как в остальных admin-страницах, вместо глобального ADMIN_BASE_URL.

Поиск теста/опроса по имени в таблице конструктора не работает — известный баг
стенда (см. задачу), поэтому open_constructor_by_id ходит по ID напрямую, а не через
search_by_name + клик по строке.
"""
import json
import re
from typing import List
from urllib.parse import quote

from playwright.sync_api import Page, Locator, expect
from ui.pages.admin_page import AdminPage
from ui.pages.base_page import BasePage


class ConstructorAdminPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    # ── Навигация ────────────────────────────────────────────────────────

    def open_constructor_table(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}/admin/testing/constructor-table")
        expect(self.page).to_have_url(re.compile(r".*/admin/testing/constructor-table.*"), timeout=30000)
        AdminPage(self.page).close_tech_banner()

    def search_by_name(self, constructor_name: str) -> None:
        """Не использовать для поиска нужного теста/опроса в фикстурах — поиск по имени
        в таблице конструктора не работает (известный баг стенда). Пригодно только для
        UI-проверки самого факта отображения строки после ручного поиска."""
        search_input = self.page.locator('[data-qa="km-search"]')
        expect(search_input).to_be_visible(timeout=15000)
        search_input.fill(constructor_name)
        self.page.wait_for_load_state("networkidle", timeout=30000)

    def open_create_page(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}/admin/testing/constructor/create")
        expect(self.page).to_have_url(re.compile(r".*/admin/testing/constructor/create.*"), timeout=30000)
        expect(self.page.get_by_text("Создание теста/опроса", exact=True)).to_be_visible(timeout=30000)

    def open_feedback_create_page(
        self,
        ui_base_url: str,
        program_id: int,
        stream_id: int,
        schedule_item_ids: List[int],
        is_last_day: bool,
    ) -> None:
        """Открыть форму создания АОС по мероприятиям потока (testPreset в query)."""
        test_preset = quote(
            json.dumps(
                {"materialIds": schedule_item_ids, "materialsType": "feedback", "isLastDay": is_last_day},
                ensure_ascii=False,
            )
        )
        self.page.goto(
            f"{ui_base_url.rstrip('/')}/admin/testing/constructor/create"
            f"?program_id={program_id}&stream_id={stream_id}&testPreset={test_preset}"
        )
        expect(self.page).to_have_url(re.compile(r".*/admin/testing/constructor/create.*"), timeout=30000)
        expect(self.page.get_by_text("Создание теста/опроса", exact=True)).to_be_visible(timeout=30000)
        expect(self.page.get_by_role("button", name=re.compile("Анкета обратной связи"))).to_be_visible(timeout=30000)

    def open_stream_feedback_tab(self, ui_base_url: str, program_id: int, stream_id: int) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}/admin/programs/{program_id}/streams/{stream_id}?i=6")
        expect(self.page).to_have_url(re.compile(r".*/admin/programs/\d+/streams/\d+\?i=6.*"), timeout=30000)
        expect(self.page.get_by_text("Анкета обратной связи", exact=True)).to_be_visible(timeout=30000)
        expect(self.page.get_by_role("button", name="Создать")).to_be_visible(timeout=30000)

    def start_feedback_creation_from_stream_tab(self) -> None:
        self.page.get_by_role("button", name="Создать").click()
        expect(self.page.get_by_text("Выберите модуль и очные мероприятия", exact=True)).to_be_visible(timeout=30000)
        self.page.get_by_role("button", name="Выбрать все в модуле").click()
        self.page.get_by_role("button", name="Подтвердить выбор").click()

        confirm = self.page.locator(".confirm", has_text="Это последний день?")
        if confirm.is_visible(timeout=3000):
            confirm.locator(".confirm__btn-ok").click()

        expect(self.page).to_have_url(re.compile(r".*/admin/testing/constructor/create.*"), timeout=30000)
        expect(self.page.get_by_text("Создание теста/опроса", exact=True)).to_be_visible(timeout=30000)
        expect(self.page.get_by_role("button", name=re.compile("Анкета обратной связи"))).to_be_visible(timeout=30000)

    # ── Первый шаг создания (тип/название/тема) ─────────────────────────

    def create_test_on_first_step(self, admin_name: str, external_name: str, topic: str) -> None:
        self.page.get_by_role("button", name=re.compile("Тип сущности")).click()
        self.page.get_by_text("Тест", exact=True).click()
        self.page.get_by_label("Название в админке").fill(admin_name)
        self.page.get_by_label("Название на внешке").fill(external_name)
        self.page.get_by_label("Тема").fill(topic)
        self.page.get_by_role("button", name="Создать").click()

        expect(self.page).to_have_url(re.compile(r".*/admin/testing/constructor/edit/\d+/second.*"), timeout=30000)
        expect(self.page.get_by_text("Используйте конструктор", exact=False)).to_be_visible(timeout=30000)

    def create_poll_on_first_step(self, admin_name: str, external_name: str, topic: str) -> None:
        self.page.get_by_role("button", name=re.compile("Тип сущности")).click()
        self.page.get_by_text("Опрос", exact=True).click()
        self.page.get_by_label("Название в админке").fill(admin_name)
        self.page.get_by_label("Название на внешке").fill(external_name)
        self.page.get_by_label("Тема").fill(topic)
        self.page.get_by_role("button", name="Создать").click()

        expect(self.page).to_have_url(re.compile(r".*/admin/testing/constructor/edit/\d+/second.*"), timeout=30000)
        expect(self.page.get_by_text("Опрос", exact=True)).to_be_visible(timeout=30000)

    def create_feedback_on_first_step(self, admin_name: str, external_name: str) -> None:
        self.page.get_by_label("Название в админке").fill(admin_name)
        self.page.get_by_label("Название на внешке").fill(external_name)
        self.page.get_by_role("button", name="Создать").click()

        expect(self.page).to_have_url(re.compile(r".*/admin/testing/constructor/edit/\d+/second.*"), timeout=30000)
        expect(self.page.get_by_text("Последовательность вопросов по ответам", exact=True)).to_be_visible(timeout=30000)

    def get_current_constructor_id(self) -> int:
        match = re.search(r"/admin/testing/constructor/edit/(\d+)/", self.page.url)
        if not match:
            raise AssertionError(f"Не удалось получить id конструктора из текущего URL.\nURL: {self.page.url}")
        return int(match.group(1))

    def open_constructor_by_id(self, ui_base_url: str, content_id: int) -> None:
        self.page.goto("about:blank")
        self.page.goto(f"{ui_base_url.rstrip('/')}/admin/testing/constructor/edit/{content_id}/second")
        self.page.wait_for_load_state("networkidle", timeout=30000)
        expect(self.page).to_have_url(
            re.compile(rf".*/admin/testing/constructor/edit/{content_id}/second.*"), timeout=30000
        )
        expect(self.page.get_by_text("Используйте конструктор", exact=False)).to_be_visible(timeout=30000)

    # ── Статистика ───────────────────────────────────────────────────────

    def open_statistics_for_individual_test(self, ui_base_url: str, content_id: int, constructor_name: str) -> None:
        filter_query = quote(
            json.dumps({"test": {"id": content_id, "name": constructor_name}, "individual": True}, ensure_ascii=False)
        )
        self.page.goto(
            f"{ui_base_url.rstrip('/')}/admin/testing/statistics?filter={filter_query}",
            wait_until="domcontentloaded",
        )
        expect(self.page).to_have_url(re.compile(r".*/admin/testing/statistics.*"), timeout=30000)
        expect(self.page.get_by_text("ФИО пользователя", exact=True)).to_be_visible(timeout=30000)

    def search_statistics_by_user_name(self, full_name: str) -> None:
        """Фильтрация строк по ФИО на этой странице — клиентская (fill не порождает
        новый `GET .../statistic` с именем в параметрах — подтверждено на develop),
        поэтому `wait_for_load_state("networkidle")` здесь не ждёт результат поиска,
        а виснет на 30с из-за открытого в админке websocket (тот же случай, что и в
        AdminDashboardPage.read_map_totals). Последующий expect() в
        assert_user_test_progress_visible сам дожидается перерисовки таблицы."""
        search_input = self.page.locator('[data-qa="km-search"]')
        expect(search_input).to_be_visible(timeout=30000)
        search_input.fill(full_name)

    def assert_user_test_progress_visible(self, full_name: str, progress: int) -> None:
        row = self.page.locator("tr", has_text=full_name)
        expect(row).to_be_visible(timeout=30000)
        expect(row).to_contain_text("Индивидуальный трек")
        expect(row.locator("td").nth(5)).to_have_text(str(progress), timeout=30000)

    # ── Таблица конструктора / потока ───────────────────────────────────

    def constructor_row(self, constructor_name: str) -> Locator:
        return self.page.locator("tr", has_text=constructor_name)

    def assert_constructor_row_visible(self, constructor_name: str, constructor_type: str, topic: str) -> None:
        row = self.constructor_row(constructor_name)
        expect(row).to_be_visible(timeout=30000)
        expect(row).to_contain_text(constructor_type)
        expect(row).to_contain_text(topic)

    def assert_constructor_row_visible_by_name(self, constructor_name: str) -> None:
        expect(self.constructor_row(constructor_name)).to_be_visible(timeout=30000)

    def stream_feedback_row(self, feedback_name: str) -> Locator:
        return self.page.locator("tr", has_text=feedback_name)

    def assert_stream_feedback_row_visible(self, feedback_name: str) -> None:
        row = self.stream_feedback_row(feedback_name)
        expect(row).to_be_visible(timeout=30000)
        expect(row).to_contain_text(feedback_name)

    def activate_stream_feedback(self, feedback_name: str) -> None:
        row = self.stream_feedback_row(feedback_name)
        expect(row).to_be_visible(timeout=30000)
        active_switch = row.locator(".v-input--switch input[type='checkbox']").first
        active_switch.check(force=True, timeout=30000)
        expect(active_switch).to_be_checked(timeout=30000)

    def assert_stream_feedback_activation_blocked(self, feedback_name: str) -> None:
        """Проверить запрет активации невалидной АОС (недостижимая группа в
        последовательности) — переключатель остаётся выключенным, а бэкенд
        отвечает статусом «Данная версия АОС недоступна для активации»."""
        row = self.stream_feedback_row(feedback_name)
        expect(row).to_be_visible(timeout=30000)
        active_switch = row.locator(".v-input--switch input[type='checkbox']").first
        expect(active_switch).not_to_be_checked(timeout=30000)

        with self.page.expect_response(
            lambda response: response.request.method == "POST"
            and "feedback" in response.url
            and "change-active" in response.url,
            timeout=30000,
        ) as response_info:
            active_switch.click(force=True, timeout=30000)

        response = response_info.value
        response_body = response.text()
        expected_status = "Данная версия АОС недоступна для активации"

        if response.ok:
            raise AssertionError(
                f"Невалидная АОС активировалась в потоке.\nSTATUS: {response.status}\nBODY:\n{response_body[:1000]}"
            )

        response_status = (response.json().get("data") or {}).get("status")
        if response_status != expected_status:
            raise AssertionError(
                f"Backend вернул неожиданную ошибку активации АОС.\nSTATUS: {response.status}\nBODY:\n{response_body[:1000]}"
            )

        expect(active_switch).not_to_be_checked(timeout=30000)

    # ── Проверки открытого конструктора ─────────────────────────────────

    def assert_created_test_constructor_opened(self) -> None:
        expect(self.page.get_by_text("Используйте конструктор", exact=False)).to_be_visible(timeout=30000)
        expect(
            self.page.get_by_text("После неправильного ответа подбирать вопросы по той же теме", exact=True)
        ).to_be_visible(timeout=30000)
        expect(self.page.get_by_text("Вопрос 1", exact=True)).to_be_visible(timeout=30000)

    def assert_created_poll_constructor_opened(self) -> None:
        expect(self.page.get_by_text("Опрос", exact=True)).to_be_visible(timeout=30000)
        expect(self.page.get_by_text("Используйте конструктор", exact=False)).to_be_visible(timeout=30000)
        expect(self.page.get_by_text("Последовательность вопросов по ответам", exact=True)).to_be_visible(timeout=30000)
        expect(
            self.page.get_by_text("После неправильного ответа подбирать вопросы по той же теме", exact=True)
        ).not_to_be_visible(timeout=10000)

    # ── Последовательность вопросов по ответам ──────────────────────────

    def sequence_questions_switch(self) -> Locator:
        sequence_setting = self.page.locator(".constructor-settings-item__wrapper", has_text="Последовательность вопросов по ответам")
        return sequence_setting.locator('input[type="checkbox"]').first

    def enable_sequence_questions(self) -> None:
        switch = self.sequence_questions_switch()
        expect(switch).to_be_visible(timeout=30000)
        switch.check(force=True, timeout=30000)
        expect(switch).to_be_checked(timeout=30000)

    def assert_sequence_questions_enabled(self) -> None:
        expect(self.sequence_questions_switch()).to_be_checked(timeout=30000)

    def assert_feedback_group_has_no_relations(self, group_title: str) -> None:
        """Проверить недостижимую группу АОС (нет входящих связей в последовательности)."""
        group = self.page.locator(".constructor-groups-item", has_text=group_title).first
        expect(group).to_be_visible(timeout=30000)
        expect(group).to_have_class(re.compile(r".*constructor-groups-item_invalid.*"), timeout=30000)
        expect(group.get_by_text("Нет связей", exact=True)).to_be_visible(timeout=30000)

    def add_single_question_to_group(
        self,
        group_index: int,
        question_text: str,
        answer_texts: List[str],
        target_titles: List[str],
    ) -> None:
        """Добавить в UI single-вопрос в группу АОС/опроса и настроить переходы по ответам
        на target_titles (по одному на каждый ответ, в том же порядке)."""
        group = self.page.locator(".constructor-groups-item").nth(group_index)
        expect(group).to_be_visible(timeout=30000)
        group.scroll_into_view_if_needed()
        group.locator(".constructor-groups-item-header__btn").click()
        active_menu = self.page.locator(".v-menu__content.menuable__content__active").last
        expect(active_menu).to_be_visible(timeout=30000)
        active_menu.locator(".v-list-item", has_text="Добавить вопрос").click()

        modal = self.page.get_by_role("dialog").filter(has_text="Добавить вопрос").last
        expect(modal).to_be_visible(timeout=30000)
        modal.get_by_label("Тип вопроса").click()
        question_type_menu = self.page.locator(".v-menu__content.menuable__content__active").last
        expect(question_type_menu).to_be_visible(timeout=30000)
        question_type_menu.get_by_text("Один верный ответ", exact=True).click()
        modal.get_by_role("button", name="Добавить вопрос").click()

        question = group.locator(".constructor-questions-item").last
        expect(question.get_by_text("Вопрос «Один верный ответ»", exact=False)).to_be_visible(timeout=30000)
        question.locator('textarea[placeholder="Вопрос"]').fill(question_text)

        while question.locator('textarea[placeholder="Ответ"]').count() < len(answer_texts):
            question.get_by_role("button", name="Добавить вариант ответа").click()

        for index, answer_text in enumerate(answer_texts):
            question.locator('textarea[placeholder="Ответ"]').nth(index).fill(answer_text)

        for index, target_title in enumerate(target_titles):
            if index == len(target_titles) - 1:
                with self.page.expect_response(
                    lambda response: "/api/v1/tests/questions/store" in response.url
                    and response.request.method == "PUT"
                    and response.ok,
                    timeout=30000,
                ):
                    self._select_question_sequence_target(question, index, target_title)
            else:
                self._select_question_sequence_target(question, index, target_title)

        expect(question).to_contain_text("Переход к группе", timeout=30000)
        for target_title in target_titles:
            expect(question).to_contain_text(target_title, timeout=30000)

    def _select_question_sequence_target(self, question: Locator, index: int, target_title: str) -> None:
        relation = question.locator(".answer-relation__autocomplete").nth(index)
        relation.click()
        active_menu = self.page.locator(".v-menu__content.menuable__content__active").last
        expect(active_menu).to_be_visible(timeout=30000)
        active_menu.get_by_text(target_title, exact=False).click()

    def question_by_text(self, question_text: str) -> Locator:
        question_textareas = self.page.locator('textarea[placeholder="Вопрос"]')
        for index in range(question_textareas.count()):
            question_textarea = question_textareas.nth(index)
            if question_textarea.input_value(timeout=5000) == question_text:
                return question_textarea.locator(
                    "xpath=ancestor::div[contains(@class, 'constructor-questions-item')]"
                ).first
        raise AssertionError(f"В конструкторе не найден вопрос: {question_text}")

    def assert_feedback_sequence_settings_visible(
        self,
        first_question_text: str,
        second_question_text: str,
        first_question_answers: List[str],
        second_question_answers: List[str],
        first_question_targets: List[str],
        second_question_targets: List[str],
    ) -> None:
        first_question = self.question_by_text(first_question_text)
        second_question = self.question_by_text(second_question_text)

        expect(first_question).to_be_visible(timeout=30000)
        expect(second_question).to_be_visible(timeout=30000)
        expect(first_question).to_contain_text("Переход к группе", timeout=30000)
        expect(second_question).to_contain_text("Переход к группе", timeout=30000)

        for index, answer in enumerate(first_question_answers):
            expect(first_question.locator('textarea[placeholder="Ответ"]').nth(index)).to_have_value(answer, timeout=30000)
        for target in first_question_targets:
            first_question.scroll_into_view_if_needed()
            expect(first_question).to_contain_text(target, timeout=30000)

        for index, answer in enumerate(second_question_answers):
            expect(second_question.locator('textarea[placeholder="Ответ"]').nth(index)).to_have_value(answer, timeout=30000)
        for target in second_question_targets:
            second_question.scroll_into_view_if_needed()
            expect(second_question).to_contain_text(target, timeout=30000)

    def assert_feedback_generated_groups_visible(self) -> None:
        expect(
            self.page.get_by_text("Какова вероятность, что Вы порекомендуете культурное мероприятие", exact=False)
        ).to_be_visible(timeout=30000)
        expect(
            self.page.get_by_text("Оцените, пожалуйста, организацию процесса обучения", exact=True)
        ).to_be_visible(timeout=30000)
        expect(
            self.page.get_by_text("Оцените, пожалуйста, общую организацию модуля", exact=True)
        ).to_be_visible(timeout=30000)

    # ── Дополнительные вопросы по теме ──────────────────────────────────

    def assert_tagged_additional_questions_visible(
        self,
        question_tag_name: str,
        main_question_text: str,
        additional_question_text: str,
    ) -> None:
        additional_settings = self.page.locator(".questions-additional")

        expect(self.page.locator('textarea[placeholder="Вопрос"]').first).to_have_value(main_question_text, timeout=30000)
        expect(additional_settings).to_contain_text("Количество дополнительных вопросов после неправильного ответа", timeout=30000)
        expect(additional_settings).to_contain_text("Тема вопроса", timeout=30000)
        expect(additional_settings).to_contain_text(question_tag_name, timeout=30000)

        additional_questions_tab = self.page.get_by_role("tab", name="Дополнительные вопросы")
        expect(additional_questions_tab).to_be_visible(timeout=30000)
        additional_questions_tab.click()

        expect(self.page.locator('textarea[placeholder="Вопрос"]').first).to_have_value(additional_question_text, timeout=30000)
        expect(additional_settings).to_contain_text("Тема вопроса", timeout=30000)
        expect(additional_settings).to_contain_text(question_tag_name, timeout=30000)

    def assert_additional_question_competition_visible(self, first_main_question_text: str, second_main_question_text: str) -> None:
        """Проверить конкуренцию двух основных вопросов за один допвопрос по теме:
        у первого счётчик = 1 и кнопка «+» доступна, у второго счётчик = 0 и заблокирована."""
        question_textareas = self.page.locator('textarea[placeholder="Вопрос"]')
        first_question_textarea = question_textareas.nth(0)
        second_question_textarea = question_textareas.nth(1)

        expect(first_question_textarea).to_have_value(first_main_question_text, timeout=30000)
        expect(second_question_textarea).to_have_value(second_main_question_text, timeout=30000)

        first_question = first_question_textarea.locator("xpath=ancestor::div[contains(@class, 'constructor-questions-item')]").first
        second_question = second_question_textarea.locator("xpath=ancestor::div[contains(@class, 'constructor-questions-item')]").first

        first_counter = first_question.locator(".constructor-widget-counter")
        expect(first_counter).to_contain_text("Количество дополнительных вопросов после неправильного ответа", timeout=30000)
        expect(first_counter.locator('input[type="number"]')).to_have_value("1", timeout=30000)

        second_question.scroll_into_view_if_needed()
        second_counter = second_question.locator(".constructor-widget-counter")
        expect(second_counter).to_contain_text("Количество дополнительных вопросов после неправильного ответа", timeout=30000)
        expect(second_counter.locator('input[type="number"]')).to_have_value("0", timeout=30000)
        # Кнопка «+» — вторая (последняя) из двух: иконка рендерится как inline SVG
        # без класса .mdi-plus (тот же разрыв с версией коллеги, что и в
        # edit_question_theme_via_ui — разведано на develop).
        expect(second_counter.locator("button").last).to_be_disabled(timeout=30000)

    # ── Каталог тем вопросов ─────────────────────────────────────────────
    # Перенос src/ui/pages/catalogs_page.py коллеги (CatalogsPage) — отдельного
    # Page Object в нашей архитектуре для этого не заводим (в задаче явно указано
    # «Локаторы только в Page Object (test_constructor_admin_page.py)»), поэтому
    # методы каталога тем вопросов живут здесь же.

    def open_question_themes_catalog(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}/admin/catalogs/test-themes")
        expect(self.page).to_have_url(re.compile(r".*/admin/catalogs/test-themes.*"), timeout=30000)
        expect(self.page.get_by_role("button", name=re.compile(r"Добавить\s+тему вопроса"))).to_be_visible(timeout=30000)

    def create_question_theme_via_ui(self, theme_name: str) -> None:
        self.page.get_by_role("button", name=re.compile(r"Добавить\s+тему вопроса")).click()

        modal = self.page.locator(".v-dialog--active")
        expect(modal).to_be_visible(timeout=30000)
        expect(modal).to_contain_text("Добавить тему вопроса")

        modal.get_by_role("textbox", name="Введите название").fill(theme_name)
        modal.get_by_role("button", name="Сохранить").click()
        expect(modal).not_to_be_visible(timeout=30000)

    def search_question_theme_by_name(self, theme_name: str) -> None:
        search_input = self.page.get_by_placeholder("Поиск")
        expect(search_input).to_be_visible(timeout=15000)
        search_input.fill(theme_name)
        expect(self.page.locator("tr", has_text=theme_name)).to_be_visible(timeout=30000)

    def edit_question_theme_via_ui(self, current_theme_name: str, new_theme_name: str) -> None:
        """Кнопка редактирования — первая в строке (иконка карандаша рендерится как
        inline SVG без класса .mdi-pencil, в отличие от версии коллеги: за ней вторым
        стоит удаление, см. разведку _scout_theme_edit.py на develop)."""
        row = self.page.locator("tr", has_text=current_theme_name)
        expect(row).to_be_visible(timeout=30000)
        row.locator("button").first.click()

        modal = self.page.locator(".v-dialog--active")
        expect(modal).to_be_visible(timeout=30000)
        expect(modal).to_contain_text("Редактировать тему вопроса")

        name_input = modal.get_by_role("textbox", name="Введите название")
        expect(name_input).to_have_value(current_theme_name, timeout=30000)
        name_input.fill(new_theme_name)
        modal.get_by_role("button", name="Сохранить").click()
        expect(modal).not_to_be_visible(timeout=30000)

    def assert_question_theme_row_visible(self, theme_name: str) -> None:
        row = self.page.locator("tr", has_text=theme_name)
        expect(row).to_be_visible(timeout=30000)
        expect(row).to_contain_text(theme_name)

    # ── Банк вопросов ────────────────────────────────────────────────────

    def add_question_from_bank_as_list(self, bank_question_text: str) -> None:
        self.page.get_by_text("Добавить вопрос(ы) из банка вопросов", exact=True).click()

        modal = self.page.get_by_role("dialog").filter(has_text="Добавить вопрос(ы) из банка вопросов")
        expect(modal).to_be_visible(timeout=30000)

        search_input = modal.locator('[data-qa="km-search"]')
        expect(search_input).to_be_visible(timeout=30000)
        search_input.fill(bank_question_text)
        self.page.wait_for_load_state("networkidle", timeout=30000)

        bank_question_row = modal.locator(".material", has_text=bank_question_text)
        expect(bank_question_row).to_be_visible(timeout=30000)
        bank_question_row.locator(".v-input--checkbox").click()

        modal.get_by_role("button", name="Добавить").click()

        insert_options_modal = self.page.get_by_role("dialog").filter(has_text="Добавить вопросы")
        expect(insert_options_modal).to_be_visible(timeout=30000)
        insert_options_modal.get_by_role("button", name="Списком").click()
        self.page.wait_for_load_state("networkidle", timeout=30000)

    def assert_bank_question_added_to_constructor(self, bank_question_text: str) -> None:
        """Иконка связи с банком вопросов — inline SVG без класса
        .mdi-file-table-box-outline (тот же разрыв с версией коллеги, что и в
        edit_question_theme_via_ui/assert_additional_question_competition_visible,
        разведано на develop): span[aria-haspopup="true"] в заголовке вопроса,
        в отличие от кнопки меню «...» (тоже aria-haspopup, но это <button>)."""
        question_textarea = self.page.locator('textarea[placeholder="Вопрос"]').last
        expect(question_textarea).to_have_value(bank_question_text, timeout=30000)
        question = question_textarea.locator("xpath=ancestor::div[contains(@class, 'constructor-questions-item')]").first
        expect(
            question.locator(".constructor-questions-item-header__content span[aria-haspopup='true']")
        ).to_be_visible(timeout=30000)

    # ── Последовательность опроса ───────────────────────────────────────

    def assert_poll_sequence_settings_visible(self, first_question_text: str, answer_text: str, target_group_title: str) -> None:
        expect(self.page.get_by_text("Последовательность вопросов по ответам", exact=True)).to_be_visible(timeout=30000)

        first_question_textarea = self.page.locator('textarea[placeholder="Вопрос"]').first
        expect(first_question_textarea).to_have_value(first_question_text, timeout=30000)
        first_question = first_question_textarea.locator("xpath=ancestor::div[contains(@class, 'constructor-questions-item')]").first

        expect(first_question.locator('textarea[placeholder="Ответ"]').first).to_have_value(answer_text, timeout=30000)
        expect(first_question).to_contain_text("Переход к группе", timeout=30000)
        expect(first_question).to_contain_text(target_group_title, timeout=30000)
