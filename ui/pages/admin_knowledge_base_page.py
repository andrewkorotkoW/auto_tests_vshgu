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
    def __init__(self, page: Page):
        super().__init__(page)

    # ── Достижение ───────────────────────────────────────────────────────

    def open_achievements_create_form(self) -> None:
        self.page.locator('a[href="/admin/knowledge-base"]').click(timeout=5000)
        self.page.locator('a[href="/admin/knowledge-base/achievements/created"]').click(timeout=5000)
        self.page.locator('a[href="/admin/knowledge-base/achievements/new"]').click(timeout=5000)
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

    def save_achievement(self) -> None:
        save_button = self.page.get_by_role("button", name="Сохранить")
        expect(save_button).to_be_visible(timeout=15000)
        save_button.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/achievements/created.*"), timeout=15000)

    def expect_achievement_created(self, name: str) -> None:
        expect(self.page.locator('a[href="/admin/knowledge-base/achievements/new"]')).to_be_visible(timeout=15000)
        self.page.reload()
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/achievements/created.*"), timeout=15000)
        expect(self.page.get_by_text(name, exact=True)).to_be_visible(timeout=15000)

    def create_achievement_with_material_count_icon(
        self,
        *,
        name: str,
        description: str,
        icon_path: Union[str, Path],
        material_type: str = "Статья",
        count: str = "1",
    ) -> None:
        self.open_achievements_create_form()
        self.fill_achievement_name(name)
        self.fill_achievement_description(description)
        self.upload_achievement_icon(icon_path)
        self.add_material_count_condition(material_type=material_type, count=count)
        self.save_achievement()
        self.expect_achievement_created(name)

    # ── Статья в БЗ ──────────────────────────────────────────────────────

    def open_material_create_form(self, admin_base_url: str) -> None:
        self.page.goto(f"{admin_base_url.rstrip('/')}/admin/knowledge-base/material")
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/material$"), timeout=15000)

    def select_material_type_article(self) -> None:
        self.page.locator(".v-input__append-inner").first.click(timeout=5000)
        option = self.page.get_by_text("Статья", exact=True)
        expect(option).to_be_visible(timeout=10000)
        option.click(timeout=5000)

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

    def save_material(self) -> None:
        save_button = self.page.locator("button.confirm__btn-ok")
        expect(save_button).to_be_visible(timeout=10000)
        expect(save_button).to_be_enabled(timeout=10000)
        save_button.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/knowledge-base/materials.*"), timeout=20000)

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
