"""Генерация тестовых данных CAS на выбранном окружении.

Создаёт связку: программа CAS -> поток -> синхронизация -> пользователь CAS с паролем
-> зачисление в поток. Это env-aware версия generate_scorm_and_certificate.py:
логин по <ENV>_LOGIN/<ENV>_PASSWORD (или кука), токен из <ENV>_CAS_TOKEN.

    .venv/bin/python test_data_generation/generate_cas_data.py --env stage
    .venv/bin/python test_data_generation/generate_cas_data.py --env develop --users 3
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.environments import ENVIRONMENTS, get_session  # noqa: E402
from api.helpers.constants import CAS_LOCATIONS, CAS_ORGANIZATIONS  # noqa: E402

DEFAULT_PASSWORD = "SecurePass123"


def _msg(resp) -> str:
    """Читаемое сообщение об ошибке (сервер экранирует кириллицу в \\uXXXX)."""
    try:
        j = resp.json()
    except ValueError:
        return resp.text[:300]
    parts = [j.get("message")] if j.get("message") else []
    errors = j.get("errors")
    if isinstance(errors, list):
        parts += [str(e) for e in errors]
    elif isinstance(errors, dict):
        parts += [f"{k}: {' '.join(map(str, v))}" for k, v in errors.items()]
    return "; ".join(parts)[:300] or resp.text[:300]


def _id(resp, *keys):
    """ID сущности из ответа: {"data": {"id"|"program_id"|"stream_id"|"user_id": ...}}."""
    data = resp.json().get("data", resp.json())
    for key in ("id",) + keys:
        if data.get(key) is not None:
            return data[key]
    raise RuntimeError(f"в ответе нет id: {data}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Генерация данных CAS")
    parser.add_argument("--env", default="develop", choices=sorted(ENVIRONMENTS))
    parser.add_argument("--users", type=int, default=1, help="сколько пользователей CAS создать и зачислить")
    parser.add_argument("--org", default=CAS_ORGANIZATIONS[1][0], help="organization_uuid CAS")
    parser.add_argument("--location", default=CAS_LOCATIONS[4][0], help="location_uuid CAS")
    parser.add_argument("--tenant", type=int, default=2, help="tenant_organization_id для связки org+location")
    args = parser.parse_args()

    env = ENVIRONMENTS[args.env]
    if not env.cas_auth_token:
        print(f"Нет токена CAS для {env.name}: задайте {env.name.upper()}_CAS_TOKEN в .env")
        return 2

    session = get_session(env)
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    })
    cas_headers = {"Authorization": env.cas_auth_token}
    base = env.api_base_url
    ts = int(time.time())

    def post(path, json=None, cas=True):
        return session.post(f"{base}{path}", json=json, headers=cas_headers if cas else None)

    print(f"Окружение: {env.name} ({base})")

    print("0. Связка организация+локация CAS с тенантом (OMT)...")
    r = post("/cas/tenant-org-locations", {
        "cas_location_uuid": args.location,
        "cas_organization_uuid": args.org,
        "tenant_organization_id": args.tenant,
    }, cas=False)
    if r.status_code in (200, 201):
        print(f"   создана: {r.json().get('data', r.json())}")
    elif r.status_code == 422 and "уже существует" in r.json().get("message", ""):
        print("   уже существует")
    else:
        print(f"   ошибка: {r.status_code} {_msg(r)}")
        return 1

    print("1. Программа CAS...")
    r = post("/external/cas/programs", {
        "name": f"CAS_Prog_{ts}",
        "description": f"Программа для CAS {ts}",
        "organization_uuid": args.org,
        "location_uuid": args.location,
    })
    if r.status_code not in (200, 201):
        print(f"   ошибка: {r.status_code} {_msg(r)}")
        return 1
    prog_id = _id(r, "program_id")
    print(f"   ID={prog_id}")

    print("2. Поток...")
    r = post(f"/external/cas/programs/{prog_id}/streams", {
        "name": f"CAS_Stream_{ts}",
        "date_from": time.strftime("%Y-%m-%d"),
        "date_to": time.strftime("%Y-%m-%d", time.localtime(ts + 30 * 86400)),
        "managers_email": ["admin1@org2.ru", "admin2@org2.ru"],
    })
    if r.status_code not in (200, 201):
        print(f"   ошибка: {r.status_code} {_msg(r)}")
        return 1
    stream_id = _id(r, "stream_id")
    print(f"   ID={stream_id}")

    print("3. Синхронизация программы и потока...")
    for path in (f"/external/cas/sync/programs/{prog_id}",
                 f"/external/cas/sync/programs/{prog_id}/streams/{stream_id}"):
        r = post(path)
        if r.ok:
            status = "ok"
        elif r.status_code == 400 and "не синхронизирован" in _msg(r):
            status = "уже синхронизирован (создание через external API синхронизирует сразу)"
        else:
            status = f"{r.status_code} {_msg(r)}"
        print(f"   {path.split('/sync/')[1]}: {status}")

    created = []
    for i in range(args.users):
        suffix = f"{ts}_{i}"
        email = f"cas_user_{env.name}_{suffix}@mail.com"
        print(f"4. Пользователь CAS {i + 1}/{args.users}: {email}")
        r = post("/external/cas/users", {
            "email": email, "name": "CAS", "surname": "Testov", "patronymic": "Testovich",
            "date_of_birth": "1990-01-01", "gender": 1, "region": "Москва",
            "organisation": "Devspark", "position": "AQA",
            "cas_uuid": f"cas-{suffix}-{os.urandom(2).hex()}",
            "organization_uuid": args.org, "location_uuid": args.location,
        })
        if r.status_code not in (200, 201):
            print(f"   ошибка: {r.status_code} {_msg(r)}")
            return 1
        user_id = _id(r, "user_id")

        r = session.get(f"{base}/users/{user_id}")
        if r.status_code != 200:
            print(f"   не удалось прочитать пользователя: {r.status_code}")
            return 1
        attrs = r.json()["data"]["attributes"]
        # GET отдаёт теги объектами, PUT ждёт список id
        attrs["tags"] = [t["id"] if isinstance(t, dict) else t for t in attrs.get("tags") or []]
        attrs["password"] = DEFAULT_PASSWORD
        attrs["system_password"] = DEFAULT_PASSWORD
        r = session.put(f"{base}/users/{user_id}", json={"data": {"attributes": attrs}})
        print(f"   пароль: {'ok' if r.ok else str(r.status_code) + ' ' + _msg(r)}")

        r = post("/external/cas/assignments", {
            "user_ids": [{"user_id": user_id, "cas_application_uid": f"auto-{suffix}-{user_id}"}],
            "stream_id": stream_id, "status": "enlisted",
            "enlisted_text": "Зачислен по автотесту", "enlisted_link": "https://autotest.com",
        })
        print(f"   зачисление: {'ok' if r.ok else str(r.status_code) + ' ' + _msg(r)}")
        created.append((user_id, email))

    print("\nГотово.")
    print(f"  Программа: {prog_id}, поток: {stream_id}")
    for user_id, email in created:
        print(f"  Пользователь: {email} / {DEFAULT_PASSWORD} (id={user_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
