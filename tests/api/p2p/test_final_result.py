"""p2p / итоговый результат: штатный проверяющий видит peer-проверки и агрегаты,
выставляет и меняет итог; администратор без назначения не может
(docs/test_cases/p2p/06_final_result.md, TC-P2P-043..046).

Контракт не подтверждён (api/endpoints/p2p.py) — функциональности ещё нет ни на одной
ветке (docs/missions/2026-09-30_tz2026_p2p.md). Кейсы написаны по приоритетной версии 04
(итог доступен любому штатному проверяющему, без отдельного признака — см. README).
Тесты пропускаются без P2P_READY, см. tests/api/p2p/conftest.py.
"""
import allure
import pytest


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Итоговый результат по работе")
class TestFinalResult:

    @allure.title("Штатный проверяющий видит все peer-проверки по работе и агрегированные значения")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_reviewer_sees_all_peer_reviews_and_aggregates(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: по работе есть хотя бы одна peer-проверка."""
        with allure.step("1. Назначить штатного проверяющего и слушателя-проверяющего, получить peer-проверку"):
            work = submitted_work()
            reviewer = created_user()
            p2p_endpoint.assign_card_reviewers(work["homework"]["id"], [reviewer["id"]])

            peer_reviewer = created_user()
            p2p_endpoint.assign_work_manually(
                work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"],
                work["work_id"], peer_reviewer["id"],
            )
            p2p_endpoint.submit_peer_review(
                work["work_id"], peer_reviewer["id"], criteria_values={"scale": 5}, final_confirm=True
            )

        with allure.step("2. Открыть работу от имени штатного проверяющего и прочитать результаты"):
            reviews = p2p_endpoint.get_peer_reviews_for_work(work["work_id"])
            aggregates = p2p_endpoint.get_aggregates(work["work_id"])

        with allure.step("3. Убедиться, что видны все peer-проверки и агрегированные значения"):
            assert len(reviews) >= 1
            assert aggregates

    @allure.title("Штатный проверяющий выставляет итоговый результат по работе")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_reviewer_sets_final_result(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Назначить штатного проверяющего"):
            work = submitted_work()
            reviewer = created_user()
            p2p_endpoint.assign_card_reviewers(work["homework"]["id"], [reviewer["id"]])

        with allure.step("2. От имени штатного проверяющего выставить итоговый результат по работе"):
            result = p2p_endpoint.set_final_result(work["work_id"], reviewer["id"], {"grade": "5"})
            assert result

        with allure.step("3. Убедиться, что работа перешла в статус «Итоговый результат выставлен»"):
            status = p2p_endpoint.get_work_status(work["homework"]["id"], work["work_id"])
            assert status == "Итоговый результат выставлен"

    @allure.title("Штатный проверяющий может изменить уже выставленный итоговый результат")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_reviewer_changes_final_result(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: итоговый результат уже выставлен."""
        with allure.step("1. Выставить итоговый результат по работе"):
            work = submitted_work()
            reviewer = created_user()
            p2p_endpoint.assign_card_reviewers(work["homework"]["id"], [reviewer["id"]])
            p2p_endpoint.set_final_result(work["work_id"], reviewer["id"], {"grade": "3"})

        with allure.step("2. От имени штатного проверяющего изменить ранее выставленный итог"):
            updated = p2p_endpoint.set_final_result(work["work_id"], reviewer["id"], {"grade": "5"})
            assert updated

        with allure.step("3. Убедиться, что новое значение сохранено"):
            saved = p2p_endpoint.client.get(f"/homework/{work['work_id']}/final-result").json()["data"]
            assert saved["attributes"]["grade"] == "5"

    @allure.title("Администратор без назначения проверяющим не может выставить итоговый результат")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_admin_without_reviewer_assignment_cannot_set_final_result(self, submitted_work, created_user, p2p_endpoint, p2p_client_for):
        """Предусловие: администратор не назначен штатным проверяющим этого ПЗ."""
        with allure.step("1. Подготовить работу без назначения текущего администратора проверяющим"):
            work = submitted_work()
            other_admin = created_user()

        with allure.step("2. От имени администратора без назначения запросить выставление итогового результата"):
            other_client, _ = p2p_client_for(other_admin)
            resp = other_client.put(
                f"/homework/{work['work_id']}/final-result",
                json={"data": {"attributes": {"reviewer_user_id": other_admin["id"], "grade": "5"}}},
            )

        with allure.step("3. Убедиться, что действие отклонено, а просмотр работ/статистики остаётся доступен"):
            assert resp.status_code in (403, 422)
            reviews = p2p_endpoint.get_peer_reviews_for_work(work["work_id"])
            assert isinstance(reviews, list)
