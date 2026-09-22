import json

import allure
import pytest

from api.helpers.data_generator import generate_buk_user_payload
from api.helpers.expectations import expect_status
from utils.logger import logger

# БУК и LPD есть только на stage — на других окружениях эти тесты пропускаются (см. conftest, маркер env)
pytestmark = pytest.mark.env("stage")


def _attach(title: str, data) -> None:
    allure.attach(json.dumps(data, indent=2, ensure_ascii=False), title, allure.attachment_type.JSON)


@allure.feature("External BUK API")
@allure.story("Users sync")
class TestExternalBukUsersAPI:
    """Входящий REST БУК → АСУО: POST/PUT/DELETE /api/v1/external/buk/users (контракт § 2, § 4)."""

    @allure.title("POST: приём пользователя → recorded, затем автосопоставление по email → synced")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.tag("api", "positive", "smoke")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_post_auto_match_by_email(self, external_buk_endpoint, created_user):
        with allure.step("1. Создать пользователя АСУО через админ-API"):
            user = created_user()
            logger.info(f"Пользователь АСУО: id={user['id']} {user['email']}")

        with allure.step("2. POST в /external/buk/users с email и ФИО как в АСУО"):
            payload = generate_buk_user_payload(from_user=user)
            _attach("POST запрос", payload)
            result = external_buk_endpoint.post_user(payload)
            _attach("POST ответ", result)
            assert result["success"] is True, result
            assert result["user"]["sync_status"] == "recorded", result
            assert result["user"]["user_id"] is None
            assert result["user"]["profile_data"]["first_name"] == user["name"]

        with allure.step("3. Дождаться асинхронного сопоставления"):
            result = external_buk_endpoint.wait_for_match(payload)
            _attach("Итог сопоставления", result)
            assert result["user"]["sync_status"] == "synced", result
            assert result["user"]["user_id"] == user["id"]
            assert result["user"]["synced_at"] is not None
            assert result["user"]["unsynced_at"] is None

    @allure.title("POST повторно с тем же buk_user_id → already_exists")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_post_duplicate_already_exists(self, external_buk_endpoint, created_user):
        user = created_user()
        payload = generate_buk_user_payload(from_user=user)
        first = external_buk_endpoint.post_user(payload)
        assert first["success"] is True, first

        with allure.step("Повторный POST тем же buk_user_id"):
            second = external_buk_endpoint.post_user(payload)
            _attach("Ответ на дубль", second)
            assert second["success"] is False, second
            assert second["error"]["code"] == "already_exists", second

    @allure.title("PUT по неизвестному buk_user_id → not_found")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_put_unknown_user_not_found(self, external_buk_endpoint):
        payload = generate_buk_user_payload()
        result = external_buk_endpoint.put_user(payload)
        _attach("Ответ", result)
        assert result["success"] is False, result
        assert result["error"]["code"] == "not_found", result
        assert payload["buk_user_id"] in result["error"]["message"]

    @allure.title("POST с email, которого нет в АСУО → pending; PUT с верным email → synced")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_pending_then_put_corrects_email(self, external_buk_endpoint, created_user):
        user = created_user()

        with allure.step("1. POST с несуществующим email"):
            payload = generate_buk_user_payload(from_user=user, email=f"missing_{user['email']}")
            result = external_buk_endpoint.post_user(payload)
            assert result["user"]["sync_status"] == "recorded", result
            result = external_buk_endpoint.wait_for_match(payload)
            _attach("После POST", result)
            assert result["user"]["sync_status"] == "pending", result
            assert result["user"]["user_id"] is None

        with allure.step("2. PUT с уточнённым email → повторное сопоставление"):
            payload["email"] = user["email"]
            result = external_buk_endpoint.put_and_wait(payload)
            _attach("После PUT", result)
            assert result["user"]["sync_status"] == "synced", result
            assert result["user"]["user_id"] == user["id"]

    @allure.title("Ручное сопоставление по user_id при несовпавшем email → synced_manual")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_manual_match_by_user_id(self, external_buk_endpoint, created_user):
        user = created_user()
        payload = generate_buk_user_payload(email=f"other_{user['email']}", user_id=user["id"])
        result = external_buk_endpoint.post_user(payload)
        assert result["success"] is True, result
        assert result["user"]["profile_data"]["requested_user_id"] == user["id"], result

        result = external_buk_endpoint.wait_for_match(payload)
        _attach("Итог", result)
        assert result["user"]["sync_status"] == "synced_manual", result
        assert result["user"]["user_id"] == user["id"]

    @allure.title("Ручное сопоставление с user_id администратора → rejected")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_manual_match_admin_rejected(self, external_buk_endpoint, api_client):
        with allure.step("Узнать id текущего администратора"):
            resp = api_client.get("/auth/me")
            expect_status(resp, 200)
            me = resp.json()["data"]
            admin_id = int(me["id"])
            _attach("auth/me", me)

        payload = generate_buk_user_payload(user_id=admin_id)  # email случайный — по email не найдётся
        result = external_buk_endpoint.post_user(payload)
        assert result["success"] is True, result
        result = external_buk_endpoint.wait_for_match(payload)
        _attach("Итог", result)
        assert result["user"]["sync_status"] == "rejected", result
        assert result["user"]["user_id"] is None

    @allure.title("Второй buk_user_id на уже связанного пользователя → conflict; связь 1:1 сохраняется")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_second_buk_id_same_user_conflict(self, external_buk_endpoint, created_user):
        user = created_user()
        first = generate_buk_user_payload(from_user=user)
        external_buk_endpoint.post_user(first)
        linked = external_buk_endpoint.wait_for_match(first)
        assert linked["user"]["sync_status"] == "synced", linked

        with allure.step("POST другого buk_user_id с тем же email"):
            second = generate_buk_user_payload(from_user=user)
            external_buk_endpoint.post_user(second)
            result = external_buk_endpoint.wait_for_match(second)
            _attach("Итог второго", result)
            assert result["user"]["sync_status"] == "conflict", result

        with allure.step("Первая связь не изменилась"):
            still = external_buk_endpoint.put_user(first)
            assert still["user"]["sync_status"] == "synced", still
            assert still["user"]["user_id"] == user["id"]

    @allure.title("PUT с другим user_id для synced-пользователя → conflict, профиль и связь не меняются")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_put_other_user_id_on_synced_conflict(self, external_buk_endpoint, created_user):
        user, other = created_user(), created_user()
        payload = generate_buk_user_payload(from_user=user)
        external_buk_endpoint.post_user(payload)
        linked = external_buk_endpoint.wait_for_match(payload)
        assert linked["user"]["sync_status"] == "synced", linked

        with allure.step("PUT с чужим user_id и другим именем"):
            changed = dict(payload, user_id=other["id"], first_name="Изменённое")

        with allure.step("Итог обработки: conflict, связь осталась с первым пользователем"):
            result = external_buk_endpoint.put_and_wait(changed)
            _attach("Итог", result)
            assert result["user"]["sync_status"] == "conflict", result
            assert result["user"]["user_id"] == user["id"], "связь должна остаться с первым пользователем"

    @allure.title("PUT для synced не перезаписывает мастер-профиль АСУО")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_put_synced_does_not_overwrite_profile(self, external_buk_endpoint, created_user, api_client):
        user = created_user()
        payload = generate_buk_user_payload(from_user=user)
        external_buk_endpoint.post_user(payload)
        linked = external_buk_endpoint.wait_for_match(payload)
        assert linked["user"]["sync_status"] == "synced", linked

        with allure.step("PUT с другим ФИО"):
            result = external_buk_endpoint.put_and_wait(dict(payload, first_name="Пётр", last_name="Петров"))
            assert result["user"]["sync_status"] == "synced", result
            assert result["user"]["user_id"] == user["id"]

        with allure.step("Профиль в АСУО остался прежним"):
            resp = api_client.get(f"/users/{user['id']}")
            expect_status(resp, 200)
            attrs = resp.json()["data"]["attributes"]
            assert attrs["name"] == user["name"] and attrs["surname"] == user["surname"], attrs

    @allure.title("DELETE: разрыв связи → unsynced/deleted_in_buk, аккаунт АСУО остаётся; повтор идемпотентен")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "positive", "smoke")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_delete_unsync_idempotent(self, external_buk_endpoint, created_user, api_client):
        user = created_user()
        payload = generate_buk_user_payload(from_user=user)
        external_buk_endpoint.post_user(payload)
        linked = external_buk_endpoint.wait_for_match(payload)
        assert linked["user"]["sync_status"] == "synced", linked

        with allure.step("1. DELETE"):
            result = external_buk_endpoint.delete_user(payload["buk_user_id"])
            _attach("DELETE ответ", result)
            assert result["success"] is True, result
            assert result["user"]["sync_status"] == "unsynced", result
            assert result["user"]["unsync_reason"] == "deleted_in_buk", result
            assert result["user"]["unsynced_at"] is not None

        with allure.step("2. Аккаунт в АСУО сохранился"):
            expect_status(api_client.get(f"/users/{user['id']}"), 200)

        with allure.step("3. Повторный DELETE — успех с тем же состоянием"):
            again = external_buk_endpoint.delete_user(payload["buk_user_id"])
            assert again["success"] is True, again
            assert again["user"]["sync_status"] == "unsynced", again

    @allure.title("После DELETE перепривязка к другому пользователю через PUT с user_id")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_relink_after_delete(self, external_buk_endpoint, created_user):
        user, other = created_user(), created_user()
        payload = generate_buk_user_payload(from_user=user)
        external_buk_endpoint.post_user(payload)
        assert external_buk_endpoint.wait_for_match(payload)["user"]["sync_status"] == "synced"

        with allure.step("DELETE, затем PUT с новым user_id"):
            external_buk_endpoint.delete_user(payload["buk_user_id"])
            relink = generate_buk_user_payload(from_user=other, buk_user_id=payload["buk_user_id"], user_id=other["id"])
            result = external_buk_endpoint.put_and_wait(relink)
            _attach("Итог", result)
            assert result["user"]["sync_status"] in ("synced", "synced_manual"), result
            assert result["user"]["user_id"] == other["id"]

    @allure.title("DELETE неизвестного buk_user_id → not_found")
    @allure.severity(allure.severity_level.MINOR)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_delete_unknown_not_found(self, external_buk_endpoint):
        result = external_buk_endpoint.delete_user(f"buk-unknown-{__import__('time').time_ns()}")
        _attach("Ответ", result)
        assert result["success"] is False, result
        assert result["error"]["code"] == "not_found", result

    @allure.title("POST без обязательного email → поэлементная ошибка валидации")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_post_without_email_validation_error(self, external_buk_endpoint):
        payload = generate_buk_user_payload()
        payload.pop("email")
        resp = external_buk_endpoint.client.post(external_buk_endpoint.PATH, json={"users": [payload]})
        allure.attach(str(resp.status_code), "Status", allure.attachment_type.TEXT)
        allure.attach(resp.text, "Body", allure.attachment_type.TEXT)
        if resp.status_code == 200:
            item = resp.json()["users"][0]
            assert item["success"] is False, item
            assert item["error"]["code"].lower() == "validation_error", item
        else:
            expect_status(resp, 422)

    @allure.title("Без токена → 403 Unauthorized")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "security")
    @pytest.mark.api
    def test_without_token_forbidden(self, api_client):
        resp = api_client.post("/external/buk/users", json={"users": [generate_buk_user_payload()]})
        expect_status(resp, 403)
        assert resp.json().get("message") == "Unauthorized", resp.text

    @allure.title("Пакет из двух пользователей: поэлементные результаты в порядке запроса")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_batch_two_users(self, external_buk_endpoint, created_user):
        u1, u2 = created_user(), created_user()
        p1, p2 = generate_buk_user_payload(from_user=u1), generate_buk_user_payload(from_user=u2)
        results = external_buk_endpoint.post_users([p1, p2])
        _attach("Ответ", results)
        assert [r["buk_user_id"] for r in results] == [p1["buk_user_id"], p2["buk_user_id"]]
        assert all(r["success"] and r["user"]["sync_status"] == "recorded" for r in results), results
