"""Создание и карточка очного мероприятия типа «МТС Линк» в модуле программы.

Блок создания (до разделителя «часть 7/8» ниже) подтверждён живой разведкой на стенде
mts-link-release-main 29.10.2026 (реальный прод-аккаунт МТС Линк — см.
docs/test_cases/mts_link/16_prod_safe_run.md, правила безопасного прогона обязательны:
короткая длительность, префикс [ТЕСТ], cleanup). Раньше считалось, что отдельного
UI-флоу создания нет вовсе — неверно, путь просто не там, где ожидалось:

- «Добавить Активити» на вкладке «Расписание» модуля (AdminProgramsPage.
  add_activity_to_schedule) — это ТОЛЬКО прикрепление готового контента из базы
  активити (курсы/тесты/ПЗ), типа mts_link_webinar там нет вовсе.
- Реальный путь: у модуля должен быть задан и сохранён «Регион реализации»
  (AdminProgramsPage.set_module_region_and_save) — без него переключатель «О»
  недоступен для создания очных мероприятий. Переключение потока с «Д» (дистанционно,
  активно по умолчанию) на «О» (очно) открывает недельный календарь очных
  мероприятий. **Правый клик** (не левый!) по любому слоту календаря открывает форму
  «Создать Активити» — подтверждено разведкой через реальные Playwright-прогоны
  29.10.2026: `@click:time` на этом календаре привязан к тривиальному тогглеру, сама
  форма создания висит на `@contextmenu:time`. Левый клик (в т.ч. настоящий трастовый
  клик через Playwright/CDP, не только синтетический через JS) не открывает ничего —
  не баг теста, подтверждено прямым сравнением обработчиков в скомпилированном бандле.
  Только в поле «Тип» формы среди очных типов (очная лекция, мастер-класс, тренинг,
  вебинар, …) есть пункт «МТС Линк».

Эндпоинты `/schedule-item/{id}/mts-link`, `/schedule-item/{id}/mts-link/status` и
`/schedule-item/{id}/mts-link/attendance/{user_id}` на ветке не реализованы (404,
подтверждено разведкой) — статусы синхронизации лежат прямо в ответе
`GET .../schedule-items/{id}` (блок `data.attributes.mts_link`: `webinar_status`,
`record_status`, `*_sync_status`) — см. ScheduleItemsEndpoint.get() в
api/endpoints/schedule_items.py, им и нужно пользоваться для проверок в тестах, а не
api/endpoints/mts_link.py (та часть файла не подтверждена и не тронута здесь).

Блок «часть 7/8» ниже (статусы синхронизации в карточке, кнопка «Повторить») этой
разведкой НЕ подтверждён — локаторы остались как были (data-qa, скорее всего не
существуют в реальном DOM по аналогии с type_select/url_field выше), трогать не стал:
вне задачи (создание мероприятия через UI + вкладка организации), см. TODO внутри.
"""
from playwright.sync_api import Page, Locator, expect

from ui.pages.base_page import BasePage
from config.settings import settings

STATUS_PARTS_RU = {
    "creation": "Создание вебинара",
    "webinar_data": "Данные вебинара",
    "participants": "Участники",
    "lecturers": "Лекторы",
    "files": "Файлы презентаций",
}


class AdminEventMtsPage(BasePage):
    # Порядок иконок в поле «Тип» формы «Создать Активити» (очные типы мероприятия).
    # У иконок нет текста/data-qa в DOM — название видно только во всплывающей
    # подсказке по hover, которая ненадёжна для автотеста (Vuetify рендерит контент
    # тултипа лениво, только на настоящее движение курсора). Выбираем по порядковому
    # номеру; если разработка добавит иконке атрибут-якорь — заменить на него.
    MTS_LINK_TYPE_INDEX = 4  # очная лекция(0), мастер-класс(1), тренинг(2), вебинар(3), МТС Линк(4)

    def __init__(self, page: Page):
        super().__init__(page)

    def open(self, ui_base_url: str, program_id: int, stream_id: int, module_id: int, item_id: int) -> None:
        self.page.goto(
            f"{ui_base_url}/programs/{program_id}/streams/{stream_id}"
            f"/modules/{module_id}/schedule-items/{item_id}"
        )
        self.wait_loaded()

    # ── переключатель «Очно»/«Дистанционно» у модуля ─────────────────────

    def switch_to_offline_tab(self) -> None:
        """«О» (очно) — открывает недельный календарь очных мероприятий модуля.
        Регион модуля должен быть уже задан и сохранён (см. докстринг модуля), иначе
        переключатель визуально кликабелен, но создание мероприятия в нём невозможно."""
        tab = self.page.locator("xpath=//button[normalize-space()='О']")
        expect(tab).to_be_visible(timeout=settings.UI_TIMEOUT)
        tab.click(timeout=settings.UI_TIMEOUT)
        expect(self.page.locator(".v-calendar-daily")).to_be_visible(timeout=settings.UI_TIMEOUT)

    # ── форма «Создать Активити» (реальный путь создания мероприятия) ────

    def _modal(self) -> Locator:
        return self.page.locator("xpath=//div[contains(@class,'v-dialog--active')]")

    def open_create_event_modal(self) -> None:
        """ПРАВЫЙ клик (контекстное меню) по слоту недельного календаря открывает
        форму создания — см. докстринг модуля. Берём слот не в прошлом (класс
        v-past у дня-колонки — в прошлых днях контекстное меню тоже не создаёт
        мероприятие) — конкретные день/час в самом клике иначе не важны: реальные
        дату и время задаём отдельно полями («Дата»/«Время с»/«Время по», см. ниже)
        уже после открытия."""
        not_past_day = self.page.locator(
            "xpath=//div[contains(@class,'v-calendar-daily__day') and not(contains(@class,'v-past'))]"
        ).first
        slot = not_past_day.locator(".v-calendar-daily__day-interval").first
        expect(slot).to_be_visible(timeout=settings.UI_TIMEOUT)
        slot.scroll_into_view_if_needed(timeout=settings.UI_TIMEOUT)
        slot.click(button="right", timeout=settings.UI_TIMEOUT)
        expect(self._modal()).to_be_visible(timeout=settings.UI_TIMEOUT)

    def select_mts_link_type(self) -> None:
        """Пункт «МТС Линк» в поле «Тип» (см. MTS_LINK_TYPE_INDEX). Поле «Название»
        заблокировано до выбора типа — вызывать этот метод первым."""
        type_button = self.page.locator("xpath=//label[normalize-space()='Тип']/parent::div//button")
        expect(type_button).to_be_visible(timeout=settings.UI_TIMEOUT)
        type_button.click(timeout=settings.UI_TIMEOUT)

        items = self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
            "//div[contains(@class,'list__item')]"
        )
        item = items.nth(self.MTS_LINK_TYPE_INDEX)
        expect(item).to_be_visible(timeout=settings.UI_TIMEOUT)
        item.click(timeout=5000)

    def fill_name(self, name: str) -> None:
        field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog--active')]//label[normalize-space()='Название']/following::input[1]"
        )
        expect(field).to_be_visible(timeout=settings.UI_TIMEOUT)
        field.fill(name, timeout=5000)

    def set_date(self, value: str) -> None:
        """value — "ДД.ММ.ГГГГ". Задать явно: день/час клика по календарю
        (open_create_event_modal) не гарантирует нужную дату."""
        field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog--active')]"
            "//label[normalize-space()='Дата']/following::input[@type='text'][1]"
        )
        expect(field).to_be_visible(timeout=settings.UI_TIMEOUT)
        field.fill(value, timeout=5000)

    def set_time_from(self, value: str) -> None:
        """value — "ЧЧ:ММ"."""
        field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog--active')]"
            "//label[normalize-space()='Время с']/following::input[@type='text'][1]"
        )
        expect(field).to_be_visible(timeout=settings.UI_TIMEOUT)
        field.fill(value, timeout=5000)

    def set_time_to(self, value: str) -> None:
        """value — "ЧЧ:ММ"."""
        field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog--active')]"
            "//label[normalize-space()='Время по']/following::input[@type='text'][1]"
        )
        expect(field).to_be_visible(timeout=settings.UI_TIMEOUT)
        field.fill(value, timeout=5000)

    def fill_location(self, value: str) -> None:
        field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog--active')]//label[normalize-space()='Место']/following::input[1]"
        )
        expect(field).to_be_visible(timeout=settings.UI_TIMEOUT)
        field.fill(value, timeout=5000)

    def select_direction(self, value: str) -> None:
        """«Направление» — фильтрует список по вводу, нужно точное совпадение (как
        select_program_type_value в admin_programs_page.py)."""
        self._select_exact_value_by_label("Направление", value)

    def select_broad_topic(self, value: str) -> None:
        """«Широкая тема» — доступна только после выбора «Направление» (список
        подгружается асинхронно под выбранное направление)."""
        self._select_exact_value_by_label("Широкая тема", value)

    # Вера — user_id 2, реальный человек (zinoveva-vs@ranepa.ru, в системе отображается
    # как «Романова … Админовна», логин admin2_org_2 — подтверждено GET /api/v1/users/2
    # 29.10.2026), лектор по умолчанию во всём сценарии МТС Линк в этой сессии (её
    # согласие на роль лектора для тестовых вебинаров уже получено, см.
    # docs/test_cases/mts_link/16_prod_safe_run.md). Решение владельца 29.10.2026:
    # использовать её и в этом автотесте, а не случайный admin-аккаунт — несмотря на то,
    # что ей будет уходить настоящее email-приглашение при каждом прогоне.
    VERA_EMAIL_FRAGMENT = "admin2@org2.ru"

    def select_teacher(self, email_fragment: str = VERA_EMAIL_FRAGMENT) -> None:
        """«Преподаватели» — мультиселект. По умолчанию выбирает Веру (см.
        VERA_EMAIL_FRAGMENT) — лектору очного мероприятия «МТС Линк» уходит настоящее
        email-приглашение (sendEmail=true, см. docs/test_cases/mts_link/
        16_prod_safe_run.md), но это осознанный выбор владельца для этого теста, не
        случайность.

        Мультиселект не закрывает выпадающий список после выбора пункта (в отличие от
        одиночных select), поэтому явно закрываем Escape — иначе открытый список
        перекрывает «Сохранить» и клик по нему падает по таймауту (подтверждено
        прогоном 29.10.2026)."""
        self._select_item_containing_by_label("Преподаватели", email_fragment)
        self.page.keyboard.press("Escape")

    def save_event(self) -> int:
        """Кликает «Сохранить» в карточке мероприятия и дожидается ответа
        POST .../schedule-items — возвращает id созданного элемента расписания."""
        save_button = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog--active')]//button[.//span[normalize-space()='Сохранить']]"
        )
        expect(save_button).to_be_visible(timeout=settings.UI_TIMEOUT)
        expect(save_button).to_be_enabled(timeout=settings.UI_TIMEOUT)
        with self.page.expect_response(
            lambda r: "/schedule-items" in r.url and r.request.method == "POST", timeout=settings.UI_TIMEOUT
        ) as response_info:
            save_button.click(timeout=settings.UI_TIMEOUT)
        data = response_info.value.json()
        return int(data["data"]["id"])

    def create_mts_webinar(
        self,
        *,
        name: str,
        date: str,
        time_from: str,
        time_to: str,
        location: str,
        direction: str,
        broad_topic: str,
    ) -> int:
        """Полный сценарий: открыть форму, выбрать тип «МТС Линк», заполнить все поля,
        сохранить. Модуль должен уже иметь сохранённый регион и быть переключён на
        вкладку «О» (см. AdminProgramsPage.set_module_region_and_save,
        switch_to_offline_tab). Возвращает id созданного элемента расписания.

        Порядок важен: «Название» заблокировано, пока не выбраны и «Направление», и
        «Широкая тема» (не только «Тип», как можно было бы ожидать) — подтверждено
        разведкой 29.10.2026, поэтому они выбираются раньше заполнения названия."""
        self.open_create_event_modal()
        self.select_mts_link_type()
        self.select_direction(direction)
        self.select_broad_topic(broad_topic)
        self.fill_name(name)
        self.set_date(date)
        self.set_time_from(time_from)
        self.set_time_to(time_to)
        self.fill_location(location)
        self.select_teacher()
        return self.save_event()

    # ── часть 7: статусы интеграции (НЕ подтверждено разведкой 29.10.2026) ──
    # Контракт из докстринга модуля выше: статусы синхронизации реально лежат в
    # GET .../schedule-items/{id} -> data.attributes.mts_link, а не через отдельные
    # эндпоинты/виджеты ниже. Эти локаторы (data-qa) остались как были написаны до
    # появления ветки — вероятно, не существуют в реальном DOM. TODO: уточнить вживую,
    # если понадобятся тесты на карточку статусов (вне задачи создания мероприятия).

    def summary_status_badge(self) -> Locator:
        return self.page.locator("[data-qa='mts-link-summary-status']")

    def summary_status_text(self) -> str:
        badge = self.summary_status_badge()
        expect(badge).to_be_visible(timeout=settings.UI_TIMEOUT)
        return badge.text_content() or ""

    def part_status_row(self, part: str) -> Locator:
        """part — ключ из STATUS_PARTS_RU."""
        label = STATUS_PARTS_RU[part]
        return self.page.locator(f"[data-qa='mts-link-part-row']", has_text=label)

    def part_status_text(self, part: str) -> str:
        row = self.part_status_row(part)
        expect(row).to_be_visible(timeout=settings.UI_TIMEOUT)
        return row.text_content() or ""

    # ── часть 8: ручной перезапуск (НЕ подтверждено) ──────────────────────

    def retry_button(self, part: str) -> Locator:
        return self.part_status_row(part).locator("[data-qa='mts-link-retry-button']")

    def click_retry(self, part: str) -> None:
        button = self.retry_button(part)
        expect(button).to_be_visible(timeout=settings.UI_TIMEOUT)
        expect(button).to_be_enabled(timeout=settings.UI_TIMEOUT)
        button.click(timeout=settings.UI_TIMEOUT)

    def is_retry_button_visible(self, part: str) -> bool:
        return self.retry_button(part).is_visible(timeout=5000)

    # ── список мероприятий / календарь (НЕ подтверждено) ──────────────────

    def status_indicator_in_list(self, event_name: str) -> Locator:
        safe = event_name.replace("'", "")
        return self.page.locator(
            f"xpath=//tr[.//*[normalize-space()='{safe}']]//*[@data-qa='mts-link-status-indicator']"
        )

    def status_indicator_in_calendar(self, event_name: str) -> Locator:
        safe = event_name.replace("'", "")
        return self.page.locator(
            f"xpath=//*[contains(@class,'calendar')]//*[normalize-space()='{safe}']"
            "/ancestor::*[1]//*[@data-qa='mts-link-status-indicator']"
        )
