"""Админка → База пользователей (/admin/users): поиск, строка пользователя, чипы колонки «Синхронизация»,
карточка пользователя → вкладка «Назначения» (индивидуальное назначение активити).

Методы поиска по email и назначения активити — перенос src/ui/locators/admin_users_locators.py
коллеги (репозиторий lms, feature/my-tests) в наш Page Object.
"""
import re
from typing import Optional

from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage
from utils.logger import logger

SYNC_COLUMN_INDEX = 8  # 0 — чекбокс, 1 — ID, 2 — почта, 3 — ФИО, 4 — дата, 5 — Альпина, 6 — МИФ, 7 — тип регистрации, 8 — Синхронизация
BUK_SYNCED_TOOLTIP = "Синхронизирован"


class AdminUsersPage(BasePage):
    PATH = "/admin/users"

    def __init__(self, page: Page):
        super().__init__(page)

    def open(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url}{self.PATH}")
        self.wait_loaded()
        self.page.locator('[data-qa="km-search"]').first.wait_for(state="visible", timeout=30000)

    def search(self, query: str) -> None:
        """Поиск в шапке таблицы. Режим по умолчанию — «ФИО», поэтому ищем по фамилии и имени, не по email."""
        box = self.page.locator('[data-qa="km-search"]').first
        box.fill("")
        box.fill(query)
        self.page.keyboard.press("Enter")
        self.wait_loaded()
        self.page.wait_for_timeout(1500)

    def row_for(self, user: dict) -> Locator:
        """Строка таблицы для пользователя (ищем по ФИО, затем сверяем email в строке)."""
        self.search(f"{user['surname']} {user['name']}")
        row = self.page.locator(f"tr:has-text('{user['email']}')").first
        row.wait_for(state="visible", timeout=15000)
        return row

    def sync_chips(self, row: Locator) -> Locator:
        return row.locator("td").nth(SYNC_COLUMN_INDEX).locator(".sync-chip")

    def sync_chip(self, row: Locator, label: str) -> Locator:
        """Чип колонки «Синхронизация» по подписи: «КАС» или «БУК»."""
        return self.sync_chips(row).filter(has_text=label).first

    def chip_icon_color(self, chip: Locator) -> str:
        return chip.locator(".v-icon").first.evaluate("e => getComputedStyle(e).color")

    # ── Поиск по email и карточка пользователя ──────────────────────────

    @property
    def search_filter_dropdown(self) -> Locator:
        return self.page.locator(
            "xpath=//button[contains(@class,'main-header__btn-dropdown') and .//span[contains(@class,'v-btn__content')]]"
        ).first

    def switch_search_filter_to_email(self) -> None:
        self.search_filter_dropdown.click(timeout=5000)
        email_option = self.page.locator("xpath=//div[@role='menuitem' and .//*[@data-qa='detalization-button__email']]").first
        expect(email_option).to_be_visible(timeout=15000)
        email_option.click(timeout=5000)
        expect(self.page.locator(
            "xpath=//button[contains(@class,'main-header__btn-dropdown') and .//span[contains(normalize-space(),'Email')]]"
        ).first).to_be_visible(timeout=15000)

    def search_by_email(self, email: str) -> None:
        """Переключает фильтр поиска на Email (если ещё не переключён) и ищет пользователя по нему."""
        self.switch_search_filter_to_email()
        box = self.page.locator('[data-qa="km-search"]').first
        box.fill(email, timeout=5000)
        self.page.keyboard.press("Enter")

    def user_row_by_email(self, email: str) -> Locator:
        # develop: email внутри <a><span>…</span></a>; ветка VSHGU2-2378 (vs-table): <a class="vs-table__link">email</a>
        # без span — принимаем оба варианта, чтобы тест не падал ни до, ни после слияния 2378.
        return self.page.locator(
            f"xpath=//tr[.//a[contains(@href,'/admin/users/')]"
            f"[normalize-space()='{email}' or .//span[normalize-space()='{email}']]]"
        )

    def open_user_by_email(self, email: str) -> int:
        row = self.user_row_by_email(email)
        expect(row).to_be_visible(timeout=30000)
        row.locator("a[href*='/admin/users/']").first.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/users/\d+.*"), timeout=15000)
        return int(self.page.url.rstrip("/").split("/")[-1])

    def open_assignments_tab(self) -> None:
        tab = self.page.locator("xpath=//a[contains(@href,'/assigment') and .//span[normalize-space()='Назначения']]")
        expect(tab).to_be_visible(timeout=15000)
        tab.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/users/\d+/assigment.*"), timeout=15000)

    def assignment_row(self, pz_name: str) -> Locator:
        safe = pz_name.replace("'", "")
        return self.page.locator(f"xpath=//tr[.//*[contains(normalize-space(),'{safe}')]]")

    def add_activity_to_user(self, pz_name: str) -> None:
        """Модалка «Добавить Активити» на вкладке «Назначения» карточки пользователя (индивидуальное назначение)."""
        add_button = self.page.get_by_role("button", name="Добавить Активити")
        expect(add_button).to_be_visible(timeout=15000)
        add_button.click(timeout=5000)

        modal = self.page.locator("xpath=//div[contains(@class,'v-dialog__content--active')]")
        # Заголовок модалки используется только чтобы снять фокус с открытого комбобокса —
        # точный текст («Добавить»/«Добавить активити») не важен и может отличаться.
        modal_title = modal.locator("xpath=.//div[contains(@class,'v-card__title')]").first
        expect(modal_title).to_be_visible(timeout=15000)

        select_field = modal.locator(
            "xpath=.//label[normalize-space()='Введите название или выберите из списка']/ancestor::div[contains(@class,'v-input')][1]"
        )
        expect(select_field).to_be_visible(timeout=15000)
        # Без force=True: пока transition открытия модалки не осела, её scrim перехватывает клик.
        select_field.click(timeout=15000)
        self.page.keyboard.type(pz_name, delay=30)
        # debounce поиска — без паузы результат иногда не успевает подгрузиться
        self.page.wait_for_timeout(800)

        safe = pz_name.replace("'", "")
        option = self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
            f"//div[contains(@class,'v-list-item') and .//div[contains(@class,'v-list-item__title') and contains(normalize-space(),'{safe}')]]"
        ).first
        expect(option).to_be_visible(timeout=15000)
        option.click(timeout=5000)

        submit_button = modal.get_by_role("button", name="Добавить")
        expect(submit_button).to_be_enabled(timeout=15000)
        modal_title.click(timeout=3000)
        submit_button.click(timeout=5000)

        expect(self.assignment_row(pz_name)).to_be_visible(timeout=30000)

    def select_region(self, value: str) -> None:
        """Выбрать значение справочника region в поле «Регион» формы создания/редактирования
        пользователя (/admin/users/create) — единственный справочник-select в этой форме,
        см. ui/pages/admin_dictionaries_page.py. В отличие от «Вид программы»/«Стоимостная
        группа» формы потока (admin_programs_page.py) это полноценный поисковый автокомплит:
        ввод текста подсвечивает совпадение (`v-list-item__mask`) и сужает список вплоть до
        единственного пункта — проверено вручную на develop для «Москва»."""
        select_locator = self.page.locator(
            "xpath=//label[normalize-space()='Регион']/ancestor::div[contains(@class,'v-input')][1]"
        )
        expect(select_locator).to_be_visible(timeout=15000)
        select_locator.click(timeout=15000)
        select_locator.locator("input").first.fill(value, timeout=5000)
        # debounce фильтрации списка — без паузы результат иногда не успевает подгрузиться
        self.page.wait_for_timeout(800)

        list_id = select_locator.get_attribute("aria-owns")
        if list_id:
            option = self.page.locator(f"#{list_id} >> xpath=.//div[contains(@class,'v-list-item__content')]").first
        else:
            option = self.page.locator(
                "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
                "//div[contains(@class,'v-list-item__content')]"
            ).first
        expect(option).to_be_visible(timeout=15000)
        option.click(timeout=5000)

    def tooltip_of(self, chip: Locator) -> Optional[str]:
        """Навести курсор на чип и вернуть текст всплывающей подсказки (v-tooltip)."""
        self.page.mouse.move(0, 0)
        self.page.wait_for_timeout(200)
        chip.hover()
        tip = self.page.locator(".v-tooltip__content.menuable__content__active, .v-tooltip__content:visible").first
        try:
            tip.wait_for(state="visible", timeout=5000)
            text = tip.inner_text().strip()
        except Exception:  # noqa: BLE001
            text = None
        logger.info(f"Подсказка чипа «{chip.inner_text().strip()}»: {text!r}")
        return text
