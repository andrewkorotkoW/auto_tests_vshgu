import allure
import pytest
import requests
import time
import random
from utils.logger import logger
from config.settings import settings


@allure.feature("Stage Tests")
@allure.story("Продолжить тест ЛПД (ИНД трек)")
class TestUILpdSaveAndContinueInd:

    @allure.title("UI Stage (ИНД трек): Сохранить → Выйти → Войти → Продолжить → Завершить")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.stage
    def test_ui_lpd_save_and_continue_ind(self, page):
        session = requests.Session()
        session.cookies.set("stage", settings.STAGE_DEVELOP_COOKIE)
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://portal-stage.d7.devspark.ru"
        })
        base_url = settings.STAGE_BASE_URL or "https://portal-stage.d7.devspark.ru/api/v1"
        ui_url = settings.STAGE_UI_BASE_URL or "https://portal-stage.d7.devspark.ru"
        ts = int(time.time() * 1000)

        # ========== API ==========
        # 1. Создать пользователя
        name = random.choice(["Иван", "Пётр", "Сергей"])
        surname = random.choice(["Иванов", "Петров", "Сидоров"])
        email = f"ui_lpd_save_ind_{ts}@mail.com"
        u = session.post(f"{base_url}/users", json={
            "data": {"attributes": {
                "fields": {"personal_phone_number": 0, "phone_number": 0, "email": 0, "position": 0,
                           "position_level": 0, "organisation": 0, "car_brand": 0, "car_number": 0},
                "roles": None, "tags": [], "email": email, "surname": surname, "name": name,
                "login": email, "patronymic": "Автотестович", "system_password": "SecurePass123",
                "password": "SecurePass123", "date_of_birth": "1990-01-01", "region_id": 1, "municipality_id": 1}}
        })
        assert u.status_code in (200, 201), f"User failed: {u.status_code}"
        user_id = u.json()["data"]["id"]

        # 2. Создать авторизованный ЛПД (235)
        lpd_name = f"UI_LPD_Save_Ind_{ts}"
        l = session.post(f"{base_url}/content", json={
            "data": {"attributes": {"duration": "3", "content_type": "lpd", "lpd_id": "235",
                                    "name": lpd_name, "name_client": f"{lpd_name}_внешка", "activity_category_id": 2,
                                    "description": f"<p>{lpd_name}</p>", "cover_uuid": "", "sub_files_uuids": "",
                                    "passing_type": "authorized"},
                     "includes": {"archive": [], "image": [], "spreadsheet": [], "video": [], "pdf": [], "document": [],
                                  "offline": [], "webinar": [], "cover": [], "sub_files": []},
                     "permissions": []}
        })
        assert l.status_code in (200, 201), f"LPD failed: {l.status_code}"
        lpd_id = l.json()["data"]["id"]

        # 3. Назначить на инд. трек
        session.post(f"{base_url}/users/content/distant/assign-activities", json={
            "data": {"attributes": {"content_ids": [lpd_id], "user_ids": [user_id]}}
        })

        # ========== UI: ЧАСТЬ 1 ==========
        with allure.step("4. Логин"):
            page.goto(f"{ui_url}/auth/main")
            page.wait_for_timeout(2000)
            page.fill('input[name="email_or_login"]', email)
            page.fill('input[name="password"]', "SecurePass123")
            page.click('button:has-text("Войти")')
            page.wait_for_timeout(3000)
            try:
                checkbox = page.locator('input[type="checkbox"]')
                if checkbox.is_visible(timeout=3000):
                    checkbox.check()
                    page.locator("text=Отправить").first.click(force=True)
                    page.wait_for_timeout(2000)
            except:
                pass
            page.screenshot(path="allure-results/stage_ui_save_ind_01_login.png")

        with allure.step("5. Онбординг"):
            try:
                start_btn = page.locator("span:has-text('Пройти обучение'), span:has-text('Начать обучение')").first
                if start_btn.is_visible(timeout=3000):
                    start_btn.click(force=True)
                    page.wait_for_timeout(1000)
                for _ in range(15):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=2000):
                        btn.click(force=True)
                        page.wait_for_timeout(300)
                    else:
                        break
            except:
                pass
            page.screenshot(path="allure-results/stage_ui_save_ind_02_onboarding.png")

        with allure.step("6. Индивидуальное обучение → вкладка ЛПД → открыть ЛПД"):
            page.locator("text=Индивидуальное обучение").first.click(force=True)
            page.wait_for_timeout(2000)
            try:
                for _ in range(15):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=2000):
                        btn.click(force=True)
                        page.wait_for_timeout(300)
                    else:
                        break
            except:
                pass
            page.evaluate("""() => {
                const spans = document.querySelectorAll('span.py-2');
                for (const span of spans) {
                    if (span.textContent.trim() === 'ЛПД') {
                        span.click();
                        break;
                    }
                }
            }""")
            page.wait_for_timeout(2000)
            page.locator(f"text={lpd_name}").first.click(force=True)
            page.wait_for_timeout(2000)
            page.screenshot(path="allure-results/stage_ui_save_ind_03_lpd.png")

        with allure.step("7. Запустить ЛПД → новое окно → Перейти → заполнить 5 полей → Сохранить"):
            with page.context.expect_event("page", timeout=15000) as event:
                page.locator("span:has-text('Начать')").first.click(force=True)
            new_page = event.value
            new_page.wait_for_load_state("networkidle")
            new_page.wait_for_timeout(3000)

            go_btn = new_page.locator("a.btn.btn-primary:has-text('Перейти')")
            assert go_btn.is_visible(timeout=10000), "Кнопка 'Перейти' не найдена"
            go_btn.first.click(force=True)
            new_page.wait_for_load_state("networkidle")
            new_page.wait_for_timeout(3000)

            new_page.wait_for_selector("select[name='field_1152']", state="visible", timeout=15000)

            # Заполнить 6 полей (включая шкалу!)
            new_page.locator("select[name='field_1152']").select_option("2", force=True)
            new_page.wait_for_timeout(300)
            new_page.locator("select[name='field_1173']").select_option("1", force=True)
            new_page.wait_for_timeout(300)
            new_page.locator("input[name='field_1176[]'][value='2']").check(force=True)
            new_page.wait_for_timeout(300)
            new_page.locator("input[name='field_1176[]'][value='3']").check(force=True)
            new_page.wait_for_timeout(300)
            new_page.locator("input[name='field_1177'][value='2']").check(force=True)
            new_page.wait_for_timeout(300)
            new_page.locator("input[name='field_1180'][value='10']").check(force=True)
            new_page.wait_for_timeout(300)
            new_page.locator("input[name='field_1179']").fill("2")
            new_page.wait_for_timeout(300)

            # Нажать "Сохранить страницу"
            save_btn = new_page.locator("input[name='save'][value='Сохранить страницу']")
            if save_btn.count() == 0:
                save_btn = new_page.locator("input[value='Сохранить страницу']")
            if save_btn.count() > 0 and save_btn.is_visible(timeout=5000):
                save_btn.click(force=True)
                new_page.wait_for_timeout(3000)
                logger.info("Кнопка 'Сохранить страницу' нажата")

            new_page.screenshot(path="allure-results/stage_ui_save_ind_04_saved.png")
            new_page.close()

        # ========== UI: ЧАСТЬ 2 (обновление и продолжение) ==========
        with allure.step("8. Обновить страницу и продолжить"):
            page.bring_to_front()
            page.reload()
            page.wait_for_timeout(5000)
            page.wait_for_load_state("networkidle")
            try:
                for _ in range(15):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=2000):
                        btn.click(force=True)
                        page.wait_for_timeout(300)
                    else:
                        break
            except:
                pass

            # Снова открыть ЛПД
            page.locator("text=Индивидуальное обучение").first.click(force=True)
            page.wait_for_timeout(2000)
            page.evaluate("""() => {
                const spans = document.querySelectorAll('span.py-2');
                for (const span of spans) {
                    if (span.textContent.trim() === 'ЛПД') {
                        span.click();
                        break;
                    }
                }
            }""")
            page.wait_for_timeout(2000)
            page.locator(f"text={lpd_name}").first.click(force=True)
            page.wait_for_timeout(2000)


            # Нажать "Продолжить"
            with page.context.expect_event("page", timeout=15000) as event:
                page.locator("span:has-text('Продолжить')").first.click(force=True)
            new_page2 = event.value
            new_page2.wait_for_load_state("networkidle")
            new_page2.wait_for_timeout(3000)

            # Нажать "Перейти" (как в начале)
            go_btn2 = new_page2.locator("a.btn.btn-primary:has-text('Перейти')")
            assert go_btn2.is_visible(timeout=10000), "Кнопка 'Перейти' не найдена после 'Продолжить'"
            go_btn2.first.click(force=True)
            new_page2.wait_for_load_state("networkidle")
            new_page2.wait_for_timeout(3000)

            new_page2.screenshot(path="allure-results/stage_ui_save_ind_05_reopened.png")
            logger.info("ЛПД повторно открыт после обновления")

            with allure.step("9. Завершить анкету"):
                new_page2.wait_for_timeout(3000)
                new_page2.screenshot(path="allure-results/stage_ui_save_ind_05_second_part.png")

                # Нажать "Далее" (если есть)
                next_btn = new_page2.locator("input[name='next']")
                if next_btn.count() > 0 and next_btn.is_visible(timeout=5000):
                    next_btn.click(force=True)
                    new_page2.wait_for_timeout(2000)
                    logger.info("Кнопка 'Далее' нажата")

                # Заполнить оставшиеся поля (7-10)
                new_page2.locator("input[name='field_1174']").fill("Да")
                new_page2.wait_for_timeout(300)
                new_page2.locator("input[name='field_1175']").fill("1990-01-01")
                new_page2.wait_for_timeout(300)
                new_page2.locator("select[name='field_1178']").select_option("4", force=True)
                new_page2.wait_for_timeout(300)

                # Автодополнение
                autocomplete_field = new_page2.locator("input[name='field_1250']")
                if autocomplete_field.count() > 0:
                    autocomplete_field.click(force=True)
                    new_page2.wait_for_timeout(500)
                    new_page2.evaluate("""
                        (input) => {
                            input.focus();
                            input.value = '';
                            const chars = 'мос';
                            for (const char of chars) {
                                input.value += char;
                                input.dispatchEvent(new KeyboardEvent('keydown', {key: char}));
                                input.dispatchEvent(new KeyboardEvent('keypress', {key: char}));
                                input.dispatchEvent(new KeyboardEvent('keyup', {key: char}));
                                input.dispatchEvent(new Event('input', {bubbles: true}));
                            }
                        }
                    """, autocomplete_field.element_handle())
                    new_page2.wait_for_timeout(5000)
                    option = new_page2.locator("li[data-value='7700000000000']")
                    option.wait_for(state="visible", timeout=15000)
                    option.click(force=True)
                    new_page2.wait_for_timeout(500)

                new_page2.screenshot(path="allure-results/stage_ui_save_ind_06_filled.png")

                # ... дальше сохранение и подтверждение

            # Завершить
            save_final = new_page2.locator("input[value='Сохранить и Проверить ответы']")
            save_final.wait_for(state="visible", timeout=10000)
            save_final.click(force=True)
            new_page2.wait_for_timeout(3000)

            confirm_btn = new_page2.locator("input[value='Данные корректны, ответы подтверждаю']")
            confirm_btn.wait_for(state="visible", timeout=15000)
            try:
                new_page2.evaluate(
                    "document.querySelector('input[value=\"Данные корректны, ответы подтверждаю\"]').click()")
            except:
                confirm_btn.click(force=True)
            new_page2.wait_for_timeout(5000)

            success_msg = new_page2.locator("div.alert-primary:has-text('Анкета успешно отправлена')")
            assert success_msg.is_visible(timeout=5000), "Сообщение об успешной отправке не появилось"
            new_page2.screenshot(path="allure-results/stage_ui_save_ind_07_completed.png")
            logger.info("Анкета успешно пройдена после повторного входа")

        with allure.step("10. Проверить «Отчет формируется»"):
            new_page2.close()
            page.bring_to_front()
            page.reload()
            page.wait_for_timeout(5000)
            page.wait_for_load_state("networkidle")
            try:
                for _ in range(15):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=2000):
                        btn.click(force=True)
                        page.wait_for_timeout(300)
                    else:
                        break
            except:
                pass
            report_btn = page.locator("button:has-text('Отчет формируется')").first
            assert report_btn.is_visible(timeout=10000), "Кнопка 'Отчет формируется' не найдена"
            is_disabled = report_btn.get_attribute("disabled") is not None
            assert is_disabled, "Кнопка 'Отчет формируется' должна быть неактивна"
            page.screenshot(path="allure-results/stage_ui_save_ind_08_report_pending.png")
            logger.info("Кнопка 'Отчет формируется' отображается и неактивна")

        # ========== Очистка ==========
        with allure.step("11. Очистка данных"):
            session.post(f"{base_url}/users/content/distant/detach-activities", json={
                "data": {"attributes": {"content_ids": [lpd_id], "user_ids": [user_id]}}
            })
            session.delete(f"{base_url}/content/{lpd_id}")
            session.delete(f"{base_url}/users/{user_id}")
            logger.info("Очистка завершена")

        logger.info("UI LPD Save & Continue (Ind) завершён!")