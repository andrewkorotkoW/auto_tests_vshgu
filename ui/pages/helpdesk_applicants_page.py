"""Админка хелпдеска → «Заявители» (/admin/identity, docs/helpdesk_recon.md,
кейсы 9606-9611): список, добавление заявителя, карточка заявителя (статистика,
назначения программ/активити) и переход в карточку пользователя ВШГУ.

Карточка заявителя (/admin/identity/{id}/show) — самый богатый раздел: блоки
«Информация о заявителе», «Связанные» (email), «Статистика», «Назначения»
(«Программы и потоки» + «Активити», каждый со своей кнопкой «Управление
обучением»), «Тикеты». Кнопка «Управление обучением» у блока «Программы и
потоки» уводит на другой домен — `global-develop.d2.devspark.ru`, вкладка
«Обучение» карточки пользователя ВШГУ (кейс 9611).

«Управление обучением» в реальной разметке — `<a href="..." target="_blank">`
(не `<button>`), 2 совпадения на странице (у «Программы и потоки» и у
«Активити» — нужен именно первый, `.first`); ссылка открывает НОВУЮ вкладку
браузера, а не навигацию в текущей — ловим её через `context.expect_page()`,
а не `page.expect_navigation()` (подтверждено Playwright на develop)."""
from playwright.sync_api import expect

from ui.pages.helpdesk_base_page import HelpdeskAdminPage


class HelpdeskApplicantsPage(HelpdeskAdminPage):
    PATH = "/admin/identity"

    def fill_create_form(self, payload: dict) -> None:
        """payload — как из generate_helpdesk_applicant_payload():
        surname/name/patronymic/email/phone (+ опционально stream_id/user_id)."""
        self.page.get_by_label("Фамилия", exact=True).fill(payload["surname"])
        self.page.get_by_label("Имя", exact=True).fill(payload["name"])
        self.page.get_by_label("Отчество", exact=True).fill(payload["patronymic"])
        self.page.get_by_label("Email", exact=True).fill(payload["email"])
        self.page.get_by_label("Номер телефона", exact=True).fill(payload["phone"])

    def add_applicant(self, payload: dict) -> None:
        """Полный цикл: открыть форму «Добавить заявителя», заполнить, сохранить
        (кнопка «Сохранить и предпросмотр» ведёт сразу на карточку заявителя)."""
        self.open_create_form()
        self.fill_create_form(payload)
        self.submit_form()

    def open_show_page(self, ui_base_url: str, applicant_id: int) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATH}/{applicant_id}/show")
        self.wait_loaded()

    def go_to_vshgu_user_education(self):
        """На уже открытой карточке заявителя — переход по ссылке «Управление
        обучением» у блока «Программы и потоки» (первая из двух одноимённых
        ссылок на странице, вторая — у блока «Активити») в карточку
        пользователя ВШГУ, вкладка «Обучение» (другой домен —
        global-develop.d2.devspark.ru, см. docs/helpdesk_recon.md, кейс 9611).
        Ссылка открывается в НОВОЙ вкладке (target=_blank) — возвращает
        Playwright Page этой вкладки (её URL проверяет вызывающий тест)."""
        link = self.page.get_by_role("link", name="Управление обучением").first
        with self.page.context.expect_page() as new_page_info:
            link.click()
        new_page = new_page_info.value
        new_page.wait_for_load_state("networkidle")
        return new_page
