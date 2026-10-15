"""Разведка: структура /profile/{id} — есть ли вкладка «Сертификаты» (владелец подтвердил,
что она там есть), независимо от того, пройдена ли программа — просто посмотреть структуру."""
import os
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage

D = "/private/tmp/claude-502/-Users-andreykorotkow-PycharmProjects-cyber-office/400bc1a1-fbe6-461e-abb3-20a741890d2d/scratchpad/cert_listener_recon"


@pytest.mark.ui
def test_profile_cert_tab_structure(page, env, prepared_user):
    os.makedirs(D, exist_ok=True)
    user = prepared_user()
    LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url, handle_onboarding=False)
    page.goto(f"{env.ui_base_url}/profile/{user['id']}", wait_until="load")
    page.wait_for_timeout(2500)
    UserSidebarPage(page).dismiss_popups()
    page.wait_for_timeout(1000)
    page.screenshot(path=f"{D}/10_profile_page.png", full_page=True)
    print("PROFILE_URL", page.url)
    body = page.locator("body").inner_text()
    print("PROFILE_BODY", body[:1000].replace("\n", " | "))
    print("HAS_CERT_WORD", "сертификат" in body.lower())

    cert_tab = page.locator("text=Мои сертификаты").first
    cert_tab.click(force=True)
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{D}/11_cert_tab_empty.png", full_page=True)
    print("CERT_TAB_URL", page.url)
    print("CERT_TAB_BODY", page.locator("body").inner_text()[:800].replace("\n", " | "))

    # Сетевой запрос, который дёргает эта вкладка — чтобы знать реальный API-эндпоинт
    # для будущего автотеста (проверка через API быстрее, чем через DOM).
    reqs = []
    page.on("request", lambda r: reqs.append(r.url) if "certificat" in r.url.lower() else None)
    page.reload()
    page.wait_for_timeout(2000)
    page.locator("text=Мои сертификаты").first.click(force=True)
    page.wait_for_timeout(2000)
    print("CERT_RELATED_REQUESTS", reqs)
