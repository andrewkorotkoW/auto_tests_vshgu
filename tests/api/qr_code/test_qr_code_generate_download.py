"""GET /qr-code/generate, GET /qr-code/download (docs/qr_code_ratings_recon.md,
раздел «QR-код») — персональный QR текущего пользователя в двух форматах."""
import allure
import pytest


@allure.feature("QR-код пользователя")
@allure.story("Генерация и скачивание персонального QR")
@pytest.mark.api
class TestQrCodeGenerateDownload:

    @allure.title("GET /qr-code/generate → PNG персонального QR")
    def test_generate_returns_png(self, qr_code_endpoint):
        resp = qr_code_endpoint.generate_qr_code()
        assert resp.headers.get("Content-Type") == "image/png"
        assert "my-qr-code.png" in resp.headers.get("Content-Disposition", "")
        assert resp.content[:8] == b"\x89PNG\r\n\x1a\n", "Тело ответа — не валидный PNG"

    @allure.title("GET /qr-code/download → PDF персонального QR")
    def test_download_returns_pdf(self, qr_code_endpoint):
        resp = qr_code_endpoint.download_qr_code()
        assert resp.headers.get("Content-Type") == "application/pdf"
        assert "my-qr-code.pdf" in resp.headers.get("Content-Disposition", "")
        assert resp.content[:5] == b"%PDF-", "Тело ответа — не валидный PDF"

    @allure.title("Два разных пользователя получают два разных QR (разные токены)")
    def test_generate_is_personal_per_user(self, qr_code_endpoint, env, created_user, decode_qr_png):
        from api.client import ApiClient
        from api.endpoints.qr_code import QrCodeEndpoint
        from config.environments import login

        admin_token = decode_qr_png(qr_code_endpoint.generate_qr_code().content)

        user = created_user()
        user_session = login(env, user["email"], user["password"])
        user_client = ApiClient(session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name)
        user_qr = QrCodeEndpoint(user_client)
        user_token = decode_qr_png(user_qr.generate_qr_code().content)

        assert admin_token != user_token

    @allure.title("Анонимный запрос generate/download → 401")
    @pytest.mark.parametrize("path", ["/qr-code/generate", "/qr-code/download"])
    def test_anon_gets_401(self, anon_api_client, path):
        resp = anon_api_client.get(path)
        assert resp.status_code == 401
        assert resp.json().get("message") == "Unauthenticated."
