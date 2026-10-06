import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_applicant_payload


@allure.feature("Хелпдеск: Заявители")
@allure.story("Поиск и добавление заявителя")
class TestApplicantsApi:

    @allure.title("POST /admin/identity/search по email — домен не ищется, полный адрес находит заявителя")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_search_applicant_by_email(self, helpdesk_endpoint):
        # У /admin/identity нет маршрута DELETE (docs/helpdesk_recon.md §2) — созданный
        # auto_test_* заявитель остаётся в системе, удаление не предусмотрено инфраструктурой.
        #
        # Исходное предположение разведки («поиск по email — только полное совпадение») не
        # подтвердилось: поиск реально фильтрует по подстроке локальной части email (например,
        # 6-символьный префикс локальной части матчит десятки накопленных на стенде
        # auto_test_*-записей прежних прогонов), но НИКОГДА не матчит по домену (подтверждено
        # многократно живыми прогонами с разными случайными данными: "@gmail.com"/"gmail"/
        # "gmail.com" стабильно дают 0 совпадений, даже для только что созданного заявителя с
        # доменом gmail.com). Поэтому для детерминированной (не зависящей от объёма накопленных
        # на стенде тестовых данных) проверки используем домен как надёжный случай "0 совпадений",
        # а полный email — как случай "ровно 1 совпадение".
        payload = generate_helpdesk_applicant_payload()
        resp = helpdesk_endpoint.add_applicant(payload)
        assert resp.status_code < 400, f"Не удалось создать заявителя: {resp.status_code} {resp.text[:300]}"

        with allure.step("Поиск по домену email («@gmail.com») — 0 результатов (домен не индексируется)"):
            domain = "@" + payload["email"].split("@")[1]
            domain_data = helpdesk_endpoint.search_applicant(domain)
            assert domain_data["recordsFiltered"] == 0, (
                f"Ожидалось 0 совпадений по домену email, получено {domain_data['recordsFiltered']}"
            )

        with allure.step("Полный email — ровно 1 результат"):
            full_data = helpdesk_endpoint.search_applicant(payload["email"])
            assert full_data["recordsFiltered"] == 1, (
                f"Ожидался 1 результат по полному email, получено {full_data['recordsFiltered']}"
            )
            row_html = "".join(full_data["data"][0])
            assert payload["email"] in row_html

    @allure.title("POST /admin/identity/search по ФИО — находит только в порядке «Фамилия Имя»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_search_applicant_by_full_name(self, helpdesk_endpoint):
        # Исходное предположение разведки («поиск одним словом ФИО не фильтрует список») не
        # подтвердилось для данных этого генератора: surname уже содержит уникальный на весь
        # стенд auto_test_-суффикз, поэтому поиск даже одним этим словом однозначно находит
        # заявителя. Подтверждённая живыми прогонами (многократно, с разными случайными ФИО)
        # закономерность — порядок слов: «Фамилия Имя» находит запись, обратный порядок
        # «Имя Фамилия» — не находит ни одной записи.
        payload = generate_helpdesk_applicant_payload()
        resp = helpdesk_endpoint.add_applicant(payload)
        assert resp.status_code < 400, f"Не удалось создать заявителя: {resp.status_code} {resp.text[:300]}"

        with allure.step("Поиск одним словом (surname с auto_test_ префиксом) — находит заявителя"):
            one_word_data = helpdesk_endpoint.search_applicant(payload["surname"])
            assert one_word_data["recordsFiltered"] == 1, (
                f"Ожидался 1 результат по surname, получено {one_word_data['recordsFiltered']}"
            )

        with allure.step("Поиск «Имя Фамилия» (обратный порядок) — 0 результатов"):
            reversed_order = f"{payload['name']} {payload['surname']}"
            reversed_data = helpdesk_endpoint.search_applicant(reversed_order)
            assert reversed_data["recordsFiltered"] == 0, (
                f"Ожидалось 0 результатов для обратного порядка слов, получено {reversed_data['recordsFiltered']}"
            )

        with allure.step("Поиск «Фамилия Имя» (прямой порядок) — ровно 1 результат"):
            direct_order = f"{payload['surname']} {payload['name']}"
            data = helpdesk_endpoint.search_applicant(direct_order)
            assert data["recordsFiltered"] == 1, f"Ожидался 1 результат, получено {data['recordsFiltered']}"

    @allure.title("POST /admin/identity — заявитель добавляется и находится по email")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_create_applicant(self, helpdesk_endpoint):
        # Удаление заявителей инфраструктурой не предусмотрено (нет DELETE у /admin/identity,
        # docs/helpdesk_recon.md §2) — созданный auto_test_* заявитель остаётся в системе.
        payload = generate_helpdesk_applicant_payload()

        with allure.step("POST /admin/identity — заявитель создан"):
            resp = helpdesk_endpoint.add_applicant(payload)
            assert resp.status_code < 400, f"Не удалось создать заявителя: {resp.status_code} {resp.text[:300]}"

        with allure.step("GET /admin/identity/search — заявитель найден по email"):
            found = helpdesk_endpoint.find_applicant_by_email(payload["email"])
            assert found is not None, f"Заявитель {payload['email']!r} не найден после создания"
