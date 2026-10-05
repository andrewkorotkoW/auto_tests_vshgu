import allure
import pytest

from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage, SIDEBAR_BUTTONS, OPTIONAL_EXTERNAL_BUTTONS
from utils.logger import logger

INTERNAL = list(SIDEBAR_BUTTONS.items())


@pytest.fixture
def logged_in_user(page, env, created_user):
    """API: создать пользователя → UI: войти по его email/паролю через форму → закрыть попапы."""
    user = created_user()
    logger.info(f"Пользователь: id={user['id']} {user['email']}")
    LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
    sidebar = UserSidebarPage(page)
    sidebar.dismiss_popups()
    return user, sidebar


@allure.feature("UI Tests")
@allure.story("User login and navigation")
class TestUserLoginNavigation:

    @allure.title("Вход по email и паролю пользователя: сессия открыта, в шапке его ФИО")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_login_with_user_credentials(self, page, env, logged_in_user):
        user, sidebar = logged_in_user
        with allure.step("После входа мы не на странице авторизации"):
            assert "/auth" not in page.url, page.url
            page.screenshot(path="allure-results/user_login_01.png")
            allure.attach.file("allure-results/user_login_01.png", "После входа", allure.attachment_type.PNG)
        with allure.step("В шапке отображается ФИО пользователя"):
            header = sidebar.user_name()
            assert user["surname"] in header and user["name"] in header, header
        with allure.step("Раздел «Мое обучение» открывается"):
            sidebar.open("/education")
            assert not sidebar.is_404(), "Страница /education отдала 404"

    @allure.title("В боковом меню отображаются кнопки пользователя с правильными ссылками")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_sidebar_buttons_displayed(self, page, env, logged_in_user):
        user, sidebar = logged_in_user
        sidebar.open("/education")
        page.screenshot(path="allure-results/user_sidebar.png")
        allure.attach.file("allure-results/user_sidebar.png", "Боковое меню", allure.attachment_type.PNG)
        missing = []
        for label, href in SIDEBAR_BUTTONS.items():
            with allure.step(f"Кнопка «{label}» → {href}"):
                btn = sidebar.button(label)
                if not btn.is_visible(timeout=5000):
                    missing.append(label)
                    continue
                actual = btn.get_attribute("href") or ""
                assert href in actual, f"«{label}»: ожидали ссылку с {href}, получили {actual}"
        assert not missing, f"Не отображаются кнопки: {missing}"
        for label, href in OPTIONAL_EXTERNAL_BUTTONS.items():
            with allure.step(f"Необязательная внешняя кнопка «{label}»"):
                btn = sidebar.button(label)
                if btn.is_visible(timeout=1500):
                    actual = btn.get_attribute("href") or ""
                    assert href in actual and actual.startswith("https://"), f"«{label}»: {actual}"
                    logger.info(f"«{label}» → {actual}")
                else:
                    logger.info(f"«{label}» у этого пользователя не показывается — пропуск")

    @allure.title("Переход по кнопкам меню: {label} → {href}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.parametrize("label,href", INTERNAL, ids=[h.strip("/") for _, h in INTERNAL])
    def test_navigate_by_sidebar_button(self, page, env, logged_in_user, label, href):
        user, sidebar = logged_in_user
        sidebar.open("/education")
        with allure.step(f"Нажать «{label}»"):
            sidebar.go(label)
            page.wait_for_url(f"**{href}**", timeout=15000)
        with allure.step("Открылся нужный раздел, без 404, пользователь тот же"):
            assert href in page.url, page.url
            assert not sidebar.is_404(), f"«{label}» привела на 404"
            assert user["surname"] in sidebar.user_name()
            page.screenshot(path=f"allure-results/user_nav_{href.strip('/')}.png")
            allure.attach.file(f"allure-results/user_nav_{href.strip('/')}.png", label, allure.attachment_type.PNG)
