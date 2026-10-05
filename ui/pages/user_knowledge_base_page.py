"""Пользовательская страница «База знаний» (/library): поиск и открытие материала,
прохождение материала (статья/аудио/видео/книга/файл/курс) и страница «Достижения»."""
import re
from urllib.parse import unquote

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect

from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage


class UserKnowledgeBasePage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.sidebar = UserSidebarPage(page)

    def open(self, ui_base_url: str) -> None:
        # UserSidebarPage.open() строит URL относительно текущего page.url — не подходит
        # для свежей страницы (about:blank), поэтому здесь переходим напрямую.
        self.page.goto(f"{ui_base_url.rstrip('/')}/library")
        self.wait_loaded()
        self.sidebar.dismiss_popups()

    def open_catalog(self) -> None:
        catalog_btn = self.page.locator("button.v-btn:has(span:has-text('Каталог'))").first
        if catalog_btn.count() == 0:
            catalog_btn = self.page.locator("button:has-text('Каталог')").first
        expect(catalog_btn).to_be_visible(timeout=15000)
        catalog_btn.click(timeout=5000)
        self.wait_loaded()

    def search(self, query: str) -> None:
        """Заполнить поле поиска и нажать Enter.

        На каталоге с большим числом материалов взаимодействие с поиском нестабильно:
        fill() иногда не долетает до модели (после Enter filter="" в URL), а иногда
        срабатывает какой-то отложенный watcher и перетирает уже применённый фильтр
        обратно на пустой. Печатаем посимвольно и повторяем весь цикл ввод+Enter,
        пока URL действительно не отразит наш запрос."""
        field = self.page.get_by_placeholder("Поиск")
        expect(field).to_be_visible(timeout=15000)
        for _ in range(5):
            field.click(timeout=5000)
            field.fill("", timeout=5000)
            field.press_sequentially(query, timeout=10000)
            if field.input_value() != query:
                self.page.wait_for_timeout(500)
                continue
            self.page.keyboard.press("Enter")
            self.wait_loaded()
            self.page.wait_for_timeout(1000)
            if query in unquote(self.page.url):
                return
        raise AssertionError(f"Поиск не применил фильтр '{query}': url={self.page.url}")

    def material_card(self, name: str):
        card = self.page.locator(f"span.library-card__name:has-text('{name}')").first
        if card.count() == 0:
            card = self.page.get_by_text(name, exact=True).first
        return card

    def open_material(self, name: str) -> None:
        """Открыть материал по имени.

        Только что созданный материал не сразу попадает в поисковый индекс —
        повторяем поиск, если карточка не появилась с первой попытки."""
        card = None
        attempts = 3
        for attempt in range(attempts):
            self.search(name)
            card = self.material_card(name)
            try:
                expect(card).to_be_visible(timeout=15000)
                break
            except AssertionError:
                if attempt == attempts - 1:
                    raise
                self.page.wait_for_timeout(3000)
        card.click(timeout=5000)
        self.wait_loaded()

    def expect_material_title_visible(self, name: str) -> None:
        title = self.page.locator(f"h2.material-header__title:has-text('{name}')")
        expect(title).to_be_visible(timeout=15000)

    # ── Достижения: прохождение материала ───────────────────────────────────

    def open_material_by_id(self, ui_base_url: str, material_id: int, material_name: str) -> None:
        """Открыть карточку материала напрямую по ID — быстрее и надёжнее поиска
        (open_material) для только что созданного через API материала, который ещё
        может не попасть в поисковый индекс.

        Заголовок ищем без exact=True: у материалов типа «курс» отображаемый заголовок —
        это название самого курса Tincan, а не материала БЗ, и на develop оно приходит с
        дополнительным суффиксом (например «..._внешка»), которого нет в имени материала."""
        self.page.goto(f"{ui_base_url.rstrip('/')}/library/material/{material_id}")
        expect(self.page).to_have_url(re.compile(rf".*/library/material/{material_id}$"), timeout=30000)
        expect(self.page.get_by_role("heading", name=material_name)).to_be_visible(timeout=30000)
        self.sidebar.dismiss_popups()

    def read_article_to_end(self, article_name: str) -> None:
        """Открыть статью в модалке и прокрутить её до конца — так фиксируется прочтение."""
        read_button = self.page.get_by_role("button", name="Читать статью", exact=True)
        expect(read_button).to_be_visible(timeout=15000)
        read_button.click(timeout=5000)

        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=15000)
        expect(dialog.get_by_text(article_name, exact=True)).to_be_visible(timeout=15000)

        scroll_container = dialog.locator(".vs-modal__card")
        expect(scroll_container).to_be_visible(timeout=10000)
        box = scroll_container.bounding_box()
        assert box is not None, "Не удалось получить координаты модалки статьи"

        scroll_container.hover()
        self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        is_scrolled_to_end = False
        for _ in range(10):
            self.page.mouse.wheel(0, 1000)
            self.page.wait_for_timeout(300)
            is_scrolled_to_end = scroll_container.evaluate(
                "el => el.scrollTop + el.clientHeight >= el.scrollHeight - 2"
            )
            if is_scrolled_to_end:
                break
        assert is_scrolled_to_end, "Статья не была прокручена до конца"
        self.page.wait_for_timeout(2000)

        close_button = dialog.locator(".vs-modal__close-btn")
        expect(close_button).to_be_visible(timeout=10000)
        close_button.click(timeout=5000)
        expect(dialog).not_to_be_visible(timeout=10000)

    def listen_audio_to_end(self, audio_name: str) -> None:
        """Аудио-плеер встроен в страницу материала сразу (без отдельной кнопки «Слушать»)."""
        audio = self.page.locator("audio")
        expect(audio).to_have_count(1, timeout=15000)
        if self._wait_for_media_duration(audio):
            self._play_media_to_progress(audio, timeout=10000)
        else:
            self._complete_media_with_dom_events(audio)

    def watch_video_to_end(self, video_name: str) -> None:
        """Видеоплеер встроен в страницу материала сразу (без отдельной кнопки «Смотреть»)."""
        video = self.page.locator("video")
        expect(video).to_have_count(1, timeout=15000)
        if self._wait_for_media_duration(video):
            self._play_media_to_progress(video, timeout=15000)
        else:
            self._complete_media_with_dom_events(video)

    def read_book_to_end(self, book_name: str) -> None:
        """Прочитать книгу (PDF) больше чем на 95% — прокруткой PDF-viewer'а."""
        open_book_button = self.page.get_by_text("Открыть книгу", exact=True)
        expect(open_book_button).to_be_visible(timeout=15000)
        open_book_button.click(timeout=5000)

        viewer = self.page.locator("#viewerContainer")
        expect(viewer).to_be_visible(timeout=15000)
        box = viewer.bounding_box()
        assert box is not None, "Не удалось получить координаты PDF-reader"

        viewer.hover()
        self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        read_percent = 0
        for _ in range(80):
            self.page.mouse.wheel(0, 1500)
            self.page.wait_for_timeout(150)
            read_percent = viewer.evaluate(
                "el => ((el.scrollTop + el.clientHeight) / el.scrollHeight) * 100"
            )
            if read_percent >= 96:
                break
        assert read_percent >= 96, f"Книга не была прочитана больше чем на 95% (осталось {read_percent:.1f}%)"
        self.page.wait_for_timeout(5000)

    def download_file(self, file_name: str, attached_file_name: str) -> None:
        """Карточка файла (.file-download) со ссылкой-скачиванием видна на странице материала
        сразу, без отдельной кнопки «Скачать»."""
        file_card = self.page.locator(".file-download").filter(
            has=self.page.get_by_text(attached_file_name, exact=True)
        )
        expect(file_card).to_be_visible(timeout=15000)
        file_link = file_card.locator("a.file-download__link")
        expect(file_link).to_be_visible(timeout=15000)
        file_link.click(timeout=5000)
        self.page.wait_for_timeout(5000)

    def start_course(self, course_name: str) -> None:
        """Открыть курс Tincan, встроенный в материал БЗ: «Приступить к изучению» → popup
        с содержимым курса. В отличие от переноса коллеги, кнопки «Изучать» перед этим на
        текущей версии портала нет — «Приступить к изучению» доступна сразу.

        Само прохождение курса (сценарий вопросов SCORM/Tincan внутри popup) не
        симулируется — это отдельный, самостоятельно нестабильный сценарий (см.
        tests/ui/courses/tincan/*), не относящийся к проверке достижений; фиксация
        прохождения материала для достижения выполняется через API (pass_material_via_api),
        как и для книги/файла (см. память в conftest.py — UI-скролл/чтение не создаёт сетевой
        запрос о прогрессе на этой версии портала)."""
        launch_button = self.page.get_by_text("Приступить к изучению", exact=True)
        expect(launch_button).to_be_visible(timeout=15000)

        with self.page.expect_popup(timeout=30000) as popup_info:
            launch_button.click(timeout=5000)

        course_popup = popup_info.value
        course_popup.wait_for_load_state("domcontentloaded", timeout=30000)
        course_popup.wait_for_timeout(5000)
        course_popup.close()

    def open_achievements(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}/achievements")
        expect(self.page).to_have_url(re.compile(r".*/achievements$"), timeout=30000)
        expect(
            self.page.get_by_role("heading", name="Полученные достижения", exact=True)
        ).to_be_visible(timeout=30000)

    def assert_achievement_received(self, achievement_name: str, achievement_description: str) -> None:
        received_achievements = self.page.locator("section, div").filter(
            has=self.page.get_by_role("heading", name="Полученные достижения", exact=True)
        )
        expect(received_achievements.get_by_text(achievement_name, exact=True)).to_be_visible(timeout=30000)

        achievement_card = self.page.locator(".achievement-cart").filter(
            has=self.page.get_by_text(achievement_name, exact=True)
        )
        expect(achievement_card.get_by_text(achievement_description, exact=True)).to_be_visible(timeout=30000)

    def _wait_for_media_duration(self, media, timeout: int = 30000) -> bool:
        media.evaluate('el => { el.preload = "auto"; el.load(); }')
        try:
            self.page.wait_for_function(
                "el => Number.isFinite(el.duration) && el.duration > 0",
                arg=media.element_handle(),
                timeout=timeout,
            )
            return True
        except PlaywrightTimeoutError:
            return False

    def _play_media_to_progress(self, media, timeout: int) -> None:
        media.evaluate(
            """async el => {
                el.muted = true;
                el._kbProgressReached = false;
                const markProgress = () => {
                    if (Number.isFinite(el.duration) && el.duration > 0 && el.currentTime / el.duration >= 0.9) {
                        el._kbProgressReached = true;
                    }
                };
                el.addEventListener("timeupdate", markProgress);
                el.addEventListener("ended", () => { el._kbProgressReached = true; });
                await el.play();
            }"""
        )
        expect(media).to_have_js_property("paused", False, timeout=5000)
        playback_timeout = int(media.evaluate("el => el.duration") * 1500)
        expect(media).to_have_js_property("_kbProgressReached", True, timeout=max(playback_timeout, timeout))

    def _complete_media_with_dom_events(self, media) -> None:
        media.evaluate(
            """el => {
                el.currentTime = Number.isFinite(el.duration) ? el.duration : 999;
                el.dispatchEvent(new Event("timeupdate", { bubbles: true }));
                el.dispatchEvent(new Event("ended", { bubbles: true }));
            }"""
        )
        self.page.wait_for_timeout(2000)
