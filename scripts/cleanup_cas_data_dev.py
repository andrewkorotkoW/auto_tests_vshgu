"""Одноразовая чистка CAS-данных автотестов на develop (06.10.2026), продолжение
cleanup_autotest_data_dev.py. Запуск ТОЛЬКО явно и с guard-переменной:

    QA_CLEANUP_DEV=1 .venv/bin/python -m pytest scripts/cleanup_cas_data_dev.py --env develop --log-cli-level=INFO -p no:cacheprovider

Удаляет: пользователей cas_user_*@mail.com (эмуляция КАС, 275 шт. на 06.10) — сначала обычным
DELETE /users/{id}, при неудаче DELETE /external/cas/sync/users/{id}; остатки обычных автотестов,
не попавшие под прошлый скрипт: программы «Автотест программа master_*» (через пробел) и API-test_*,
пользователей auto_test_*. Связи организация–площадка КАС (/cas/tenant-org-locations, созданы
автотестами с 18.09, id >= 167) удаляются только с QA_CLEANUP_CAS_LOCATIONS=1 — id 1 (30.06) не трогаем.
В конце печатает ONEOFF DELETED / ONEOFF REMAINING.
"""
import json, os, time, pytest
from utils.logger import logger

pytestmark = pytest.mark.skipif(os.getenv("QA_CLEANUP_DEV") != "1", reason="guard: QA_CLEANUP_DEV=1 не выставлен")

LOCATIONS_MIN_ID = 167  # первая связь, созданная автотестами (18.09.2026); id 1 — ручная, 30.06


def _get(api_client, path, tries=3):
    for i in range(tries):
        try:
            return api_client.get(path).json()
        except Exception as e:
            logger.warning(f"retry {i+1} {path}: {str(e)[:80]}"); time.sleep(3)
    return {}


def _page_ids(api_client, path, name_key, must):
    ids, page = [], 1
    while True:
        j = _get(api_client, f"{path}&per-page=25&page={page}")
        data = j.get("data") or []
        for d in data:
            a = d.get("attributes", d)
            if must in str(a.get(name_key, "")):
                ids.append(d.get("id"))
        meta = j.get("meta") or {}
        if not data or page >= (meta.get("last_page") or 1):
            break
        page += 1
    return ids


def _safe(fn, *a):
    try:
        return bool(fn(*a))
    except Exception as e:
        logger.warning(f"delete failed: {str(e)[:100]}"); return False


@pytest.mark.api
def test_cleanup_cas_data_dev(env, api_client, users_endpoint, programs_endpoint, external_cas_endpoint, omt_cas_endpoint):
    assert env.name == "develop", f"скрипт только для develop, сейчас env={env.name}"
    api_client.timeout = 120
    rep = {}

    # 1. Пользователи эмуляции КАС
    uids = _page_ids(api_client, "/users?filters[email]=cas_user_", "email", "cas_user_")
    ok = fallback = 0
    for uid in uids:
        if _safe(users_endpoint.delete, uid):
            ok += 1
        elif _safe(external_cas_endpoint.delete_user, uid):
            ok += 1; fallback += 1
    rep["cas_users"] = f"{ok}/{len(uids)} (через external: {fallback})"

    # 2. Остатки обычных автотестов, не попавшие под прошлый скрипт
    pids = set()
    for pat in ("Автотест программа", "API-test_"):
        pids.update(_page_ids(api_client, f"/programs?filters[name]={pat}", "name", pat))
    ok = sum(_safe(programs_endpoint.delete, p) for p in pids)
    rep["programs"] = f"{ok}/{len(pids)}"
    auids = _page_ids(api_client, "/users?filters[email]=auto_test", "email", "auto_test")
    ok = sum(_safe(users_endpoint.delete, u) for u in auids)
    rep["auto_test_users"] = f"{ok}/{len(auids)}"

    # 3. Связи организация–площадка КАС (только по отдельному флагу)
    if os.getenv("QA_CLEANUP_CAS_LOCATIONS") == "1":
        j = _get(api_client, "/cas/tenant-org-locations?per-page=100&page=1")
        lids = [d["id"] for d in (j.get("data") or []) if int(d.get("id", 0)) >= LOCATIONS_MIN_ID]
        ok = sum(_safe(omt_cas_endpoint.delete_tenant_org_location, l) for l in lids)
        rep["cas_locations"] = f"{ok}/{len(lids)}"
    else:
        rep["cas_locations"] = "пропущено (QA_CLEANUP_CAS_LOCATIONS не выставлен)"

    print("ONEOFF DELETED " + json.dumps(rep, ensure_ascii=False))

    rem = {}
    for label, path in [("cas_users", "/users?per-page=1&filters[email]=cas_user_"),
                        ("auto_test_users", "/users?per-page=1&filters[email]=auto_test"),
                        ("programs_space", "/programs?per-page=1&filters[name]=Автотест программа"),
                        ("programs_api_test", "/programs?per-page=1&filters[name]=API-test_")]:
        rem[label] = ((_get(api_client, path).get("meta") or {}).get("total"))
    j = _get(api_client, "/cas/tenant-org-locations?per-page=100&page=1")
    rem["cas_locations_autotest"] = len([d for d in (j.get("data") or []) if int(d.get("id", 0)) >= LOCATIONS_MIN_ID])
    print("ONEOFF REMAINING " + json.dumps(rem, ensure_ascii=False))
