"""p2p / регресс обычного ПЗ при выключенной взаимопроверке — API-часть
(docs/test_cases/p2p/16_regression.md, TC-P2P-110, 111).

Контракт p2p не подтверждён, но эти два кейса проверяют, что уже существующее
поведение обычного ПЗ (не затронутое p2p) не меняется. Тесты пропускаются без
P2P_READY, см. tests/api/p2p/conftest.py — до появления ветки нет смысла гонять их
отдельно от остального пакета p2p.
"""
import allure
import pytest


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Регресс обычного ПЗ без взаимопроверки")
class TestRegression:

    @allure.title("Индивидуальное назначение ПЗ проходит стандартный сценарий без взаимопроверки")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_personal_assignment_keeps_standard_flow_without_p2p(self, created_user, created_homework,
                                                                    assignments_endpoint, homework_endpoint,
                                                                    p2p_client_for):
        """Предусловие: -"""
        with allure.step("1. Назначить ПЗ пользователю напрямую (без потока), без включения взаимопроверки"):
            student = created_user()
            homework = created_homework()
            assigned_ok = assignments_endpoint.assign_to_individual([homework["id"]], [student["id"]])
            assert assigned_ok

        with allure.step("2. Пройти сдачу и проверку, как в test_complete_and_review_personal_assignment.py"):
            student_client, _ = p2p_client_for(student)
            resp = student_client.post(
                f"/homework/{homework['id']}/answers",
                json={"data": {"attributes": {"text": "Автотест: ответ по индивидуальному назначению"}}},
            )
            assert resp.status_code in (200, 201)

        with allure.step("3. Убедиться, что статус ПЗ читается как для обычного (не-P2P) сценария"):
            status = homework_endpoint.get_status(homework["id"], student["id"])
            assert status == "Сдано"

    @allure.title("Ограничение «одно и то же ПЗ нельзя назначить в поток/программу дважды» не меняется")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_single_homework_per_program_restriction_unchanged(self, created_stream, created_module,
                                                                  created_homework, assignments_endpoint,
                                                                  p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Назначить P2P-ПЗ в поток программы"):
            stream = created_stream()
            module = created_module(program_id=stream["program_id"], stream_id=stream["id"])
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            first_ok = assignments_endpoint.assign_content_to_module(
                stream["program_id"], stream["id"], module["id"], [homework["id"]]
            )
            assert first_ok

        with allure.step("2. Попытаться повторно назначить то же ПЗ в другой поток той же программы"):
            second_stream = created_stream(program_id=stream["program_id"])
            second_module = created_module(program_id=stream["program_id"], stream_id=second_stream["id"])
            second_ok = assignments_endpoint.assign_content_to_module(
                stream["program_id"], second_stream["id"], second_module["id"], [homework["id"]]
            )
            assert not second_ok, "Ограничение на повторное назначение ПЗ в программу должно действовать так же, как для обычного ПЗ"
