"""p2p / распределение работ между слушателями потока
(docs/test_cases/p2p/03_distribution.md, TC-P2P-021..025).

Контракт не подтверждён (api/endpoints/p2p.py) — функциональности ещё нет ни на одной
ветке (docs/missions/2026-09-30_tz2026_p2p.md). Тесты пропускаются без P2P_READY, см.
tests/api/p2p/conftest.py.
"""
import allure
import pytest

from utils.logger import logger


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Распределение работ между слушателями")
class TestDistribution:

    @allure.title("Ручное распределение: администратор назначает конкретному слушателю конкретную чужую работу")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_manual_assignment_of_specific_work_to_listener(self, stream_with_submitted_works, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Подготовить поток с несколькими сданными работами"):
            data = stream_with_submitted_works(listeners_count=2)
            reviewer, author = data["listeners"][0], data["listeners"][1]
            author_work = next(w for w in data["works"] if w["author"]["id"] == author["id"])

        with allure.step("2. Назначить слушателю на проверку конкретную чужую работу вручную"):
            p2p_endpoint.assign_work_manually(
                data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"],
                author_work["work_id"], reviewer["id"],
            )

        with allure.step("3. Убедиться, что назначение появилось в списке слушателя-проверяющего"):
            assignments = p2p_endpoint.list_assignments(
                data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"],
                reviewer_user_id=reviewer["id"],
            )
            assigned_work_ids = {a.get("attributes", {}).get("work_id") or a.get("work_id") for a in assignments}
            assert author_work["work_id"] in assigned_work_ids

    @allure.title("Ручное распределение: собственная работа слушателю не назначается")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_manual_assignment_rejects_own_work(self, submitted_work, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Попытаться вручную назначить слушателю на проверку его собственную работу"):
            work = submitted_work()
            resp = p2p_endpoint.client.post(
                f"/programs/{work['stream']['program_id']}/streams/{work['stream']['id']}"
                f"/content/{work['homework']['id']}/peer-review/assignments",
                json={"data": {"attributes": {"work_id": work["work_id"], "reviewer_user_id": work["author"]["id"]}}},
            )

        with allure.step("2. Убедиться, что назначение отклонено"):
            assert resp.status_code in (400, 422), (
                f"Назначение собственной работы должно быть отклонено, получили {resp.status_code}"
            )

    @allure.title("Автоматическое распределение назначает слушателю заданное количество чужих работ")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_automatic_distribution_respects_works_per_listener(self, stream_with_submitted_works, p2p_endpoint):
        """Предусловие: в потоке настроено «Количество работ для проверки одним слушателем» = N."""
        works_per_listener = 2

        with allure.step(f"1. Настроить works_per_listener={works_per_listener} и запустить автораспределение"):
            data = stream_with_submitted_works(listeners_count=3)
            p2p_endpoint.set_distribution_mode(data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"], "auto")
            p2p_endpoint.set_works_per_listener(
                data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"], works_per_listener
            )
            p2p_endpoint.run_automatic_distribution(data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"])

        with allure.step("2. Проверить, что каждому слушателю назначено не больше N чужих работ"):
            for listener in data["listeners"]:
                assignments = p2p_endpoint.list_assignments(
                    data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"],
                    reviewer_user_id=listener["id"],
                )
                logger.info(f"Слушателю {listener['id']} назначено {len(assignments)} работ")
                assert len(assignments) <= works_per_listener

    @allure.title("Автоматическое распределение не назначает слушателю его собственную работу")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_automatic_distribution_excludes_own_work(self, stream_with_submitted_works, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Запустить автоматическое распределение в потоке со сданными работами"):
            data = stream_with_submitted_works(listeners_count=3)
            p2p_endpoint.set_distribution_mode(data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"], "auto")
            p2p_endpoint.run_automatic_distribution(data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"])

        with allure.step("2. Убедиться, что ни одному слушателю не назначена его собственная работа"):
            own_work_by_listener = {w["author"]["id"]: w["work_id"] for w in data["works"]}
            for listener in data["listeners"]:
                assignments = p2p_endpoint.list_assignments(
                    data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"],
                    reviewer_user_id=listener["id"],
                )
                assigned_work_ids = {a.get("attributes", {}).get("work_id") or a.get("work_id") for a in assignments}
                assert own_work_by_listener[listener["id"]] not in assigned_work_ids

    @allure.title("Ограничения ручного/автоматического распределения не применяются к внешнему проверяющему")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_external_reviewer_bypasses_stream_distribution_limits(self, stream_with_submitted_works, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Настроить в потоке режим распределения и лимит «Количество работ на слушателя»"):
            data = stream_with_submitted_works(listeners_count=3)
            p2p_endpoint.set_distribution_mode(data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"], "auto")
            p2p_endpoint.set_works_per_listener(data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"], 1)
            p2p_endpoint.run_automatic_distribution(data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"])

        with allure.step("2. Добавить внешнего проверяющего и открыть его список работ"):
            external = p2p_endpoint.add_external_reviewer(
                data["stream"]["program_id"], data["stream"]["id"], data["homework"]["id"],
                full_name="Автотест Внешний Проверяющий",
            )
            link = p2p_endpoint.get_external_reviewer_link(external["id"])

        with allure.step("3. Убедиться, что внешнему проверяющему выводится весь список сданных работ без лимита"):
            works = p2p_endpoint.list_works_for_external_link(link.rsplit("/", 1)[-1])
            assert len(works) == len(data["works"]), (
                "Лимит «Количество работ для проверки одним слушателем» не должен действовать на внешнего проверяющего"
            )
