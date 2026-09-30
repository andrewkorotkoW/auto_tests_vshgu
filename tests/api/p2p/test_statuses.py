"""p2p / статусы работы и назначенной проверки (03 §8, 04 §10)
(docs/test_cases/p2p/09_statuses.md, TC-P2P-062..069).

Контракт не подтверждён (api/endpoints/p2p.py) — функциональности ещё нет ни на одной
ветке (docs/missions/2026-09-30_tz2026_p2p.md). Тесты пропускаются без P2P_READY, см.
tests/api/p2p/conftest.py.
"""
import allure
import pytest


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Статусы работы и назначенной проверки")
class TestStatuses:

    @allure.title("Статус работы «Не сдано» → «Сдано» после отправки ответа слушателем")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_work_status_not_submitted_to_submitted(self, assigned_user, created_homework, p2p_endpoint,
                                                      homework_endpoint, p2p_client_for):
        """Предусловие: -"""
        with allure.step("1. Проверить статус работы до отправки ответа"):
            assigned = assigned_user()
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            status_before = homework_endpoint.get_status(homework["id"], assigned["user"]["id"])
            assert status_before in ("Не сдано", None, "not_submitted")

        with allure.step("2. Слушатель отправляет ответ по P2P-ПЗ"):
            client, _ = p2p_client_for(assigned["user"])
            client.post(f"/homework/{homework['id']}/answers", json={"data": {"attributes": {"text": "Автотест: ответ"}}})

        with allure.step("3. Проверить, что статус изменился на «Сдано»"):
            status_after = homework_endpoint.get_status(homework["id"], assigned["user"]["id"])
            assert status_after == "Сдано"

    @allure.title("Статус работы «Сдано» → «На взаимопроверке» после назначения проверяющих")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_work_status_submitted_to_under_review(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: работа в статусе «Сдано»."""
        with allure.step("1. Назначить работу слушателям-проверяющим и/или штатным проверяющим"):
            work = submitted_work()
            peer_reviewer = created_user()
            p2p_endpoint.assign_work_manually(
                work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"],
                work["work_id"], peer_reviewer["id"],
            )

        with allure.step("2. Проверить статус работы"):
            status = p2p_endpoint.get_work_status(work["homework"]["id"], work["work_id"])
            assert status == "На взаимопроверке"

    @allure.title("Статус работы меняется на «Взаимопроверка завершена, ожидает итогового результата» после набора минимума")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_work_status_review_completed_awaiting_final_result(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: по работе набрано минимальное количество peer-проверок."""
        with allure.step("1. Получить по работе минимально необходимое количество peer-проверок"):
            work = submitted_work()
            p2p_endpoint.set_minimum_reviews_per_work(
                work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"], 1
            )
            peer_reviewer = created_user()
            p2p_endpoint.assign_work_manually(
                work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"],
                work["work_id"], peer_reviewer["id"],
            )
            p2p_endpoint.submit_peer_review(work["work_id"], peer_reviewer["id"], {"scale": 5}, final_confirm=True)

        with allure.step("2. Проверить статус работы"):
            status = p2p_endpoint.get_work_status(work["homework"]["id"], work["work_id"])
            assert status == "Взаимопроверка завершена, ожидает итогового результата"

    @allure.title("Статус работы меняется на «Итоговый результат выставлен» после действия штатного проверяющего")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_work_status_final_result_set(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: работа в статусе «Взаимопроверка завершена, ожидает итогового результата»."""
        with allure.step("1. Штатный проверяющий выставляет итоговый результат"):
            work = submitted_work()
            reviewer = created_user()
            p2p_endpoint.assign_card_reviewers(work["homework"]["id"], [reviewer["id"]])
            p2p_endpoint.set_final_result(work["work_id"], reviewer["id"], {"grade": "5"})

        with allure.step("2. Проверить статус работы"):
            status = p2p_endpoint.get_work_status(work["homework"]["id"], work["work_id"])
            assert status == "Итоговый результат выставлен"

    @allure.title("Статус работы «Возвращено на доработку» и возврат в цикл проверки после повторной сдачи")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_work_status_returned_for_revision_and_resubmission(self, submitted_work, created_user, p2p_endpoint, p2p_client_for):
        """Предусловие: -"""
        with allure.step("1. Штатный проверяющий возвращает работу на доработку"):
            work = submitted_work()
            reviewer = created_user()
            p2p_endpoint.assign_card_reviewers(work["homework"]["id"], [reviewer["id"]])
            p2p_endpoint.return_for_revision(work["work_id"], reviewer["id"], comment="Автотест: доработайте пункт 2")

        with allure.step("2. Проверить статус «Возвращено на доработку»"):
            status = p2p_endpoint.get_work_status(work["homework"]["id"], work["work_id"])
            assert status == "Возвращено на доработку"

        with allure.step("3. Автор отправляет новую версию работы"):
            author_client, _ = p2p_client_for(work["author"])
            author_client.post(
                f"/homework/{work['homework']['id']}/answers",
                json={"data": {"attributes": {"text": "Автотест: доработанный ответ"}}},
            )

        with allure.step("4. Проверить, что работа снова в цикле проверки"):
            status_after = p2p_endpoint.get_work_status(work["homework"]["id"], work["work_id"])
            assert status_after in ("На взаимопроверке", "Сдано")

    @allure.title("Статус назначенной проверки «Назначена» → «В работе» → «Проверена»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_review_status_assigned_in_progress_reviewed(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Назначить проверку слушателю/проверяющему"):
            work = submitted_work()
            peer_reviewer = created_user()
            assignment = p2p_endpoint.assign_work_manually(
                work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"],
                work["work_id"], peer_reviewer["id"],
            )
            review_id = assignment["data"]["id"]
            assert p2p_endpoint.get_review_status(review_id) == "Назначена"

        with allure.step("2. Открыть форму проверки, начать заполнение (без отправки)"):
            p2p_endpoint.submit_peer_review(work["work_id"], peer_reviewer["id"], {"scale": 4}, final_confirm=False)
            assert p2p_endpoint.get_review_status(review_id) == "В работе"

        with allure.step("3. Отправить форму оценки"):
            p2p_endpoint.submit_peer_review(work["work_id"], peer_reviewer["id"], {"scale": 4}, final_confirm=True)
            assert p2p_endpoint.get_review_status(review_id) == "Проверена"

    @allure.title("Статус назначенной проверки «Приостановлена» при возврате работы на доработку")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_review_status_paused_on_return_for_revision(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: по работе есть незавершённая peer-проверка."""
        with allure.step("1. Подготовить незавершённую peer-проверку"):
            work = submitted_work()
            peer_reviewer = created_user()
            assignment = p2p_endpoint.assign_work_manually(
                work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"],
                work["work_id"], peer_reviewer["id"],
            )
            review_id = assignment["data"]["id"]
            p2p_endpoint.submit_peer_review(work["work_id"], peer_reviewer["id"], {"scale": 4}, final_confirm=False)

        with allure.step("2. Штатный проверяющий возвращает работу на доработку"):
            reviewer = created_user()
            p2p_endpoint.assign_card_reviewers(work["homework"]["id"], [reviewer["id"]])
            p2p_endpoint.return_for_revision(work["work_id"], reviewer["id"], comment="Автотест: доработать")

        with allure.step("3. Проверить статус незавершённой peer-проверки"):
            assert p2p_endpoint.get_review_status(review_id) == "Приостановлена"

    @allure.title("Статус назначенной проверки «Отменена», если проверка больше не требуется")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_review_status_cancelled_when_no_longer_required(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Снять с пользователя ранее назначенную, но не выполненную проверку"):
            work = submitted_work()
            peer_reviewer = created_user()
            assignment = p2p_endpoint.assign_work_manually(
                work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"],
                work["work_id"], peer_reviewer["id"],
            )
            review_id = assignment["data"]["id"]

            resp = p2p_endpoint.client.delete(
                f"/programs/{work['stream']['program_id']}/streams/{work['stream']['id']}"
                f"/content/{work['homework']['id']}/peer-review/assignments/{review_id}"
            )
            assert resp.status_code in (200, 204)

        with allure.step("2. Проверить статус этой проверки"):
            assert p2p_endpoint.get_review_status(review_id) == "Отменена"
