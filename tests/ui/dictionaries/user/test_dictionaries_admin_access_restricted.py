"""UI: раздел «Справочники» в админке (/admin/catalogs/*) недоступен обычному слушателю.

second_user_page — реально другой пользователь без ролей admin/manager (см.
conftest.py::second_user_page), а не user_page — на develop user_page/admin_page это
один и тот же аккаунт (roles admin+manager, README §13/§14), поэтому проверить
ограничение на нём нельзя. Согласуется с API-моделью прав, разведанной в
tests/api/dictionaries (README §14 «Модель прав»): чтение справочника открыто любому
авторизованному, запись — только админу.

Разведано вручную (ad-hoc pytest-скрипт, до написания этого теста): прямой переход
обычного пользователя на /admin/catalogs/programs детерминированно редиректит на
/programs (SPA-роутер не пускает в раздел «Админка» целиком), а не показывает
таблицу справочника в режиме только для чтения — поэтому здесь достаточно проверить
редирект, отдельный сценарий «доступен для чтения, но без кнопок CRUD» недостижим.
"""
import allure
import pytest


@allure.feature("Справочники UI")
@allure.story("Права доступа")
@pytest.mark.ui
@pytest.mark.dictionaries
class TestDictionariesAdminAccessRestricted:

    @allure.title("Обычный пользователь не может открыть каталог справочника в админке — редирект из /admin")
    def test_regular_user_redirected_away_from_dictionaries_catalog(self, second_user_page, env):
        with allure.step("Перейти напрямую на /admin/catalogs/programs под обычным пользователем"):
            # wait_until="domcontentloaded", а не дефолтный "load": SPA продолжает
            # держать сеть активной (поллинг/долгоживущие запросы) и событие "load"
            # не всегда успевает наступить за 30с — надёжнее дождаться самого DOM,
            # а не полной тишины сети.
            second_user_page.goto(f"{env.ui_base_url}/admin/catalogs/programs", wait_until="domcontentloaded")
            second_user_page.wait_for_timeout(4000)

        assert "/admin" not in second_user_page.url, (
            f"Обычный пользователь остался в разделе админки: {second_user_page.url}"
        )
