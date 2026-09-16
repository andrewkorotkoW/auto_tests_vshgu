import sys
import os
import time
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import settings

BASE_URL = "https://portal-develop.d2.devspark.ru/api/v1"
COOKIE_NAME = "develop"
COOKIE_VALUE = settings.DEVELOP_COOKIE
CAS_TOKEN = settings.CAS_AUTH_TOKEN

def headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": f"{COOKIE_NAME}={COOKIE_VALUE}",
        "Authorization": CAS_TOKEN
    }

def extract_id(response_json):
    """Извлекает id из разных возможных структур ответа"""
    if "data" in response_json:
        data = response_json["data"]
        if isinstance(data, dict):
            return data.get("id")
    if "id" in response_json:
        return response_json["id"]
    return None

def main():
    ts = int(time.time())
    prog_name = f"CAS_Prog_{ts}"
    stream_name = f"CAS_Stream_{ts}"

    print("=== ЗАПУЩЕНА ИСПРАВЛЕННАЯ ВЕРСИЯ СКРИПТА ===\n")

    # 1. Создание программы
    print("1. Создаю программу CAS...")
    prog_payload = {
        "name": prog_name,
        "description": f"Программа для CAS {prog_name}",
        "organization_uuid": "1a41b037-c5fc-11e5-80e4-005056a00b6e",
        "location_uuid": "3d4b8136-5f9d-11ea-8144-005056a03e4f"
    }
    r = requests.post(f"{BASE_URL}/external/cas/programs", json=prog_payload, headers=headers())
    if r.status_code in (200, 201):
        resp_json = r.json()
        print("   [DEBUG] Полный ответ сервера:", resp_json)
        prog_id = extract_id(resp_json)
        if not prog_id:
            print("   ОШИБКА: не удалось извлечь id программы из ответа!")
            return
        print(f"   Программа создана: ID={prog_id}")
    else:
        print(f"   Ошибка создания программы: {r.status_code} {r.text}")
        return

    # 2. Создание потока
    print("2. Создаю поток CAS...")
    stream_payload = {
        "name": stream_name,
        "date_from": time.strftime("%Y-%m-%d"),
        "date_to": time.strftime("%Y-%m-%d", time.localtime(ts + 30 * 86400)),
        "managers_email": ["admin1@org2.ru", "admin2@org2.ru"]
    }
    r = requests.post(f"{BASE_URL}/external/cas/programs/{prog_id}/streams", json=stream_payload, headers=headers())
    if r.status_code in (200, 201):
        stream_data = r.json().get("data", r.json())
        stream_id = stream_data.get("id")
        print(f"   Поток создан: ID={stream_id}")
    else:
        print(f"   Ошибка создания потока: {r.status_code} {r.text}")
        return

    # 3. Синхронизация программы
    print("3. Синхронизирую программу...")
    r = requests.post(f"{BASE_URL}/external/cas/sync/programs/{prog_id}", headers=headers())
    if r.status_code in (200, 201):
        print("   Программа синхронизирована")
    else:
        print(f"   Ошибка синхронизации программы: {r.status_code} {r.text}")

    # 4. Синхронизация потока
    print("4. Синхронизирую поток...")
    r = requests.post(f"{BASE_URL}/external/cas/sync/programs/{prog_id}/streams/{stream_id}", headers=headers())
    if r.status_code in (200, 201):
        print("   Поток синхронизирован")
    else:
        print(f"   Ошибка синхронизации потока: {r.status_code} {r.text}")

    # 5. Создание пользователя
    print("5. Создаю пользователя CAS...")
    user_email = f"cas_user_dev_{ts}@mail.com"
    user_payload = {
        "email": user_email,
        "name": "CAS",
        "surname": "Testov",
        "patronymic": "Testovich",
        "date_of_birth": "1990-01-01",
        "gender": 1,
        "region": "Москва",
        "organisation": "Devspark",
        "position": "AQA",
        "cas_uuid": f"cas-{ts}-{os.urandom(2).hex()}",
        "organization_uuid": "1a41b037-c5fc-11e5-80e4-005056a00b6e",
        "location_uuid": "3d4b8136-5f9d-11ea-8144-005056a03e4f"
    }
    r = requests.post(f"{BASE_URL}/external/cas/users", json=user_payload, headers=headers())
    if r.status_code in (200, 201):
        user_data = r.json().get("data", r.json())
        user_id = user_data.get("id")
        print(f"   Пользователь CAS создан: user_id={user_id}, email={user_email}")
    else:
        print(f"   Ошибка создания пользователя: {r.status_code} {r.text}")
        return

    # 6. Установка пароля
    print("6. Устанавливаю пароль...")
    r = requests.get(f"{BASE_URL}/users/{user_id}", headers={
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": f"{COOKIE_NAME}={COOKIE_VALUE}"
    })
    if r.status_code != 200:
        print(f"   Ошибка получения пользователя: {r.status_code}")
        return
    attrs = r.json()["data"]["attributes"]
    attrs["password"] = "SecurePass123"
    attrs["system_password"] = "SecurePass123"
    r = requests.put(f"{BASE_URL}/users/{user_id}", json={"data": {"attributes": attrs}}, headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": f"{COOKIE_NAME}={COOKIE_VALUE}"
    })
    if r.status_code == 200:
        print(f"   Пароль установлен: {user_email} / SecurePass123")
    else:
        print(f"   Ошибка установки пароля: {r.status_code} {r.text}")

    # 7. Назначение в поток
    print("7. Назначаю пользователя в поток...")
    assign_payload = {
        "user_ids": [{"user_id": user_id, "cas_application_uid": f"auto-{ts}-{user_id}"}],
        "stream_id": stream_id,
        "status": "enlisted",
        "enlisted_text": "Зачислен по автотесту",
        "enlisted_link": "https://autotest.com"
    }
    r = requests.post(f"{BASE_URL}/external/cas/assignments", json=assign_payload, headers=headers())
    if r.status_code in (200, 201):
        print("   Пользователь назначен в поток")
    else:
        print(f"   Ошибка назначения: {r.status_code} {r.text}")

    print("\nГотово! Данные для входа:")
    print(f"  Email: {user_email}")
    print(f"  Пароль: SecurePass123")
    print(f"  Программа: {prog_id}, Поток: {stream_id}")

if __name__ == "__main__":
    main()