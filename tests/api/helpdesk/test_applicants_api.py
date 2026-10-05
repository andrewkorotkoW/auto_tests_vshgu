import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_applicant_payload
from tests.api.helpdesk._known_defects import CSRF_TOKEN_DEFECT_REASON


@allure.feature("Хелпдеск: Заявители")
@allure.story("Поиск и добавление заявителя")
class TestApplicantsApi:

    @allure.title("POST /admin/identity/search по email — фильтрует только по полному совпадению")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=CSRF_TOKEN_DEFECT_REASON)
    def test_search_applicant_by_email(self, helpdesk_endpoint):
        # У /admin/identity нет маршрута DELETE (docs/helpdesk_recon.md §2) — созданный
        # auto_test_* заявитель остаётся в системе, удаление не предусмотрено инфраструктурой.
        payload = generate_helpdesk_applicant_payload()
        resp = helpdesk_endpoint.add_applicant(payload)
        assert resp.status_code < 400, f"Не удалось создать заявителя: {resp.status_code} {resp.text[:300]}"

        with allure.step("Партиал email (6 символов) — 0 результатов"):
            partial = payload["email"][:6]
            partial_data = helpdesk_endpoint.search_applicant(partial)
            assert partial_data["recordsFiltered"] == 0, (
                f"Ожидалось 0 совпадений по партиалу email, получено {partial_data['recordsFiltered']}"
            )

        with allure.step("Полный email — ровно 1 результат"):
            full_data = helpdesk_endpoint.search_applicant(payload["email"])
            assert full_data["recordsFiltered"] == 1, (
                f"Ожидался 1 результат по полному email, получено {full_data['recordsFiltered']}"
            )
            row_html = "".join(full_data["data"][0])
            assert payload["email"] in row_html

    @allure.title("POST /admin/identity/search по ФИО — одно слово не фильтрует, «Фамилия Имя» находит заявителя")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=CSRF_TOKEN_DEFECT_REASON)
    def test_search_applicant_by_full_name(self, helpdesk_endpoint):
        payload = generate_helpdesk_applicant_payload()
        resp = helpdesk_endpoint.add_applicant(payload)
        assert resp.status_code < 400, f"Не удалось создать заявителя: {resp.status_code} {resp.text[:300]}"

        with allure.step("Поиск одним словом (surname с auto_test_ префиксом) — не фильтрует список"):
            one_word_data = helpdesk_endpoint.search_applicant(payload["surname"])
            full_data = helpdesk_endpoint.search_applicant("")
            assert one_word_data["recordsFiltered"] == full_data["recordsTotal"], (
                "Ожидалось, что поиск одним словом ФИО не фильтрует список "
                f"(получено recordsFiltered={one_word_data['recordsFiltered']}, "
                f"recordsTotal={full_data['recordsTotal']})"
            )

        with allure.step("Поиск «Фамилия Имя» (два слова) — ровно 1 результат"):
            two_words = f"{payload['surname']} {payload['name']}"
            data = helpdesk_endpoint.search_applicant(two_words)
            assert data["recordsFiltered"] == 1, f"Ожидался 1 результат, получено {data['recordsFiltered']}"

    @allure.title("POST /admin/identity — заявитель добавляется и находится по email")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=CSRF_TOKEN_DEFECT_REASON)
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
