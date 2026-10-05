import allure
import pytest

from api.client import ApiClient
from api.endpoints.tickets import TicketsEndpoint
from api.helpers.data_generator import generate_ticket_payload
from utils.logger import logger


@allure.feature("Хелпдеск: Тикеты")
@allure.story("Список обращений в админке")
class TestTicketsApi:

    @allure.title("POST /admin/ticket/search — список тикетов подгружается и фильтруется по теме")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_list_tickets(self, env, user_session, helpdesk_endpoint):
        # Тикеты создаются через пользовательский портал (/api/v1/tickets, api.endpoints.tickets),
        # админка хелпдеска — их read-only витрина (список/поиск), отдельного create там нет.
        portal_client = ApiClient(session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name)
        tickets_endpoint = TicketsEndpoint(portal_client)
        payload = generate_ticket_payload()
        tickets_endpoint.create(payload)
        ticket = tickets_endpoint.find_by_title(payload["title"])
        assert ticket is not None, f"Созданное обращение не найдено в my-tickets: {payload['title']!r}"

        try:
            with allure.step("POST /admin/ticket/search без фильтра — непустой список"):
                full_data = helpdesk_endpoint.list_tickets()
                assert "data" in full_data
                assert full_data.get("recordsTotal", 0) >= 1

            with allure.step("POST /admin/ticket/search с search[value] по теме — список сужается до созданного тикета"):
                filtered_data = helpdesk_endpoint.list_tickets(search_value=payload["title"])
                assert filtered_data["recordsFiltered"] >= 1, (
                    f"Обращение с темой {payload['title']!r} не найдено в админке хелпдеска"
                )
                assert filtered_data["recordsFiltered"] <= full_data["recordsTotal"]
                row_html = "".join(filtered_data["data"][0])
                assert payload["title"] in row_html
        finally:
            try:
                tickets_endpoint.close(ticket["id"])
            except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
                logger.warning(f"Не удалось закрыть обращение {ticket['id']}: {exc}")
