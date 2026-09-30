"""p2p / агрегация результатов peer-проверок по критериям
(docs/test_cases/p2p/07_aggregation.md, TC-P2P-049..051).

Контракт не подтверждён (api/endpoints/p2p.py) — функциональности ещё нет ни на одной
ветке (docs/missions/2026-09-30_tz2026_p2p.md). Тесты пропускаются без P2P_READY, см.
tests/api/p2p/conftest.py.
"""
import allure
import pytest


def _assign_reviewers_and_submit(p2p_endpoint, created_user, work, criteria_values_list):
    """Назначает по одному слушателю-проверяющему на каждый набор значений критериев
    и сохраняет по нему peer-проверку с финальным подтверждением."""
    for criteria_values in criteria_values_list:
        peer_reviewer = created_user()
        p2p_endpoint.assign_work_manually(
            work["stream"]["program_id"], work["stream"]["id"], work["homework"]["id"],
            work["work_id"], peer_reviewer["id"],
        )
        p2p_endpoint.submit_peer_review(work["work_id"], peer_reviewer["id"], criteria_values, final_confirm=True)


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Агрегация результатов по критериям")
class TestAggregation:

    @allure.title("Среднее арифметическое по числовому критерию считается с округлением до 0,1")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_numeric_criterion_average_rounded_to_one_decimal(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: по работе получено несколько peer-проверок по числовому критерию (шкала)."""
        with allure.step("1. Настроить критерий-шкалу и получить оценки 4, 5, 4 от трёх проверяющих"):
            work = submitted_work()
            p2p_endpoint.set_criteria(work["homework"]["id"], [{"id": "scale", "type": "scale", "label": "Оценка по шкале"}])
            _assign_reviewers_and_submit(p2p_endpoint, created_user, work, [
                {"scale": 4}, {"scale": 5}, {"scale": 4},
            ])

        with allure.step("2. Прочитать агрегированное значение по критерию"):
            aggregates = p2p_endpoint.get_aggregates(work["work_id"])

        with allure.step("3. Убедиться, что показано среднее с округлением до одного знака: 4,3"):
            assert round(aggregates["scale"], 1) == 4.3

    @allure.title("Текстовые критерии выводятся списком без числовой агрегации")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_text_criterion_listed_without_aggregation(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: по работе получено несколько peer-проверок с текстовым комментарием."""
        with allure.step("1. Настроить текстовый критерий и получить несколько текстовых ответов"):
            work = submitted_work()
            p2p_endpoint.set_criteria(work["homework"]["id"], [{"id": "comment", "type": "text", "label": "Комментарий"}])
            texts = ["Автотест: комментарий проверяющего 1", "Автотест: комментарий проверяющего 2"]
            _assign_reviewers_and_submit(p2p_endpoint, created_user, work, [{"comment": t} for t in texts])

        with allure.step("2. Прочитать результаты по критерию"):
            aggregates = p2p_endpoint.get_aggregates(work["work_id"])

        with allure.step("3. Убедиться, что ответы выводятся списком без усреднения"):
            comment_values = aggregates["comment"]
            assert isinstance(comment_values, list)
            assert set(texts) == set(comment_values)

    @allure.title("При смешанных количественных и качественных критериях доступны оба вида результатов")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_mixed_numeric_and_text_criteria_both_available(self, submitted_work, created_user, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Настроить форму с числовым и текстовым критерием, получить проверки"):
            work = submitted_work()
            p2p_endpoint.set_criteria(work["homework"]["id"], [
                {"id": "scale", "type": "scale", "label": "Оценка по шкале"},
                {"id": "comment", "type": "text", "label": "Комментарий"},
            ])
            _assign_reviewers_and_submit(p2p_endpoint, created_user, work, [
                {"scale": 4, "comment": "Автотест: хорошо"},
                {"scale": 5, "comment": "Автотест: отлично"},
            ])

        with allure.step("2. Прочитать результаты по работе"):
            aggregates = p2p_endpoint.get_aggregates(work["work_id"])

        with allure.step("3. Убедиться, что доступны и агрегированное число, и список текстов"):
            assert isinstance(aggregates["scale"], (int, float))
            assert isinstance(aggregates["comment"], list) and len(aggregates["comment"]) == 2
