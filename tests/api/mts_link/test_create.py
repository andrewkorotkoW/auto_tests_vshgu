"""Часть 1 — фоновое создание вебинара при создании мероприятия (docs/test_cases/mts_link/02_create.md).

02.11.2026: 3 из 5 тестов удалены при сведении api/endpoints/mts_link.py с реальным
контрактом (живая разведка на mts-link-release-main) — сценарии с управляемой
ошибкой/задержкой МТС Линк («мок отвечает ошибкой», «мок сначала отвечает ошибкой,
затем успехом») непроверяемы на реальном проде (нет мока, нет контроля над
поведением МТС Линк), а «части 2–5 не стартуют, пока вебинар не создан» прямо
противоречит наблюдаемому: живьём participants/lecturers/files_sync_status уже были
"success", пока webinar_status ещё был "syncing" — удалённую проверку порядка
частей не починить переименованием, сама посылка неверна. См.
docs/test_cases/mts_link/16_prod_safe_run.md."""
import os
import time
from datetime import datetime, timedelta

import allure
import pytest

from utils.logger import logger
from api.helpers.data_generator import MTS_LINK_SAFE_TEACHER_ID


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 1: создание вебинара")
@pytest.mark.api
@pytest.mark.mts_link
class TestCreate:
    @allure.title("Мероприятие создаётся в ЛМС сразу, не дожидаясь МТС Линк")
    @pytest.mark.smoke
    def test_event_created_immediately_status_in_progress(
        self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint
    ):
        """Предусловие: мероприятие только что создано."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert item["id"] is not None

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert fetched["id"] == item["id"]

        status = mts_link_endpoint.get_part_status(item, "creation")
        assert status == "syncing", status

    @allure.title("Фоновое создание вебинара завершилось успешно")
    def test_event_creation_success_saves_ids_and_url(
        self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint
    ):
        """Предусловие: мероприятие «МТС Линк» создано, фон досинхронизировался."""
        item = created_schedule_item(item_type="mts_link", url="")

        status = mts_link_endpoint.wait_for_part_status(item, "creation")
        assert status == "synced", status

        integration = mts_link_endpoint.get_integration_status(item)
        assert integration.get("mts_webinar_id")

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert fetched["attributes"].get("url")

    @allure.title("Негативный: создание вебинара с датой в прошлом не проходит")
    def test_creating_webinar_in_the_past_is_rejected(
        self, api_client, created_module, schedule_items_endpoint, mts_link_endpoint
    ):
        """Предусловие: -. date_time_from/to вчера, а не завтра (mts_link_safe_schedule_item_kwargs
        здесь не годится — он нарочно ставит дату в будущем). Если бэкенд всё же создаст
        мероприятие, оно реально уйдёт в МТС Линк на боевом аккаунте — явно удаляем в этом
        случае сами, с тем же grace-ожиданием, что в созданном_schedule_item (см. корневой
        conftest.py), прежде чем провалить тест."""
        module = created_module()
        yesterday = datetime.now() - timedelta(days=1)
        payload = mts_link_endpoint.build_event_payload(
            teacher_ids=[MTS_LINK_SAFE_TEACHER_ID],
            region_id=1,
            region_name="Москва",
            date_time_from=yesterday.strftime("%Y-%m-%dT11:00"),
            date_time_to=yesterday.strftime("%Y-%m-%dT11:10"),
        )

        resp = api_client.post(
            f"/programs/{module['program_id']}/streams/{module['stream_id']}"
            f"/modules/{module['id']}/schedule-items",
            json=payload,
        )

        if resp.status_code in (200, 201):
            item_id = resp.json()["data"]["id"]
            logger.warning(f"Вебинар с датой в прошлом создан (id={item_id}) — удаляю и жду grace-паузу")
            schedule_items_endpoint.delete(module["program_id"], module["stream_id"], module["id"], item_id)
            time.sleep(int(os.getenv("MTS_LINK_DELETE_GRACE_SECONDS", "60")))
            pytest.fail(
                f"Создание вебинара с date_time_from={yesterday:%Y-%m-%dT%H:%M} (вчера) "
                f"не должно проходить, но вернуло {resp.status_code} и реально создало "
                f"мероприятие {item_id} в МТС Линк (удалено)"
            )

        assert resp.status_code == 422, f"Ожидали 422 (валидация даты), получили {resp.status_code}: {resp.text[:300]}"
        body = resp.text
        assert "/srv/app" not in body and '"trace"' not in body, (
            f"В ответе 422 не должно быть стектрейса/серверных путей: {body[:300]}"
        )
