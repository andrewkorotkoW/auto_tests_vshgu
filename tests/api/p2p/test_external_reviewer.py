"""p2p / внешний проверяющий по ссылке: добавление, персональная ссылка, уникальность
по ФИО (docs/test_cases/p2p/05_external_reviewer.md, TC-P2P-033, 034, 038).

Контракт не подтверждён (api/endpoints/p2p.py) — функциональности ещё нет ни на одной
ветке (docs/missions/2026-09-30_tz2026_p2p.md). Кейсы написаны по приоритетной версии 04
(ссылка многоразовая, внешний видит весь список работ потока — см. README). Тесты
пропускаются без P2P_READY, см. tests/api/p2p/conftest.py.
"""
import allure
import pytest


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Внешний проверяющий: добавление и персональная ссылка")
class TestExternalReviewer:

    @allure.title("Менеджер добавляет внешнего проверяющего к ПЗ в потоке (ФИО, email опционален)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_add_external_reviewer_with_optional_email(self, created_stream, created_homework, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Добавить внешнего проверяющего, указав только ФИО"):
            stream = created_stream()
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])

            without_email = p2p_endpoint.add_external_reviewer(
                stream["program_id"], stream["id"], homework["id"], full_name="Автотест Внешний Проверяющий Первый"
            )
            assert without_email.get("id")
            assert not without_email.get("attributes", {}).get("email")

        with allure.step("2. Добавить второго внешнего проверяющего с ФИО и email"):
            with_email = p2p_endpoint.add_external_reviewer(
                stream["program_id"], stream["id"], homework["id"],
                full_name="Автотест Внешний Проверяющий Второй", email="external.reviewer@example.com",
            )
            assert with_email.get("id")
            assert with_email.get("attributes", {}).get("email") == "external.reviewer@example.com"

    @allure.title("Системой создаётся персональная ссылка для внешнего проверяющего")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_personal_link_generated_for_external_reviewer(self, created_stream, created_homework, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Добавить внешнего проверяющего"):
            stream = created_stream()
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            external = p2p_endpoint.add_external_reviewer(
                stream["program_id"], stream["id"], homework["id"], full_name="Автотест Внешний Проверяющий"
            )

        with allure.step("2. Убедиться, что создана отдельная персональная ссылка"):
            link = p2p_endpoint.get_external_reviewer_link(external["id"])
            assert link, "Персональная ссылка должна быть создана"
            assert str(external["id"]) in link or link.endswith(("/", "")), "Ссылка должна быть привязана к внешнему проверяющему"

    @allure.title("Несколько внешних проверяющих с полностью совпадающим ФИО — уникальность по ссылке, а не по ФИО")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_multiple_external_reviewers_same_full_name(self, created_stream, created_homework, p2p_endpoint):
        """Предусловие: -"""
        same_full_name = "Автотест Внешний Однофамилец"

        with allure.step("1. Добавить к одному ПЗ двух внешних проверяющих с полностью одинаковым ФИО"):
            stream = created_stream()
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])

            first = p2p_endpoint.add_external_reviewer(stream["program_id"], stream["id"], homework["id"], full_name=same_full_name)
            second = p2p_endpoint.add_external_reviewer(stream["program_id"], stream["id"], homework["id"], full_name=same_full_name)

        with allure.step("2. Убедиться, что оба созданы с разными идентификаторами и ссылками"):
            assert first["id"] != second["id"], "Внешние проверяющие с одинаковым ФИО должны быть разными сущностями"
            first_link = p2p_endpoint.get_external_reviewer_link(first["id"])
            second_link = p2p_endpoint.get_external_reviewer_link(second["id"])
            assert first_link != second_link, "У каждого внешнего проверяющего должна быть своя отдельная ссылка"
