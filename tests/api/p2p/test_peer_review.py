"""p2p / слушатель-проверяющий: ограничение на выставление итогового результата
(docs/test_cases/p2p/04_peer_review.md, TC-P2P-032).

Контракт не подтверждён (api/endpoints/p2p.py) — функциональности ещё нет ни на одной
ветке (docs/missions/2026-09-30_tz2026_p2p.md). Тесты пропускаются без P2P_READY, см.
tests/api/p2p/conftest.py.
"""
import allure
import pytest

from utils.logger import logger


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Слушатель-проверяющий: ограничения API")
class TestPeerReview:

    @allure.title("Слушатель-проверяющий не выставляет итоговый результат по чужой работе")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_peer_reviewer_cannot_set_final_result(self, submitted_work, created_user, p2p_endpoint, p2p_client_for):
        """Предусловие: -"""
        with allure.step("1. Назначить слушателю проверку чужой работы"):
            work = submitted_work()
            reviewer_listener = created_user()
            p2p_endpoint.assign_work_manually(
                work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"],
                work["work_id"], reviewer_listener["id"],
            )

        with allure.step("2. От имени слушателя-проверяющего запросить выставление итогового результата"):
            reviewer_client, _ = p2p_client_for(reviewer_listener)
            resp = reviewer_client.put(
                f"/homework/{work['work_id']}/final-result",
                json={"data": {"attributes": {"reviewer_user_id": reviewer_listener["id"], "grade": "5"}}},
            )
            logger.info(f"Попытка слушателя-проверяющего выставить итог: {resp.status_code}")

        with allure.step("3. Убедиться, что действие отклонено — итог выставляет только штатный проверяющий"):
            assert resp.status_code in (403, 404, 422), (
                f"Слушатель-проверяющий не должен иметь возможность выставить итоговый результат, "
                f"получили {resp.status_code}"
            )
