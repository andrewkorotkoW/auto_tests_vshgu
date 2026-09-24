"""Пользовательская страница «Техподдержка» (/support): форма создания обращения,
список обращений пользователя, открытие переписки и чтение/отправка сообщений.

Виджет — vue-advanced-chat (классы vac-*), обращения — «тикеты» (классы ticket-*).
Структура проверена вручную через Playwright на --env develop (HEADLESS=1), включая
полный цикл создания через реальную форму (кнопка + -> диалог -> список).

Квирк формы создания: поле «Тема» (категория/request_type) — Vuetify v-select, у его
<input> задан aria-label="Открыть" (это перекрывает подпись поля для get_by_label),
поэтому открывать его нужно кликом по контейнеру комбобокса, а не по лейблу/get_by_label."""
from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage


class TicketsPage(BasePage):
    PATH = "/support"

    def __init__(self, page: Page):
        super().__init__(page)
        self.sidebar = UserSidebarPage(page)

    def open(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATH}")
        self.wait_loaded()
        self.sidebar.dismiss_popups()

    # ---- список обращений пользователя ----

    @property
    def tickets_list(self) -> Locator:
        return self.page.locator("#rooms-list")

    def ticket_titles(self) -> list:
        """Темы (title) обращений, отрисованных в списке сейчас. Список подгружается
        постранично (id="infinite-loader-rooms" внизу, по факту разведки — первая
        порция 15 штук не по дате создания) — на аккаунте с большим числом старых
        обращений свежесозданное может не попасть в эту порцию сразу; тесту может
        понадобиться подождать/перезагрузить страницу перед проверкой."""
        return [t.strip() for t in self.tickets_list.locator(".ticket__room-info--text").all_inner_texts()]

    def ticket_row(self, title: str) -> Locator:
        """Строка обращения по теме (title) среди уже отрисованных (см. ticket_titles)."""
        return self.page.locator(f".vac-room-item:has-text('{title}')").first

    def ticket_status(self, title: str) -> str:
        """"open"/"closed" — CSS-модификатор статуса обращения в списке (по факту
        отображается как «В работе»/«Закрыт», но модификатор класса стабильнее текста)."""
        classes = (self.ticket_row(title).locator(".ticket-status").first.get_attribute("class") or "").split()
        return "closed" if "closed" in classes else "open"

    # ---- создание обращения ----

    def open_create_form(self) -> None:
        self.page.locator(".vac-add-icon").first.click()
        expect(self.page.get_by_label("Название тикета", exact=True)).to_be_visible(timeout=15000)

    def select_category(self, category: str) -> None:
        """Выбрать категорию (поле «Тема», обязательно для отправки). У поля combobox
        input aria-label="Открыть" — открываем клик по контейнеру, не по лейблу."""
        self.page.locator("div[role=combobox]:has(label:text-is('Тема'))").first.click()
        option = self.page.get_by_role("option", name=category)
        expect(option).to_be_visible(timeout=10000)
        option.click()

    def fill_create_form(self, title: str, text: str, category: str = None) -> None:
        self.page.get_by_label("Название тикета", exact=True).fill(title)
        if category:
            self.select_category(category)
        self.page.get_by_label("Текст обращения", exact=True).fill(text)

    def submit_create_form(self) -> None:
        self.page.locator("button[type=submit]:has-text('Создать тикет')").click()

    def create_ticket(self, title: str, text: str, category: str) -> None:
        """Полный цикл: открыть форму, заполнить тему/текст/категорию, отправить."""
        self.open_create_form()
        self.fill_create_form(title, text, category=category)
        self.submit_create_form()

    # ---- переписка ----

    def open_ticket(self, title: str) -> None:
        """Открыть переписку по обращению с заданной темой."""
        row = self.ticket_row(title)
        expect(row).to_be_visible(timeout=15000)
        row.click(force=True)
        expect(self.page.locator(".chat__content-roominfo-title")).to_have_text(title, timeout=15000)
        # сообщения подгружаются отдельным GET уже после отрисовки шапки переписки
        expect(self.page.locator(".vac-message-wrapper").first).to_be_visible(timeout=15000)

    def message_texts(self) -> list:
        """Тексты всех сообщений в открытой переписке, в порядке отображения (старые
        сверху) — один элемент списка на одно сообщение (.vac-format-message-wrapper,
        не .vac-format-container: markdown-рендер чата дробит текст на несколько
        .vac-format-container внутри одного сообщения, если в нём есть "_" — трактует
        их как разметку курсива и вырезает при отображении, поэтому сравнивать с
        исходным текстом сообщения, содержащим "_", напрямую нельзя)."""
        return [t.strip() for t in self.page.locator(".vac-message-wrapper .vac-format-message-wrapper").all_inner_texts()]

    def send_message(self, text: str) -> None:
        """Отправить сообщение в открытой переписке (доступно только для открытого
        обращения — у закрытого форма ввода скрыта)."""
        textarea = self.page.locator("#roomTextarea")
        expect(textarea).to_be_visible(timeout=15000)
        textarea.click()
        textarea.type(text)
        send_button = self.page.locator("#room-footer .vac-svg-button:not(.vac-send-disabled)").last
        send_button.click()
