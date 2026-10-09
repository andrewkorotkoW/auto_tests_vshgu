"""POST /qr-code/parse-token (docs/qr_code_ratings_recon.md, раздел «QR-код»).

Полный раунд-трип generate -> decode_qr_png -> parse-token подтверждён живым прогоном
при подготовке этой задачи (opencv QRCodeDetector, без pyzbar/zbar — см. conftest.py).
Также здесь задокументированы два дефекта, найденных тем же живым прогоном (не
исправляются согласно условию задачи — только фиксируются тестами):

1. Невалидный по структуре токен (не JWT) роняет ручку в HTTP 500 (необработанное
   исключение Lcobucci\\JWT\\Token\\InvalidTokenStructure /
   Lcobucci\\JWT\\Encoding\\CannotDecodeContent) вместо чистой 4xx-ошибки валидации.
2. Подпись JWT не проверяется вовсе: самодельный токен с произвольным payload и
   заведомо случайной подписью (ту же структуру "header.payload.signature", но
   signature не является HMAC от header.payload) успешно "парсится" и возвращает
   тот user_id, что указан в payload, — т.е. ручка доверяет содержимому токена без
   криптографической проверки подлинности. Это даёт возможность подделать QR-токен
   на произвольного пользователя.
"""
import base64
import json

import allure
import pytest


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _forge_token(user_id: int) -> str:
    header = _b64url(json.dumps({"typ": "JWT", "alg": "HS256"}).encode())
    payload = _b64url(json.dumps({"user_id": user_id, "aud": "qr-code-token"}).encode())
    bogus_signature = _b64url(b"not-a-real-hmac-signature")
    return f"{header}.{payload}.{bogus_signature}"


@allure.feature("QR-код пользователя")
@allure.story("Разбор токена QR-кода")
@pytest.mark.api
class TestQrCodeParseToken:

    @allure.title("Полный цикл: generate -> decode QR -> parse-token возвращает свой user_id")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_parse_token_full_round_trip_returns_own_user_id(
        self, env, created_user, decode_qr_png
    ):
        from api.client import ApiClient
        from api.endpoints.qr_code import QrCodeEndpoint
        from config.environments import login

        user = created_user()
        user_session = login(env, user["email"], user["password"])
        user_client = ApiClient(session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name)
        user_qr = QrCodeEndpoint(user_client)

        token = decode_qr_png(user_qr.generate_qr_code().content)
        parsed = user_qr.parse_qr_token(token)

        assert parsed == {"data": {"user_id": user["id"]}}

    @allure.title("Без token в конверте data.attributes → 422")
    @pytest.mark.parametrize("payload", [{}, {"data": {}}, {"data": {"attributes": {}}}, {"token": "x"}])
    def test_parse_token_missing_field_422(self, api_client, payload):
        resp = api_client.post("/qr-code/parse-token", json=payload)
        assert resp.status_code == 422
        assert "token" in str(resp.json().get("errors", {})).lower() or "data.attributes.token" in resp.text

    @allure.title("Анонимный запрос parse-token → 401")
    def test_parse_token_anon_401(self, anon_api_client):
        resp = anon_api_client.post(
            "/qr-code/parse-token", json={"data": {"attributes": {"token": "garbage"}}}
        )
        assert resp.status_code == 401

    @allure.title("Невалидная структура токена — известный дефект (500 вместо 4xx)")
    @pytest.mark.xfail(
        strict=False,
        reason="Известный дефект: POST /qr-code/parse-token со строкой без двух точек "
        "(не JWT) отвечает 500 (Lcobucci\\JWT\\Token\\InvalidTokenStructure: "
        "'The JWT string must have two dots') вместо 422/400 — ошибка валидации не "
        "перехватывается и наружу уходит трейс исключения.",
    )
    def test_parse_token_malformed_structure_is_validation_error(self, api_client):
        resp = api_client.post(
            "/qr-code/parse-token", json={"data": {"attributes": {"token": "garbage"}}}
        )
        assert resp.status_code in (400, 422), resp.text

    @allure.title("Токен с произвольной подписью — известный дефект (подпись JWT не проверяется)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(
        strict=False,
        reason="Известный дефект безопасности: POST /qr-code/parse-token не проверяет "
        "криптографическую подпись JWT — самодельный токен "
        "header.payload.случайная-подпись с произвольным user_id в payload успешно "
        "парсится (200) и возвращает этот user_id, как будто подпись верна. Подтверждено "
        "живым прогоном: реальный токен с добавленным мусорным байтом в конец подписи "
        "также проходит как валидный. Позволяет подделать QR-токен на любого пользователя.",
    )
    def test_parse_token_rejects_forged_signature(self, api_client):
        forged = _forge_token(user_id=999999999)
        resp = api_client.post("/qr-code/parse-token", json={"data": {"attributes": {"token": forged}}})
        assert resp.status_code in (401, 422), (
            f"Ожидалась ошибка проверки подписи, получено {resp.status_code}: {resp.text}"
        )
