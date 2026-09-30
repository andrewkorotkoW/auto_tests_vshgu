"""p2p / карточка ПЗ: тумблер «Включить взаимопроверку», штатные проверяющие
(docs/test_cases/p2p/00_pt_card_settings.md, TC-P2P-001..005).

Контракт не подтверждён (api/endpoints/p2p.py) — функциональности ещё нет ни на одной
ветке (docs/missions/2026-09-30_tz2026_p2p.md). Тесты пропускаются без P2P_READY, см.
tests/api/p2p/conftest.py.
"""
import allure
import pytest

from api.endpoints.users import UsersEndpoint
from api.helpers.expectations import expect_status
from utils.logger import logger

# Роль «Преподаватель» — по аналогии с tests/api/users/teacher/test_examine_by_teacher.py
# (там же помечена как "предполагаемая", ID не подтверждён на develop).
TEACHER_ROLE_ID = 4


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Карточка ПЗ: тумблер и штатные проверяющие")
class TestPtCardSettings:

    @allure.title("Тумблер «Включить взаимопроверку» выключен — ПЗ работает по стандартному сценарию")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_toggle_off_keeps_standard_homework_flow(self, homework_endpoint, assigned_user, created_homework, p2p_endpoint):
        """Предусловие: ПЗ создано без включения «Включить взаимопроверку» (04 §1, §4)."""
        with allure.step("1. Создать ПЗ без включения «Включить взаимопроверку», назначить в поток"):
            assigned = assigned_user()
            homework = created_homework()

        with allure.step("2. Проверить, что настройки взаимопроверки недоступны/не отображаются для этого ПЗ"):
            resp = p2p_endpoint.client.get(f"/content/{homework['id']}/peer-review/criteria")
            assert resp.status_code in (403, 404), (
                f"Без включённой взаимопроверки форма критериев не должна быть доступна, получили {resp.status_code}"
            )

        with allure.step("3. Убедиться, что штатный (не-P2P) сценарий проверки ПЗ работает как раньше"):
            status = homework_endpoint.get_status(homework["id"], assigned["user"]["id"])
            logger.info(f"Homework {homework['id']} status для {assigned['user']['id']}: {status}")
            assert status is not None, "Статус обычного ПЗ должен читаться так же, как до появления взаимопроверки"

    @allure.title("Включение тумблера открывает блок настроек взаимопроверки в карточке ПЗ")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_toggle_on_exposes_p2p_settings_block(self, created_homework, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Создать ПЗ и включить «Включить взаимопроверку»"):
            homework = created_homework()
            result = p2p_endpoint.enable_peer_review(homework["id"], enabled=True)
            assert result, "Включение взаимопроверки не вернуло данные"

        with allure.step("2. Прочитать карточку ПЗ: доступны штатные проверяющие и форма критериев"):
            eligible = p2p_endpoint.list_eligible_reviewers(homework["id"])
            criteria = p2p_endpoint.get_criteria(homework["id"])
            assert isinstance(eligible, list)
            assert isinstance(criteria, list)

    @allure.title("Список штатных проверяющих ограничен пользователями, разрешёнными системой быть проверяющими ПЗ")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_reviewer_pool_limited_to_existing_eligible_users(self, created_homework, created_user, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Включить взаимопроверку и запросить список кандидатов в штатные проверяющие"):
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            eligible = p2p_endpoint.list_eligible_reviewers(homework["id"])
            eligible_ids = {item.get("id") for item in eligible}

        with allure.step("2. Попытаться назначить пользователя вне этого списка (слушатель без прав)"):
            outsider = created_user()
            assert outsider["id"] not in eligible_ids, (
                "Свежесозданный слушатель без прав не должен входить в пул штатных проверяющих"
            )
            resp = p2p_endpoint.client.post(
                f"/content/{homework['id']}/peer-review/reviewers",
                json={"data": {"attributes": {"user_ids": [outsider["id"]]}}},
            )
            assert resp.status_code in (403, 422), (
                f"Назначение пользователя вне пула кандидатов должно быть отклонено, получили {resp.status_code}"
            )

    @allure.title("Назначение штатным проверяющим автоматически выдаёт роль «Преподаватель»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_assigning_reviewer_grants_teacher_role_if_missing(self, created_homework, created_user, p2p_endpoint, api_client):
        """Предусловие: -"""
        users_endpoint = UsersEndpoint(api_client)

        with allure.step("1. Взять пользователя без роли «Преподаватель»"):
            candidate = created_user()
            before = users_endpoint.get(candidate["id"])
            roles_before = before.get("attributes", {}).get("roles") or before.get("attributes", {}).get("role_ids") or []
            assert TEACHER_ROLE_ID not in roles_before

        with allure.step("2. Назначить пользователя штатным проверяющим P2P-ПЗ"):
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            p2p_endpoint.assign_card_reviewers(homework["id"], [candidate["id"]])

        with allure.step("3. Убедиться, что роль «Преподаватель» выдана автоматически"):
            after = users_endpoint.get(candidate["id"])
            roles_after = after.get("attributes", {}).get("roles") or after.get("attributes", {}).get("role_ids") or []
            assert TEACHER_ROLE_ID in roles_after, "Роль «Преподаватель» не была выдана автоматически"

        with allure.step("4. Повторно назначить пользователя, у которого роль уже есть — без дублирования"):
            p2p_endpoint.assign_card_reviewers(homework["id"], [candidate["id"]])
            repeated = users_endpoint.get(candidate["id"])
            roles_repeated = repeated.get("attributes", {}).get("roles") or repeated.get("attributes", {}).get("role_ids") or []
            assert roles_repeated.count(TEACHER_ROLE_ID) == 1, "Роль «Преподаватель» не должна дублироваться"

    @allure.title("Слушатели-проверяющие потока не попадают в список штатных проверяющих карточки ПЗ")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_stream_peer_reviewers_not_added_to_card_reviewer_list(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. В потоке распределить чужую работу слушателю как peer-проверку"):
            work = submitted_work()
            stream_reviewer = created_user()
            p2p_endpoint.assign_work_manually(
                work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"],
                work["work_id"], stream_reviewer["id"],
            )

        with allure.step("2. Прочитать список штатных проверяющих в карточке ПЗ"):
            card_reviewers = p2p_endpoint.list_eligible_reviewers(work["homework"]["id"])
            card_reviewer_ids = {item.get("id") for item in card_reviewers}
            logger.info(f"Штатные проверяющие карточки ПЗ {work['homework']['id']}: {card_reviewer_ids}")

        with allure.step("3. Убедиться, что слушатель-проверяющий отсутствует в списке штатных"):
            assert stream_reviewer["id"] not in card_reviewer_ids, (
                "Слушатель-проверяющий потока не должен попадать в список штатных проверяющих карточки ПЗ"
            )
