"""Админка → карточка активити (/admin/activities/{id}?i=1), вкладка «Чат с ИИ», и список
активити (значок в строке, фильтр «Курсы с чатом ИИ») — локаторы и контракт сняты разведкой,
см. docs/ai_chat_recon.md (разделы 3.1, 3.2) и docs/plans/2026-10-07_ai_chat_pmi_mission.md.
"""
from pathlib import Path
from typing import Union

from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage


class AdminActivityAiChatPage(BasePage):
    PATH = "/admin/activities"

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Карточка активити: открытие на вкладке «Чат с ИИ» ────────────────

    def open_card(self, ui_base_url: str, activity_id: int) -> None:
        """?i=1 открывает карточку сразу на вкладке «Чат с ИИ», без клика по вкладке
        (docs/ai_chat_recon.md, 1.1)."""
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATH}/{activity_id}?i=1")
        expect(self.tab_container).to_be_visible(timeout=15000)

    @property
    def tab_container(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat")

    @property
    def settings_title(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat-settings__title")

    @property
    def settings_description(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat-settings__description")

    # ── Переключатель ─────────────────────────────────────────────────────

    @property
    def switch_input(self) -> Locator:
        return self.page.locator('input[data-qa="activity__ai-chat-switch"]')

    @property
    def switch_clickable_area(self) -> Locator:
        """Кликабельная область переключателя — сам чекбокс может не принимать клик
        напрямую (docs/ai_chat_recon.md, 3.1)."""
        return self.page.locator(".activity-details-ai-chat-settings__switch")

    def toggle_switch(self) -> None:
        expect(self.switch_clickable_area).to_be_visible(timeout=15000)
        self.switch_clickable_area.click(timeout=5000)

    def is_switch_checked(self) -> bool:
        return self.switch_input.is_checked()

    @property
    def context_block(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat__context")

    # ── Загрузка файлов ──────────────────────────────────────────────────

    @property
    def dropzone(self) -> Locator:
        """Клик открывает системный выбор файла — скрытого input[type=file] нет
        (docs/ai_chat_recon.md, 3.1), поэтому загрузка идёт через expect_file_chooser."""
        return self.page.locator(".activity-details-ai-chat-uploader__dropzone")

    def upload_file(self, path: Union[str, Path]) -> None:
        expect(self.dropzone).to_be_visible(timeout=15000)
        with self.page.expect_file_chooser(timeout=15000) as file_chooser_info:
            self.dropzone.click(timeout=5000)
        file_chooser_info.value.set_files(str(path))

    def drop_unsupported_file(self, path: Union[str, Path]) -> None:
        """Перетаскивание файла (например .xlsx) в дропзону — set_input_files не годится
        (скрытого input[type=file] нет), эмулируем drag'n'drop через DataTransfer, как
        указано в плане миссии (шаг 13: page.dispatch_event('drop', {dataTransfer}))."""
        import mimetypes

        file_path = Path(path)
        file_bytes = list(file_path.read_bytes())
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        data_transfer = self.page.evaluate_handle(
            """([bytes, fileName, fileType]) => {
                const dt = new DataTransfer();
                const file = new File([new Uint8Array(bytes)], fileName, {type: fileType});
                dt.items.add(file);
                return dt;
            }""",
            [file_bytes, file_path.name, mime_type],
        )
        expect(self.dropzone).to_be_visible(timeout=15000)
        self.dropzone.dispatch_event("drop", {"dataTransfer": data_transfer})

    # ── Статус обработки / список файлов ─────────────────────────────────

    @property
    def status_block(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat-status")

    def is_processing(self) -> bool:
        return "_processing" in (self.status_block.get_attribute("class") or "")

    def is_error(self) -> bool:
        return "_error" in (self.status_block.get_attribute("class") or "")

    @property
    def files_block(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat-files")

    @property
    def empty_state(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat-files__empty")

    @property
    def empty_state_note(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat-files__empty-note")

    @property
    def file_rows(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat-files__file")

    def file_row_by_name(self, file_name: str) -> Locator:
        safe = file_name.replace("'", "")
        return self.page.locator(
            "xpath=//*[contains(@class,'activity-details-ai-chat-files__file')]"
            f"[.//*[contains(@class,'activity-details-ai-chat-files__file-name') and contains(normalize-space(),'{safe}')]]"
        )

    def remove_file_button(self, file_name: str) -> Locator:
        return self.file_row_by_name(file_name).locator(".activity-details-ai-chat-files__file-remove")

    # ── Удаление файла (корзина + модалка подтверждения) ────────────────

    @property
    def confirm_modal(self) -> Locator:
        return self.page.locator(".base-modal")

    def remove_file(self, file_name: str) -> None:
        self.remove_file_button(file_name).click(timeout=5000)
        expect(self.confirm_modal).to_be_visible(timeout=15000)
        self.confirm_modal.locator(".confirm__btn-ok").click(timeout=5000)

    def cancel_remove_file(self, file_name: str) -> None:
        self.remove_file_button(file_name).click(timeout=5000)
        expect(self.confirm_modal).to_be_visible(timeout=15000)
        self.confirm_modal.locator(".confirm__btn-cancel").click(timeout=5000)

    # ── История ИИ-чата ──────────────────────────────────────────────────

    @property
    def history_block(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat-history")

    @property
    def history_title(self) -> Locator:
        return self.page.locator(".activity-details-ai-chat-history__title")

    def _counter_by_label(self, label_text: str) -> Locator:
        return self.page.locator(
            "xpath=//*[contains(@class,'activity-details-ai-chat-history__counter')]"
            f"[.//*[contains(@class,'activity-details-ai-chat-history__counter-label') and contains(normalize-space(),'{label_text}')]]"
        )

    def questions_count(self) -> str:
        counter = self._counter_by_label("Задано вопросов")
        value = counter.locator(".activity-details-ai-chat-history__counter-value")
        expect(value).to_be_visible(timeout=15000)
        return value.text_content().strip()

    def answers_count(self) -> str:
        counter = self._counter_by_label("Получено ответов")
        value = counter.locator(".activity-details-ai-chat-history__counter-value")
        expect(value).to_be_visible(timeout=15000)
        return value.text_content().strip()

    @property
    def download_history_button(self) -> Locator:
        return self.page.locator("button:has-text('Скачать историю')")

    def click_download_history(self) -> None:
        expect(self.download_history_button).to_be_visible(timeout=15000)
        self.download_history_button.click(timeout=5000)

    # ── Список активити: значок «Чат с ИИ» и фильтр ──────────────────────

    def icon_in_row(self, row: Locator) -> Locator:
        """SVG-иконка «Чат с ИИ» в ячейке типа сущности строки таблицы активити (row —
        например AdminActivitiesPage.row_by_name), docs/ai_chat_recon.md, 3.2."""
        return row.locator("td.text-center .d-flex svg path[d^='M20 2H4C2.9 2 2 2.9']")

    def expect_icon_visible(self, row: Locator) -> None:
        expect(self.icon_in_row(row)).to_be_visible(timeout=15000)

    def expect_icon_hidden(self, row: Locator) -> None:
        expect(self.icon_in_row(row)).to_have_count(0)

    @property
    def ai_chat_filter_checkbox(self) -> Locator:
        return self.page.locator(
            "xpath=//div[contains(@class,'v-input__slot')][.//*[contains(text(),'Курсы с чатом ИИ')]]//input[@type='checkbox']"
        )

    def enable_ai_chat_filter(self) -> None:
        expect(self.ai_chat_filter_checkbox).to_be_visible(timeout=15000)
        self.ai_chat_filter_checkbox.check(timeout=5000)
