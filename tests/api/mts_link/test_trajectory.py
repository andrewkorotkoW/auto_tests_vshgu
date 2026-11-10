"""Часть 14 — вебинар в индивидуальной траектории (docs/test_cases/mts_link/13_trajectory.md).

Восстановлено 10.11.2026 после живой разведки на mts-link-release-main: мероприятие
«МТС Линк» в индивидуальной траектории — это офлайн-контент пользователя
(POST /users/content/offline, список GET /users/content/offline/user-content/{user_id}
с attributes.mts_link в том же формате, что у schedule-item). Прежняя версия файла
(удалена 02.11.2026) опиралась на несуществующий /individual-trajectory/assignments/…
TC-MTS-079 («снятие после проведённого вебинара не удаляет его») требует реально
проведённого эфира с ведущим — остаётся ручным шагом ПМИ, автотеста нет.

Стенд — реальный прод-аккаунт МТС Линк: лектор только Вера, дата завтра, все имена с
«[ТЕСТ]» (mts_link_safe_schedule_item_kwargs); каждое назначение создаёт настоящий
вебинар, фикстура снимает его после теста.
"""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 14: вебинар в индивидуальной траектории")
@pytest.mark.api
@pytest.mark.mts_link
class TestTrajectory:
    @allure.title("Назначение в ИТ создаёт отдельный вебинар")
    @pytest.mark.smoke
    def test_it_assignment_creates_dedicated_webinar(self, mts_link_endpoint, created_it_event, created_schedule_item):
        """Предусловие: есть потоковое мероприятие «МТС Линк» (для сравнения) и слушатель."""
        with allure.step("1. Создать потоковое мероприятие «МТС Линк» и дождаться синхронизации"):
            stream_item = created_schedule_item(item_type="mts_link", url="", name="[ТЕСТ] ИТ-сравнение: поток")
            assert mts_link_endpoint.wait_for_part_status(stream_item, "creation") == "synced"
            stream_status = mts_link_endpoint.get_integration_status(stream_item)

        with allure.step("2. Назначить мероприятие «МТС Линк» слушателю в индивидуальной траектории"):
            it = created_it_event(name="[ТЕСТ] ИТ: отдельный вебинар")
            assert mts_link_endpoint.wait_for_it_part_status(it["user_id"], it["content_id"], "creation") == "synced"
            it_status = mts_link_endpoint.get_it_integration_status(it["user_id"], it["content_id"])
            it_event = mts_link_endpoint.get_it_event(it["user_id"], it["content_id"])

        with allure.step("3. Под назначение создан свой вебинар, отличный от потокового"):
            assert it_status.get("mts_webinar_id"), f"у мероприятия ИТ нет mts_webinar_id: {it_status}"
            assert it_status["mts_webinar_id"] != stream_status.get("mts_webinar_id")
            assert it_event["attributes"].get("url"), "у мероприятия ИТ нет ссылки на вебинар"
            assert it_event["attributes"]["url"] != stream_item["attributes"].get("url")
            assert it_event["attributes"].get("type") == "mts_link_webinar"

    @allure.title("На вебинар в ИТ регистрируется только этот слушатель")
    def test_it_webinar_has_single_registered_listener(self, mts_link_endpoint, created_it_event, created_user):
        """Предусловие: вебинар под назначение в ИТ создан; есть второй слушатель без назначения."""
        with allure.step("1. Назначить мероприятие «МТС Линк» слушателю A в ИТ и дождаться сверки участников"):
            it = created_it_event(name="[ТЕСТ] ИТ: единственный участник")
            assert mts_link_endpoint.wait_for_it_part_status(it["user_id"], it["content_id"], "creation") == "synced"
            assert mts_link_endpoint.wait_for_it_part_status(it["user_id"], it["content_id"], "participants") == "success"

        with allure.step("2. Мероприятие есть в ИТ слушателя A, участники сверены без ручной регистрации"):
            # attributes.is_registered здесь остаётся False — это отметка регистрации/посещения
            # в ЛМС (как «Отметить регистрацию» у потокового мероприятия), а не факт регистрации
            # в МТС Линк: participants_sync_status=success приходит без неё (живьём 10.11.2026).
            # Детализации по участникам у API нет — «ровно один участник» сверяется вручную в
            # кабинете МТС Линк / mts_webinar_participants (см. 13_trajectory.md).
            event = mts_link_endpoint.get_it_event(it["user_id"], it["content_id"])
            assert event is not None and event["attributes"].get("type") == "mts_link_webinar"

        with allure.step("3. У слушателя B этого мероприятия в ИТ нет"):
            other = created_user()
            assert mts_link_endpoint.get_it_event(other["id"], it["content_id"]) is None

    @allure.title("Снятие назначения до вебинара удаляет его целиком")
    def test_removing_it_assignment_before_webinar_deletes_it(self, mts_link_endpoint, created_it_event):
        """Предусловие: назначение в ИТ с созданным, ещё не проведённым вебинаром (дата — завтра)."""
        with allure.step("1. Назначить мероприятие «МТС Линк» в ИТ и дождаться синхронизации"):
            it = created_it_event(name="[ТЕСТ] ИТ: снятие до вебинара")
            assert mts_link_endpoint.wait_for_it_part_status(it["user_id"], it["content_id"], "creation") == "synced"

        with allure.step("2. Снять мероприятие с индивидуальной траектории (как админка: detach-activities)"):
            assert mts_link_endpoint.delete_it_event(it["user_id"], it["content_id"]) is True

        with allure.step("3. Мероприятие пропало из ИТ слушателя сразу, без ожидания МТС Линк"):
            assert mts_link_endpoint.wait_for_it_event_removed(it["user_id"], it["content_id"], timeout=30) is True
