import allure
import pytest
import requests
import time
import random
from utils.logger import logger
from config.settings import settings


@allure.feature("Stage Tests")
@allure.story("UI LPD Stage (Auth)")
class TestUILpdStageAuth:

    @allure.title("UI Stage: Создание → Логин → Онбординг → Инд.трек → ЛПД (auth) → Анкета → Отчет")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.stage
    def test_ui_lpd_auth_flow(self, page):
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
        email = f"ui_lpd_auth_{ts}@mail.com"
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
        lpd_name = f"UI_LPD_AUTH_{ts}"
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

        # ========== UI ==========
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
            page.screenshot(path="allure-results/stage_ui_auth_01_login.png")
            allure.attach.file("allure-results/stage_ui_auth_01_login.png", "Логин", allure.attachment_type.PNG)

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
            page.screenshot(path="allure-results/stage_ui_auth_02_onboarding.png")
            allure.attach.file("allure-results/stage_ui_auth_02_onboarding.png", "Онбординг",
                               allure.attachment_type.PNG)

        with allure.step("6. Индивидуальное обучение → вкладка ЛПД"):
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
            logger.info("Вкладка 'ЛПД' выбрана")

            page.locator(f"text={lpd_name}").first.click(force=True)
            page.wait_for_timeout(2000)
            page.screenshot(path="allure-results/stage_ui_auth_03_lpd.png")
            allure.attach.file("allure-results/stage_ui_auth_03_lpd.png", "ЛПД открыт", allure.attachment_type.PNG)
            logger.info(f"ЛПД '{lpd_name}' открыт")

        with allure.step("7. Запустить ЛПД и перехватить новое окно"):
            with page.context.expect_event("page", timeout=15000) as event:
                page.locator("span:has-text('Начать')").first.click(force=True)
            new_page = event.value
            new_page.wait_for_load_state("networkidle")
            new_page.wait_for_timeout(3000)
            new_page.screenshot(path="allure-results/stage_ui_auth_04_launched.png")
            allure.attach.file("allure-results/stage_ui_auth_04_launched.png", "Новое окно ЛПД",
                               allure.attachment_type.PNG)
            logger.info(f"URL нового окна: {new_page.url}")

        with allure.step("8. Нажать «Перейти» (в новом окне)"):
            go_btn = new_page.locator("a.btn.btn-primary:has-text('Перейти')")
            assert go_btn.is_visible(timeout=10000), "Кнопка 'Перейти' не найдена"
            go_btn.first.click(force=True)
            new_page.wait_for_load_state("networkidle")
            new_page.wait_for_timeout(3000)
            new_page.screenshot(path="allure-results/stage_ui_auth_05_anketa_opened.png")
            allure.attach.file("allure-results/stage_ui_auth_05_anketa_opened.png", "Анкета открыта",
                               allure.attachment_type.PNG)
            logger.info("Кнопка 'Перейти' нажата")

        with allure.step("9. Прохождение анкеты"):
            # Ждать появления первого select
            new_page.wait_for_selector("select[name='field_1152']", state="visible", timeout=15000)

            new_page.screenshot(path="allure-results/stage_ui_auth_05_before_answers.png")
            allure.attach.file("allure-results/stage_ui_auth_05_before_answers.png", "До выбора ответов",
                               allure.attachment_type.PNG)

            # 1. Самочувствие — хорошее (value=2)
            new_page.locator("select[name='field_1152']").select_option("2", force=True)
            new_page.wait_for_timeout(300)
            logger.info("1/10: Самочувствие — хорошее")

            # 2. Да/Нет — Да (value=1)
            new_page.locator("select[name='field_1173']").select_option("1", force=True)
            new_page.wait_for_timeout(300)
            logger.info("2/10: Да/Нет — Да")

            # 3. Флажки — оба (value=2 и value=3)
            new_page.locator("input[name='field_1176[]'][value='2']").check(force=True)
            new_page.wait_for_timeout(300)
            new_page.locator("input[name='field_1176[]'][value='3']").check(force=True)
            new_page.wait_for_timeout(300)
            logger.info("3/10: Флажки отмечены")

            # 4. Radio "Не очень" (value=2)
            new_page.locator("input[name='field_1177'][value='2']").check(force=True)
            new_page.wait_for_timeout(300)
            logger.info("4/10: Radio — Не очень")

            # 5. Шкала — 10 (value=10)
            new_page.locator("input[name='field_1180'][value='10']").check(force=True)
            new_page.wait_for_timeout(300)
            logger.info("5/10: Шкала — 10")

            # 6. Числовое поле — 5
            new_page.locator("input[name='field_1179']").fill("5")
            new_page.wait_for_timeout(300)
            logger.info("6/10: Числовое поле — 5")

            # ===== НАЖАТЬ "ДАЛЕЕ" =====
            next_btn = new_page.locator("input[name='next']")
            if next_btn.count() > 0 and next_btn.is_visible(timeout=3000):
                next_btn.click(force=True)
                new_page.wait_for_timeout(2000)
                logger.info("Кнопка 'Далее' нажата")

            # 7. Текстовое поле — "Да"
            new_page.locator("input[name='field_1174']").fill("Да")
            new_page.wait_for_timeout(300)
            logger.info("7/10: Текстовое поле — Да")

            # 8. Дата — 1990-01-01
            new_page.locator("input[name='field_1175']").fill("1990-01-01")
            new_page.wait_for_timeout(300)
            logger.info("8/10: Дата — 1990-01-01")

            # 9. Выпадающий список — Молодёжная политика (value=4)
            new_page.locator("select[name='field_1178']").select_option("4", force=True)
            new_page.wait_for_timeout(300)
            logger.info("9/10: Select — Молодёжная политика")

            # 10. Автодополнение — г Москва
            autocomplete_field = new_page.locator("input[name='field_1250']")
            if autocomplete_field.count() > 0:
                autocomplete_field.click(force=True)
                new_page.wait_for_timeout(500)

                # Ввести "мос" через диспетчеризацию событий (как ручной ввод)
                new_page.evaluate("""
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
                new_page.wait_for_timeout(5000)

                option = new_page.locator("li[data-value='7700000000000']")
                option.wait_for(state="visible", timeout=15000)
                option.click(force=True)
                new_page.wait_for_timeout(500)
                logger.info("10/10: Автодополнение — г Москва: Выбрана ")

            # 11 Сохранить и Проверить ответы
            save_btn = new_page.locator("input[value='Сохранить и Проверить ответы']")
            save_btn.wait_for(state="visible", timeout=10000)
            save_btn.click(force=True)
            new_page.wait_for_timeout(3000)

            # 12 Данные корректны, ответы подтверждаю
            confirm_btn = new_page.locator("input[value='Данные корректны, ответы подтверждаю']")
            confirm_btn.wait_for(state="visible", timeout=15000)
            try:
                new_page.evaluate(
                    "document.querySelector('input[value=\"Данные корректны, ответы подтверждаю\"]').click()")
            except:
                confirm_btn.click(force=True)
            new_page.wait_for_timeout(5000)

            # Проверить успех
            success_msg = new_page.locator("div.alert-primary:has-text('Анкета успешно отправлена')")
            assert success_msg.is_visible(timeout=5000), "Сообщение об успешной отправке не появилось"
            new_page.screenshot(path="allure-results/stage_ui_auth_07_anketa_completed.png")
            allure.attach.file("allure-results/stage_ui_auth_07_anketa_completed.png", "Анкета пройдена",
                               allure.attachment_type.PNG)
            logger.info("Анкета успешно пройдена")

        with allure.step("10. Проверить статус «Отчет формируется»"):
            new_page.close()
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
            page.screenshot(path="allure-results/stage_ui_auth_08_report_pending.png")
            allure.attach.file("allure-results/stage_ui_auth_08_report_pending.png", "Отчет формируется",
                               allure.attachment_type.PNG)
            logger.info("Кнопка 'Отчет формируется' отображается и неактивна")

        # ========== Очистка ==========
        with allure.step("11. Очистка данных"):
            resp_detach = session.post(f"{base_url}/users/content/distant/detach-activities", json={
                "data": {"attributes": {"content_ids": [lpd_id], "user_ids": [user_id]}}
            })
            if resp_detach.status_code in (200, 201):
                logger.info("Назначение снято")
            else:
                logger.warning(f"Снятие назначения: {resp_detach.status_code} {resp_detach.text}")

            resp_lpd = session.delete(f"{base_url}/content/{lpd_id}")
            if resp_lpd.status_code in (200, 204):
                logger.info("LPD удалён")
            else:
                logger.warning(f"Удаление LPD: {resp_lpd.status_code} {resp_lpd.text}")

            resp_user = session.delete(f"{base_url}/users/{user_id}")
            if resp_user.status_code in (200, 204):
                logger.info("Пользователь удалён")
            else:
                logger.warning(f"Удаление пользователя: {resp_user.status_code} {resp_user.text}")

            logger.info("Очистка завершена")

