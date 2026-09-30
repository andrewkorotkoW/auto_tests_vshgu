"""Карточка очного мероприятия типа «МТС Линк» в модуле программы (части 0, 1, 7, 8).

Новый файл (а не расширение `admin_programs_page.py`) — мероприятие «МТС Линк» открывает
отдельную карточку со своим блоком статусов интеграции (часть 7) и кнопкой «Повторить»
(часть 8), которых нет у обычного очного мероприятия; общие для обоих типов действия
(создание элемента расписания, открытие модуля) уже есть в `AdminProgramsPage` и здесь не
дублируются — тесты создают мероприятие через API (`created_schedule_item`,
`api/endpoints/mts_link.py: build_event_payload`) и открывают только эту карточку.

Разведка (только чтение, через код существующих page objects — живого браузера в этой
среде нет) подтвердила, что обычное очное мероприятие создаётся по маршруту
`/programs/{id}/streams/{id}/modules/{id}/schedule-items/{id}` (см. `admin_programs_page.py`,
`api/endpoints/schedule_items.py`) — карточка мероприятия «МТС Линк» предположительно тот
же путь, содержимое (иконка типа, поле URL, блок статусов) не подтверждено.
TODO: уточнить после появления ветки — каждый локатор.
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
    def __init__(self, page: Page):
        super().__init__(page)

    def open(self, ui_base_url: str, program_id: int, stream_id: int, module_id: int, item_id: int) -> None:
        self.page.goto(
            f"{ui_base_url}/programs/{program_id}/streams/{stream_id}"
            f"/modules/{module_id}/schedule-items/{item_id}"
        )
        self.wait_loaded()

    def open_create_form(self, ui_base_url: str, program_id: int, stream_id: int, module_id: int) -> None:
        """Форма создания очного мероприятия в модуле — путь схемы схож с карточкой
        (см. open) с суффиксом /create по конвенции остальных create-форм репозитория
        (`AdminProgramsPage.open_create_program_form`/`open_create_stream_form`).
        TODO: уточнить после появления ветки."""
        self.page.goto(
            f"{ui_base_url}/programs/{program_id}/streams/{stream_id}"
            f"/modules/{module_id}/schedule-items/create"
        )
        self.wait_loaded()

    def type_select(self) -> Locator:
        return self.page.locator("[data-qa='schedule-item-type-select']")

    def type_options(self) -> Locator:
        self.type_select().click(timeout=settings.UI_TIMEOUT)
        return self.page.locator("[data-qa='schedule-item-type-option']")

    def is_mts_link_type_option_visible(self) -> bool:
        """Пункт «МТС Линк» в селекте типа мероприятия — виден только при настроенной и
        проверенной интеграции тенанта (часть 0, раздел «Видимость типа»)."""
        option = self.page.locator("[data-qa='schedule-item-type-option-mts_link']")
        return option.is_visible(timeout=5000)

    def select_mts_link_type(self) -> None:
        option = self.page.locator("[data-qa='schedule-item-type-option-mts_link']")
        expect(option).to_be_visible(timeout=settings.UI_TIMEOUT)
        option.click(timeout=settings.UI_TIMEOUT)

    def is_type_field_editable(self) -> bool:
        """При редактировании существующего мероприятия тип нельзя менять ни в одну из
        сторон (часть 0, раздел «Тип мероприятия»)."""
        return not self.type_select().is_disabled()

    # ── часть 0: тип мероприятия ────────────────────────────────────────

    def type_icon(self) -> Locator:
        """Иконка типа «МТС Линк» на карточке/в списке — видна только при настроенной
        интеграции тенанта (часть 0, раздел «Форма создания»)."""
        return self.page.locator("[data-qa='mts-link-type-icon']")

    def url_field(self) -> Locator:
        return self.page.locator("[data-qa='schedule-item-url-field'], input[name='url']")

    def is_url_field_disabled(self) -> bool:
        field = self.url_field()
        expect(field).to_be_visible(timeout=settings.UI_TIMEOUT)
        return field.is_disabled()

    # ── часть 7: статусы интеграции ─────────────────────────────────────

    def summary_status_badge(self) -> Locator:
        return self.page.locator("[data-qa='mts-link-summary-status']")

    def summary_status_text(self) -> str:
        badge = self.summary_status_badge()
        expect(badge).to_be_visible(timeout=settings.UI_TIMEOUT)
        return badge.text_content() or ""

    def part_status_row(self, part: str) -> Locator:
        """Строка статуса одной из пяти частей синхронизации в карточке (часть 7,
        раздел «Карточка мероприятия»), part — ключ из STATUS_PARTS_RU."""
        label = STATUS_PARTS_RU[part]
        return self.page.locator(f"[data-qa='mts-link-part-row']", has_text=label)

    def part_status_text(self, part: str) -> str:
        row = self.part_status_row(part)
        expect(row).to_be_visible(timeout=settings.UI_TIMEOUT)
        return row.text_content() or ""

    # ── часть 8: ручной перезапуск ───────────────────────────────────────

    def retry_button(self, part: str) -> Locator:
        """Кнопка «Повторить» доступна только у части в статусе «Ошибка»."""
        return self.part_status_row(part).locator("[data-qa='mts-link-retry-button']")

    def click_retry(self, part: str) -> None:
        button = self.retry_button(part)
        expect(button).to_be_visible(timeout=settings.UI_TIMEOUT)
        expect(button).to_be_enabled(timeout=settings.UI_TIMEOUT)
        button.click(timeout=settings.UI_TIMEOUT)

    def is_retry_button_visible(self, part: str) -> bool:
        return self.retry_button(part).is_visible(timeout=5000)

    # ── список мероприятий / календарь ───────────────────────────────────

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
