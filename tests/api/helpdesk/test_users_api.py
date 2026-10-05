import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_role_assignment_payload
from tests.api.helpdesk._known_defects import CSRF_TOKEN_DEFECT_REASON, USER_SEARCH_500_DEFECT_REASON


@allure.feature("Хелпдеск: Пользователи")
@allure.story("Назначение ролей, поиск")
class TestUsersApi:

    @allure.title("POST /admin/user/{id}/assign-role — роль назначается тестовому пользователю")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(
        strict=False,
        reason=f"{USER_SEARCH_500_DEFECT_REASON} find_user_by_email падает первым (тот же поиск), "
        f"не доходя до assign_role(), который дополнительно заблокирован CSRF-дефектом: {CSRF_TOKEN_DEFECT_REASON}",
    )
    def test_assign_role(self, helpdesk_endpoint, created_user):
        user = created_user()

        with allure.step("Найти созданного тестового пользователя в хелпдеске по email"):
            found = helpdesk_endpoint.find_user_by_email(user["email"])
            assert found is not None and found["id"], f"Пользователь {user['email']!r} не найден в хелпдеске"
            helpdesk_user_id = found["id"]

        with allure.step("GET /admin/user/{id}/assign-role — модалка с чекбоксами ролей открывается"):
            client = helpdesk_endpoint.client
            resp = client.session.get(
                f"{client.base_url}{helpdesk_endpoint.USER_PATH}/{helpdesk_user_id}/assign-role",
                timeout=client.timeout,
            )
            assert resp.status_code == 200, f"Ожидался 200, получено {resp.status_code}"

        with allure.step("POST /admin/user/{id}/assign-role — роль «Поддержка» назначена"):
            payload = generate_helpdesk_role_assignment_payload(support=True)
            resp = helpdesk_endpoint.assign_role(helpdesk_user_id, payload)
            assert resp.status_code < 400, f"Не удалось назначить роль: {resp.status_code} {resp.text[:300]}"

        with allure.step("GET /admin/user/{id}/show — назначенная роль отображается в карточке"):
            html = helpdesk_endpoint.get_user(helpdesk_user_id)
            assert "оддержк" in html, "Назначенная роль «Поддержка» не отображается в карточке пользователя"

    @allure.title("POST /admin/user/search по email — прогрессивная фильтрация с первого символа")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=USER_SEARCH_500_DEFECT_REASON)
    def test_search_user_by_email(self, helpdesk_endpoint, created_user):
        user = created_user()

        with allure.step("Поиск по уникальной части email — список уже сужен"):
            # 20 символов локальной части (auto_test_<worker>_<ts>) — уникальный фрагмент,
            # не встречающийся у других пользователей, но ещё не полный email
            narrow_part = user["email"].split("@")[0][:20]
            full_data = helpdesk_endpoint.search_user("")
            narrow_data = helpdesk_endpoint.search_user(narrow_part)
            assert narrow_data["recordsFiltered"] < full_data["recordsTotal"], (
                "Ожидалось, что поиск по уникальному фрагменту email сужает список "
                f"(получено recordsFiltered={narrow_data['recordsFiltered']}, "
                f"recordsTotal={full_data['recordsTotal']})"
            )

        with allure.step("Поиск по полному email — ровно одна строка с искомым пользователем"):
            data = helpdesk_endpoint.search_user(user["email"])
            assert data["recordsFiltered"] == 1, (
                f"Ожидалась 1 запись по полному email, получено {data['recordsFiltered']}"
            )
            row_html = "".join(data["data"][0])
            assert user["email"] in row_html
