"""Админка (global) → «База знаний»: создание достижения с условием и иконкой,
создание статьи через редактор.

Перенос tests/ui/knowledge_base_achievements/test_01_admin_create_achievement_material_count.py
и test_02_admin_create_article_material.py коллеги (репозиторий lms, feature/my-tests) —
там не было отдельного locators-файла, действия шли прямо в тестах.
"""
import re
from pathlib import Path
from typing import Union

from playwright.sync_api import Page, expect
from ui.pages.base_page import BasePage


class AdminKnowledgeBasePage(BasePage):
    # Ключ — тип материала как в API (KnowledgeBaseEndpoint.create_material/create_course_material),
    # значение — подпись в выпадающем списке условия «Количество материалов» в форме достижения.
    MATERIAL_TYPE_LABELS = {
        "article": "Статья",
        "video": "Видео",
        "audio": "Аудио",
        "book": "Книга",
        "file": "Файл",
        "course": "Курс",
    }

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Достижение ───────────────────────────────────────────────────────

    def open_achievements_create_form(self, ui_base_url: str) -> None:
        # В сайдбаре админки нет пункта "База знаний" (раздел не связан с основной
        # навигацией) — попасть в «Достижения» можно только прямой навигацией.
        self.page.goto(f"{ui_base_url.rstrip('/')}/admin/knowledge-base/achievements/created")
        create_link = self.page.locator('a[href="/admin/knowledge-base/achievements/new"]')
        expect(create_link).to_be_visible(timeout=15000)
        create_link.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/achievements/new"), timeout=15000)

    def fill_achievement_name(self, name: str) -> None:
        field = self.page.get_by_label("Название достижения")
        expect(field).to_be_visible(timeout=15000)
        field.fill(name, timeout=5000)

    def fill_achievement_description(self, text: str) -> None:
        field = self.page.get_by_label("Описание")
        expect(field).to_be_visible(timeout=15000)
        field.fill(text, timeout=5000)

    def upload_achievement_icon(self, path: Union[str, Path]) -> None:
        self.page.locator('input[type="file"]').set_input_files(str(path))

    def add_material_count_condition(self, material_type: str = "Статья", count: str = "1") -> None:
        add_condition_button = self.page.get_by_role("button", name=re.compile("Добавить условие"))
        expect(add_condition_button).to_be_visible(timeout=15000)
        add_condition_button.click(timeout=5000)

        condition_option = self.page.get_by_text("Количество материалов", exact=True)
        expect(condition_option).to_be_visible(timeout=15000)
        condition_option.click(timeout=5000)

        material_type_select = self.page.locator(".v-select__selections input[readonly]").last
        expect(material_type_select).to_be_visible(timeout=15000)
        material_type_select.click(timeout=5000)

        type_option = self.page.get_by_text(material_type, exact=True)
        expect(type_option).to_be_visible(timeout=15000)
        type_option.click(timeout=5000)

        count_field = self.page.locator('input[type="number"]')
        expect(count_field).to_be_visible(timeout=15000)
        count_field.fill(count, timeout=5000)

    def add_material_count_condition_for_type(self, material_type: str, count: str = "1") -> None:
        """Как add_material_count_condition, но принимает тип материала в виде ключа API
        (article/video/audio/book/file/course) — переводит его в подпись UI сама.
        Нужна для переноса test_01..06 коллеги (там 6 копий одного сценария, различающихся
        только типом материала)."""
        label = self.MATERIAL_TYPE_LABELS.get(material_type)
        if label is None:
            raise ValueError(
                f"Неизвестный тип материала: {material_type!r}. "
                f"Допустимые: {sorted(self.MATERIAL_TYPE_LABELS)}"
            )
        self.add_material_count_condition(material_type=label, count=count)

    def save_achievement(self) -> None:
        save_button = self.page.get_by_role("button", name="Сохранить")
        expect(save_button).to_be_visible(timeout=15000)
        save_button.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/achievements/created.*"), timeout=15000)

    def save_achievement_and_get_id(self) -> int:
        """Сохранить достижение и вернуть его ID из ответа POST-запроса (для teardown через API —
        в форме админки ID достижения нигде не отображается)."""
        save_button = self.page.get_by_role("button", name="Сохранить")
        expect(save_button).to_be_visible(timeout=15000)
        with self.page.expect_response(
            lambda resp: "/admin/achievements" in resp.url and resp.request.method == "POST"
        ) as resp_info:
            save_button.click(timeout=5000)
        achievement_id = resp_info.value.json()["data"]["id"]
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/achievements/created.*"), timeout=15000)
        return achievement_id

    def expect_achievement_created(self, name: str) -> None:
        expect(self.page.locator('a[href="/admin/knowledge-base/achievements/new"]')).to_be_visible(timeout=15000)
        self.page.reload()
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/achievements/created.*"), timeout=15000)
        expect(self.page.get_by_text(name, exact=True)).to_be_visible(timeout=15000)

    def create_achievement_with_material_count_icon(
        self,
        *,
        ui_base_url: str,
        name: str,
        description: str,
        icon_path: Union[str, Path],
        material_type: str = "Статья",
        count: str = "1",
    ) -> int:
        self.open_achievements_create_form(ui_base_url)
        self.fill_achievement_name(name)
        self.fill_achievement_description(description)
        self.upload_achievement_icon(icon_path)
        self.add_material_count_condition(material_type=material_type, count=count)
        achievement_id = self.save_achievement_and_get_id()
        self.expect_achievement_created(name)
        return achievement_id

    def create_achievement_with_material_count_icon_for_type(
        self,
        *,
        ui_base_url: str,
        name: str,
        description: str,
        icon_path: Union[str, Path],
        material_type: str,
        count: str = "1",
    ) -> int:
        """create_achievement_with_material_count_icon с типом материала как ключом API
        (article/video/audio/book/file/course) вместо русской подписи UI."""
        self.open_achievements_create_form(ui_base_url)
        self.fill_achievement_name(name)
        self.fill_achievement_description(description)
        self.upload_achievement_icon(icon_path)
        self.add_material_count_condition_for_type(material_type=material_type, count=count)
        achievement_id = self.save_achievement_and_get_id()
        self.expect_achievement_created(name)
        return achievement_id

    # ── Статья в БЗ ──────────────────────────────────────────────────────

    def open_material_create_form(self, admin_base_url: str) -> None:
        self.page.goto(f"{admin_base_url.rstrip('/')}/admin/knowledge-base/material")
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/material$"), timeout=15000)

    def select_material_type(self, label: str) -> None:
        self.page.locator(".v-input__append-inner").first.click(timeout=5000)
        option = self.page.get_by_text(label, exact=True)
        expect(option).to_be_visible(timeout=10000)
        option.click(timeout=5000)

    def select_material_type_article(self) -> None:
        self.select_material_type("Статья")

    def fill_material_name(self, name: str) -> None:
        field = self.page.get_by_label("Название материала")
        expect(field).to_be_visible(timeout=15000)
        field.fill(name, timeout=5000)

    def fill_material_short_description(self, text: str) -> None:
        field = self.page.get_by_label("Короткое описание")
        expect(field).to_be_visible(timeout=15000)
        field.fill(text, timeout=5000)

    def fill_article_text(self, text: str) -> None:
        editor = self.page.locator(".fr-element[contenteditable='true']").first
        expect(editor).to_be_visible(timeout=10000)
        editor.fill(text, timeout=5000)

    def fill_material_description(self, text: str) -> None:
        """Для типов видео/аудио/книга/файл поле «Описание» — тот же редактор
        (единственный .fr-element на форме), что и «Текст статьи» у типа «Статья»."""
        self.fill_article_text(text)

    def set_material_duration(self, hours: str = "0", minutes: str = "1") -> None:
        """Поля «Часы»/«Минуты» — есть только у видео и аудио."""
        hours_field = self.page.get_by_label("Часы", exact=True)
        expect(hours_field).to_be_visible(timeout=10000)
        hours_field.fill(hours, timeout=5000)
        minutes_field = self.page.get_by_label("Минуты", exact=True)
        expect(minutes_field).to_be_visible(timeout=10000)
        minutes_field.fill(minutes, timeout=5000)

    def upload_material_content_file(self, path: Union[str, Path], accept_hint: str) -> None:
        """Загрузка контентного файла материала (не обложки — у обложки accept=".jpeg,.jpg,.png",
        поэтому оба input[type=file] на форме различаются через accept_hint, напр. ".mp4"/".mp3"/".pdf").
        Дожидается ответа /upload/material_files — без этого «Сохранить» можно нажать раньше,
        чем файл прикрепится к материалу, и он сохранится без file_uuid (гонка, найдено при переносе)."""
        file_input = self.page.locator(f'input[type="file"][accept*="{accept_hint}"]')
        with self.page.expect_response(lambda resp: "/upload/material_files" in resp.url, timeout=30000):
            file_input.set_input_files(str(path), timeout=10000)

    def select_material_course(self, course_name: str) -> None:
        """Тип материала «Курс»: выбрать уже существующий курс (Tincan) из автокомплита."""
        field = self.page.get_by_label("Выбрать курс")
        expect(field).to_be_visible(timeout=15000)
        field.click(timeout=5000)
        field.fill(course_name, timeout=5000)
        option = self.page.get_by_text(course_name, exact=True)
        expect(option).to_be_visible(timeout=15000)
        option.click(timeout=5000)

    def save_material(self) -> None:
        save_button = self.page.locator("button.confirm__btn-ok")
        expect(save_button).to_be_visible(timeout=10000)
        expect(save_button).to_be_enabled(timeout=10000)
        save_button.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/materials.*"), timeout=20000)

    def save_material_and_get_id(self) -> int:
        """Сохранить материал и вернуть его ID из ответа POST-запроса (для teardown через API —
        в форме админки ID материала нигде не отображается)."""
        save_button = self.page.locator("button.confirm__btn-ok")
        expect(save_button).to_be_visible(timeout=10000)
        expect(save_button).to_be_enabled(timeout=10000)
        with self.page.expect_response(
            lambda resp: "/knowledge-base/admin/materials" in resp.url and resp.request.method == "POST"
        ) as resp_info:
            save_button.click(timeout=5000)
        material_id = resp_info.value.json()["data"]["id"]
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/materials.*"), timeout=20000)
        return material_id

    def expect_material_created(self, name: str) -> None:
        self.page.reload()
        expect(self.page.get_by_text(name, exact=True)).to_be_visible(timeout=15000)

    def create_article_material(
        self,
        *,
        admin_base_url: str,
        name: str,
        short_description: str,
        article_text: str,
    ) -> None:
        self.open_material_create_form(admin_base_url)
        self.select_material_type_article()
        self.fill_material_name(name)
        self.fill_material_short_description(short_description)
        self.fill_article_text(article_text)
        self.save_material()
        self.expect_material_created(name)
