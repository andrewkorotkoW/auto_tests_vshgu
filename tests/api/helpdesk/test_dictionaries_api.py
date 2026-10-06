"""API: CRUD одной записи для каждого из 7 справочников хелпдеска — один общий паттерн
(api.endpoints.helpdesk.HelpdeskDictEndpoint), docs/test_cases/helpdesk/tickets.md
TC-HELPDESK_TICKETS-003..009. Создание/удаление — только свои Автотест_*/auto_test_*
записи, системные справочники не трогаем.

group_id обязателен для 6 из 7 справочников (всех, кроме чёрного списка — см. docstring
HelpdeskDictEndpoint в api/endpoints/helpdesk.py: без него сервер отвечает 422), поэтому
используем ID уже существующей системной группы «Личная группа»
(helpdesk_existing_group_id, tests/api/helpdesk/conftest.py) — группа только читается,
не создаётся/не редактируется/не удаляется.

ОБНАРУЖЕННЫЙ ДЕФЕКТ (подтверждён живым прогоном на develop, не правим — api/endpoints/
helpdesk.py защищён условиями задачи): POST /admin/blacklist (создание записи чёрного
списка с единственным полем формы `email`) стабильно отвечает 500 ещё на этапе валидации
уникальности адреса: `SQLSTATE[22P02]: Invalid text representation: invalid input syntax
for type bigint: "deleted_at"` на запросе `select count(*) ... from "blacklist" ...` —
бэкенд некорректно связывает параметры SQL-запроса проверки уникальности (воспроизведено
и напрямую через requests с полным набором полей формы, включая скрытый `created_by`, и
через тот же сценарий в UI — tests/ui/helpdesk/admin/test_dictionaries.py). Запись в БД не
создаётся ни разу (find_by_value после 500 стабильно возвращает None)."""
import allure
import pytest

from api.helpers.data_generator import unique_suffix
from utils.logger import logger

_BLACKLIST_500_DEFECT_REASON = (
    "Дефект стенда (не правим — api/endpoints/helpdesk.py защищён условиями задачи): "
    "POST /admin/blacklist стабильно отвечает 500 на этапе валидации уникальности email "
    "('SQLSTATE[22P02]: invalid input syntax for type bigint: \"deleted_at\"' на SQL-запросе "
    "'select count(*) ... from blacklist ...') — бэкенд некорректно связывает параметры "
    "запроса проверки уникальности. Запись в БД не создаётся, воспроизведено и напрямую "
    "через requests с полным набором полей формы (включая скрытый created_by), и через UI."
)

_DICT_CASES = [
    pytest.param("category", "Категории", "Значение", True, id="category"),
    pytest.param("tag", "Теги", "Значение", True, id="tag"),
    pytest.param("applicant_type", "Типы заявителей", "Значение", True, id="applicant_type"),
    pytest.param("request_source", "Типы контактов", "Значение", True, id="request_source"),
    pytest.param("request_type", "Типы обращений", "Значение", True, id="request_type"),
    pytest.param("processing_result", "Типы результата", "Значение", True, id="processing_result"),
    pytest.param(
        "blacklist",
        "Черный список адресов",
        "Почтовый адрес",
        False,
        id="blacklist",
        marks=pytest.mark.xfail(strict=False, reason=_BLACKLIST_500_DEFECT_REASON),
    ),
]


def _generate_value(key: str, field_label: str) -> str:
    suffix = unique_suffix()
    if field_label == "Почтовый адрес":
        return f"auto_test_blacklist_{suffix}@autotest.invalid"
    return f"Автотест_{key}_{suffix}"


@allure.feature("Хелпдеск: Справочники")
@allure.story("CRUD записи справочника (API)")
class TestDictionariesApi:

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.parametrize("key,dict_label,field_label,needs_group", _DICT_CASES)
    def test_dictionary_crud(
        self, helpdesk_endpoint, helpdesk_existing_group_id, key, dict_label, field_label, needs_group
    ):
        allure.dynamic.title(
            f"API: справочник «{dict_label}» (поле «{field_label}») — создание, "
            "редактирование и удаление записи"
        )
        dict_ep = helpdesk_endpoint.dict_endpoint(key)
        group_id = helpdesk_existing_group_id if needs_group else None
        value = _generate_value(key, field_label)

        with allure.step(f"Создать запись «{value}»"):
            resp = dict_ep.create(value, group_id)
            assert resp.status_code < 400, f"Не удалось создать запись: {resp.status_code} {resp.text[:300]}"

        with allure.step("Найти созданную запись в списке"):
            found = dict_ep.find_by_value(value)
            assert found is not None and found["id"], f"Созданная запись {value!r} не найдена в списке"
            item_id = found["id"]

        deleted = False
        try:
            new_value = f"{value}_upd"
            with allure.step("Отредактировать значение записи"):
                resp = dict_ep.update(item_id, new_value, group_id)
                assert resp.status_code < 400, f"Не удалось обновить запись: {resp.status_code} {resp.text[:300]}"

            with allure.step("Изменение сохранилось"):
                found_updated = dict_ep.find_by_value(new_value)
                assert found_updated is not None and found_updated["id"] == item_id, (
                    "Изменённое значение не найдено в списке"
                )

            with allure.step("Удалить запись"):
                resp = dict_ep.delete(item_id)
                assert resp.status_code < 400, f"Не удалось удалить запись: {resp.status_code} {resp.text[:300]}"
                deleted = True

            with allure.step("Запись пропала из списка после удаления"):
                assert dict_ep.find_by_value(new_value) is None, "Запись всё ещё видна в списке после удаления"
        finally:
            if not deleted:
                try:
                    dict_ep.delete(item_id)
                except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
                    logger.warning(f"Не удалось удалить запись справочника {key} id={item_id}: {exc}")
