"""p2p / настройки ПЗ в потоке: участники, режим распределения, лимиты
(docs/test_cases/p2p/02_stream_settings.md, TC-P2P-015..019).

Контракт не подтверждён (api/endpoints/p2p.py) — функциональности ещё нет ни на одной
ветке (docs/missions/2026-09-30_tz2026_p2p.md). Тесты пропускаются без P2P_READY, см.
tests/api/p2p/conftest.py.
"""
import allure
import pytest


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Настройки P2P-ПЗ в потоке")
class TestStreamSettings:

    @allure.title("В потоке задаётся список участников взаимопроверки из слушателей этого потока")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_p2p_participants_limited_to_stream_listeners(self, created_stream, created_homework, created_user,
                                                            assignments_endpoint, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Назначить P2P-ПЗ в поток и указать список участников из слушателей потока"):
            stream = created_stream()
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            listener = created_user()
            assignments_endpoint.assign(stream["program_id"], stream["id"], [listener["id"]])

            result = p2p_endpoint.set_stream_participants(
                stream["program_id"], stream["id"], homework["id"], [listener["id"]]
            )
            assert result

        with allure.step("2. Убедиться, что пользователя вне потока в участники добавить нельзя"):
            outsider = created_user()
            resp = p2p_endpoint.client.put(
                f"/programs/{stream['program_id']}/streams/{stream['id']}/content/{homework['id']}/peer-review/participants",
                json={"data": {"attributes": {"user_ids": [listener["id"], outsider["id"]]}}},
            )
            assert resp.status_code in (400, 422), (
                f"Добавление пользователя вне потока должно быть отклонено, получили {resp.status_code}"
            )

    @allure.title("В потоке можно включить ручной режим распределения работ")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_enable_manual_distribution_mode(self, created_stream, created_homework, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. В настройках P2P-ПЗ в потоке выбрать ручной режим распределения"):
            stream = created_stream()
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            result = p2p_endpoint.set_distribution_mode(stream["program_id"], stream["id"], homework["id"], "manual")
            assert result

        with allure.step("2. Убедиться, что автоматическое распределение не запускается само"):
            work_before = p2p_endpoint.list_assignments(stream["program_id"], stream["id"], homework["id"])
            assert work_before == [], "При ручном режиме назначения не должны появляться без явного действия"

    @allure.title("В потоке можно включить автоматический режим распределения работ")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_enable_automatic_distribution_mode(self, created_stream, created_homework, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. В настройках P2P-ПЗ в потоке выбрать автоматический режим распределения"):
            stream = created_stream()
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            result = p2p_endpoint.set_distribution_mode(stream["program_id"], stream["id"], homework["id"], "auto")
            assert result

    @allure.title("Настройка «Количество работ для проверки одним слушателем» в автоматическом режиме")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_configure_works_per_listener_count(self, created_stream, created_homework, p2p_endpoint):
        """Предусловие: включён автоматический режим распределения."""
        with allure.step("1. Включить автоматический режим распределения"):
            stream = created_stream()
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            p2p_endpoint.set_distribution_mode(stream["program_id"], stream["id"], homework["id"], "auto")

        with allure.step("2. Задать «Количество работ для проверки одним слушателем» = 2"):
            result = p2p_endpoint.set_works_per_listener(stream["program_id"], stream["id"], homework["id"], 2)
            assert result

    @allure.title("Настройка минимального количества peer-проверок на одну работу")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.p2p
    def test_configure_minimum_reviews_per_work(self, created_stream, created_homework, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Задать минимальное количество peer-проверок на одну работу"):
            stream = created_stream()
            homework = created_homework()
            p2p_endpoint.enable_peer_review(homework["id"])
            result_min = p2p_endpoint.set_minimum_reviews_per_work(stream["program_id"], stream["id"], homework["id"], 2)
            assert result_min

        with allure.step("2. Убедиться, что настройка применяется независимо от режима распределения"):
            p2p_endpoint.set_distribution_mode(stream["program_id"], stream["id"], homework["id"], "manual")
            result_manual = p2p_endpoint.set_minimum_reviews_per_work(stream["program_id"], stream["id"], homework["id"], 2)
            p2p_endpoint.set_distribution_mode(stream["program_id"], stream["id"], homework["id"], "auto")
            result_auto = p2p_endpoint.set_minimum_reviews_per_work(stream["program_id"], stream["id"], homework["id"], 2)
            assert result_manual and result_auto
