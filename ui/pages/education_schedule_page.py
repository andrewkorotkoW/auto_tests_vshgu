"""«Моё обучение» слушателя: карточка программы → расписание модуля → мероприятие
«МТС Линк» → ссылка на вебинар.

Подтверждено живьём 12.11.2026 (mts-link-release-main, реальный прод-аккаунт): ссылка в
карточке мероприятия — настоящий <a href="https://my.mts-link.ru/..." target="_blank">,
обычный клик (без force) открывает её в новой вкладке — так и устроено в реальном DOM
(проверено prepared_user + Playwright, без force=True)."""
from playwright.sync_api import Page, expect

from config.settings import settings
from ui.pages.base_page import BasePage


class EducationSchedulePage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def open_program(self, program_name: str) -> None:
        """«Моё обучение» → карточка программы по названию."""
        self.page.goto(f"{settings.UI_BASE_URL}/education")
        self.wait_loaded()
        card = self.page.locator(f"text={program_name}").first
        expect(card).to_be_visible(timeout=settings.UI_TIMEOUT)
        card.click(timeout=settings.UI_TIMEOUT)
        self.wait_loaded()

    def open_schedule_item(self, event_name: str) -> None:
        """Карточка мероприятия в расписании модуля по названию — открывает детальную
        панель с преподавателем, датой/временем и ссылкой на вебинар."""
        item = self.page.locator(f"text={event_name}").first
        expect(item).to_be_visible(timeout=settings.UI_TIMEOUT)
        item.click(timeout=settings.UI_TIMEOUT)

    def click_join_link_and_get_new_page(self):
        """Кликает по ссылке на вебинар (target=_blank) и возвращает открывшуюся вкладку."""
        link = self.page.locator('a[href*="mts-link.ru"]').first
        expect(link).to_be_visible(timeout=settings.UI_TIMEOUT)
        with self.page.context.expect_page(timeout=10000) as new_page_info:
            link.click(timeout=settings.UI_TIMEOUT)
        return new_page_info.value
