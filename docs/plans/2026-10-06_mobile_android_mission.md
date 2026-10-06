# Миссия: мобильное тестирование Android-приложения ВШГУ (Appium) + вкладка «Мобильный» в офисе

Записано 06.10.2026. Черновик — ждём apk от разработчиков. Решения владельца (06.10): тестируем
полноценное нативное приложение (не мобильный веб); входа в админку в приложении нет; учётки те же,
что на портале; требований по устройствам нет — берём одно «универсальное» (Pixel 6, Android 13);
приоритетные сценарии — прохождение активностей, выдача сертификатов, отображение данных;
мобильные тесты живут в этом репозитории (`tests/mobile/`), запуск через test_hub.

## Окружение на машине (проверено 06.10)

- macOS 12.7.6, Intel i7-6700HQ, 16 ГБ. Аппаратное ускорение эмулятора: Hypervisor.Framework — OK
  (`emulator -accel-check`). Один эмулятор одновременно; параллельно с Playwright-прогонами — тяжело.
- Android SDK: `~/Library/Android/sdk` (emulator 31.3.10, adb 1.0.41, platforms 31–33). Переменные
  `ANDROID_SDK_ROOT`/`ANDROID_HOME` в окружении не выставлены — задавать в `.env`/фикстурах.
- AVD `Pixel_6_API_33` (1080×2400, 420 dpi, 2 ГБ RAM, образ `system-images;android-33;google_apis;x86_64`)
  создан вручную (`~/.android/avd/Pixel_6_API_33.*`), потому что `tools/bin/avdmanager` не работает на
  Java 18. **Сам образ android-33 на диске пустой (обрыв скачивания) — нужно докачать 1,5 ГБ**
  (`https://dl.google.com/android/repository/sys-img/google_apis/x86_64-33_r12.zip` или через SDK Manager
  в Android Studio). Рабочие сейчас только старые AVD на API 26 (Android 8).
- Запуск эмулятора без окна: `emulator -avd Pixel_6_API_33 -no-window -no-audio -no-boot-anim
  -gpu swiftshader_indirect`; готовность — `adb shell getprop sys.boot_completed` == 1.
- Node: системный v12 — не годится для Appium; ставится `node@18` через Homebrew
  (`/usr/local/opt/node@18/bin`). Appium 2 + драйвер `uiautomator2` — глобально через npm этого Node.
  Картинка экрана: `scrcpy` (brew) для живого окна, `adb exec-out screencap -p` для скриншотов в отчёт.
- Python-клиент: `Appium-Python-Client` (в `.venv`), Allure уже есть.

## Исходные данные (ждём)

- apk приложения: источник, окружение, на которое оно ходит (develop), `applicationId`, `minSdk`.
  Проверить: `aapt dump badging app.apk | head`, установка `adb install -r app.apk`, запуск.
- Авторизация в приложении: тот же логин/пароль, что на портале develop (`.env`, `get_credentials`).
  Нет ли СМС/внешнего провайдера — если есть, нужен обход для тестового стенда.
- Исходники приложения — «вроде есть, данных пока нет». Без них селекторы по `resource-id` не
  гарантированы: сначала снять дерево через `uiautomator dump`/Appium Inspector и зафиксировать в
  `docs/mobile/ui_tree.md`, затем писать page objects.
- Ручных кейсов по мобилке в Test IT нет (не указаны) — кейсы пишем сами по `docs/test_cases/TEMPLATE.md`
  в `docs/test_cases/mobile/*.md` (`TC-MOBILE-<ОБЛАСТЬ>-NNN`).

## Часть 1 — каркас мобильных тестов (auto_tests_vshgu)

1. `config/mobile.py` + `.env.example`: `ANDROID_SDK_ROOT`, `MOBILE_AVD=Pixel_6_API_33`, `MOBILE_APK`,
   `APPIUM_URL=http://127.0.0.1:4723`, `MOBILE_APP_ID`. Значения `.env` в код/логи/md не писать.
2. `tests/mobile/conftest.py`: фикстуры session-scope `emulator` (поднять AVD, если не поднят; дождаться
   `sys.boot_completed`; не гасить чужой), `appium_server` (поднять `appium` subprocess, если порт 4723
   свободен), `app` (установка apk, `noReset`/`fullReset` по флагу), function-scope `driver`
   (UiAutomator2, `appium:appPackage/appActivity`), скриншот + `page_source` в Allure при падении.
   Маркер `@pytest.mark.mobile`, зарегистрировать в `pytest.ini`; в `product_map.yml` — область `mobile`.
3. Page objects `ui/mobile/pages/*.py` (login, список программ, карточка активности, сертификаты, профиль)
   по снятому дереву; локаторы — `resource-id` → `accessibility id` → `xpath` по тексту, в таком порядке.
4. Первые сценарии (данные готовить через существующие API-фикстуры `created_user`/`created_program`/
   `assignments_endpoint`, как в UI-тестах): вход; список назначенных программ соответствует
   `/my-programs`; открыть активность и пройти (тест/опрос — простейший); сертификат появляется после
   завершения программы; данные профиля/прогресса совпадают с API. Каждый — `allure.title` на русском,
   `TC-MOBILE-*` в md.
5. `README` §19 «Мобильные тесты»: установка (brew node@18, appium, драйвер, образ), запуск
   `pytest tests/mobile --env develop -m mobile`, типовые проблемы (эмулятор не поднялся, порт занят).
6. test_hub: пресет/раздел «Mobile» в пресетах запуска (как API/UI/Smoke), прогон `-m mobile`
   последовательно (один эмулятор → `-n 1`).

## Часть 2 — вкладка «Мобильный» в cyber_office (второстепенно)

- Новая панель в `ui/index.html` + `ui/app.js`: статус эмулятора (поднят/нет, AVD, Android), кнопки
  «Поднять»/«Погасить», живой экран — поток скриншотов `adb exec-out screencap -p` раз в 1–2 с
  (MJPEG/polling), рамка телефона 1080×2400 с масштабом. Кнопка «Прогнать mobile» → `testlab.run`
  с `-m mobile`, ссылка на Allure.
- REST: `GET /api/mobile/status`, `POST /api/mobile/emulator/start|stop`, `GET /api/mobile/screen`
  (png), всё через `adb`/`emulator` из `ANDROID_SDK_ROOT`. Без Appium в офисе — только adb.
- Ограничение: один эмулятор, не поднимать второй экземпляр, если уже есть `emulator-5554`.

## Правила

- Только develop. Учётки/токены только из `.env`. apk в git не коммитить (`.gitignore`: `*.apk`,
  `build/mobile/`), путь — через `MOBILE_APK`.
- Сначала часть 1 (п. 1–3 и один сквозной сценарий «вход → список программ»), показать владельцу,
  потом остальные сценарии и test_hub; часть 2 — отдельной миссией для cyber_office.
- Ничего не удалять на стенде; данные помечать `Автотест_`/`auto_test_` как везде.
