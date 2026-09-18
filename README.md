# auto_tests_vshgu_cloude

Автотесты портала (API + UI) для develop/stage/prod окружений.

## 1. О проекте

Стек: `pytest` 8, `requests` (API-слой), `Playwright` (UI-слой), `allure-pytest` (отчёты),
`pytest-xdist` (параллельный запуск), `pytest-rerunfailures` (авторетрай флаки UI-тестов).
Полный список версий — в `requirements.txt`.

Слои:

- `api/client.py` — тонкий HTTP-клиент поверх `requests.Session` (базовый URL, кука/заголовки,
  логирование запросов).
- `api/endpoints/*` — по одному модулю на сущность портала (`users.py`, `programs.py`,
  `lpd.py`, `certificates.py` и т.д.) — методы, которые собирают запрос и возвращают
  `requests.Response`, без ассертов внутри.
- `api/helpers/expectations.py` — `expect_status(resp, expected_status)`: единая проверка
  статус-кода с телом ответа в сообщении об ошибке, используется в тестах вместо голых `assert`.
- `api/helpers/data_generator.py` — генераторы тестовых данных (уникальные для параллельного
  запуска под `xdist`).
- `ui/pages/*` — Page Object для UI-тестов на Playwright (`login_page.py`, `lpd_page.py`,
  `admin_page.py` и т.д.).
- `config/settings.py` — тонкие алиасы на develop/stage из `config/environments.py`, оставлены
  ради обратной совместимости с кодом, который уже импортирует `settings.BASE_URL` и т.п.
- `config/environments.py` — реестр окружений, логин по логину/паролю, кэш сессий и
  Playwright `storage_state` (см. раздел 2 и 6).
- `utils/logger.py`, `utils/retry.py` — логирование и `retry_until_success` для ожиданий в UI
  вместо `sleep`.

## 2. Окружения

Окружения (`develop`, `stage`, `prod`) описаны в `config/environments.py` в виде реестра
`ENVIRONMENTS = {"develop": Environment(...), "stage": Environment(...), "prod": Environment(...)}`.
Каждое — это `api_base_url`, `ui_base_url`, `cookie_name`, `cookie`, `global_base_url`,
`cas_auth_token`, `external_system_client_token`, `lpd_jwt_token`.

Значения читаются из `.env` через переменные с префиксом `<ENV>_` (`DEVELOP_*`, `STAGE_*`,
`PROD_*`), например `DEVELOP_API_URL`, `STAGE_COOKIE`, `PROD_LPD_JWT`. Если переменная с новым
именем не задана, для develop/stage есть fallback на старые плоские имена (`BASE_URL`,
`STAGE_BASE_URL`, `DEVELOP_COOKIE` и т.п.) — они уже могли быть в существующем `.env`.

`prod` по умолчанию выключен: `pytest --env=prod` без `-m smoke` падает с понятной ошибкой
(`ensure_prod_allowed` в `config/environments.py`, `PROD_ALLOWED_MARKEXPR = "smoke"`) — это
защита от случайного полного (в т.ч. мутирующего) прогона на проде.

Как начать:

```bash
cp .env.example .env
```

и заполнить нужные переменные (как минимум для одного окружения — `DEVELOP_*` или `STAGE_*`).
`.env` **не должен** попадать в git — он в `.gitignore`; в README и коммиты не должны идти
реальные значения кук/токенов/паролей, только имена переменных из `.env.example`.

## 3. Запуск

Выбор окружения — флагом `--env` (добавлен в `pytest_addoption` в корневом `conftest.py`):

```bash
pytest --env=develop
pytest --env=stage
pytest --env=prod -m smoke   # prod без -m smoke будет отклонён
```

По умолчанию (без `--env`) используется `develop`, либо значение переменной `ENV` из `.env`.

Маркеры зарегистрированы в `pytest.ini`:

- `api` / `ui` — тип теста;
- `smoke` / `regression` — важность/объём прогона;
- `develop` / `stage` — исторические маркеры окружения;
- `env(name)` — тест специфичен для окружения (`develop` или `stage`): если запуск идёт с
  другим `--env`, такой тест автоматически skip-ается (`pytest_collection_modifyitems` в
  `conftest.py`). Пример использования — `@pytest.mark.env("stage")` в `tests/e2e/`.

Тесты с маркером `ui` автоматически получают один автоповтор (`pytest-rerunfailures`) —
это сглаживает флаки реального браузера, а не ошибки в самом тесте.

Примеры команд:

```bash
pytest --env=develop -m "smoke and api"
pytest --env=stage -m "smoke and ui"
pytest --env=develop -n auto           # параллельный прогон через pytest-xdist
pytest --env=stage -m regression -n auto
```

Обёртки `scripts/run.sh` (bash) и `scripts/run.bat` (Windows) — тот же `pytest --env ...`,
но дополнительно кладут allure-результаты в `results/<env>/<timestamp>/`, хранят allure-history
отдельно на каждое окружение в `results/<env>/allure-history/` и (если найден allure CLI)
сразу генерируют отчёт в `results/<env>/allure-report/`. Использование — по комментарию в
начале каждого скрипта:

```bash
scripts/run.sh --env develop
scripts/run.sh --env stage -m "smoke and ui"
scripts/run.sh --env prod -m smoke
```

```bat
scripts\run.bat --env develop
```

## 4. Структура проекта

```
tests/
  api/     — API-тесты по сущностям портала (cas/, programs/, users/, certificates/, ...)
  ui/      — UI-тесты (Playwright) по тем же сущностям
  e2e/     — сквозные сценарии на LPD/назначения (api/ и ui/ подпапки), помеченные
             @pytest.mark.env("stage") — привязка не по названию папки, а по маркеру
api/
  client.py        — HTTP-клиент
  endpoints/        — по модулю на сущность
  helpers/          — expectations.py (expect_status), data_generator.py, constants.py
ui/
  pages/            — Page Object'ы Playwright
config/
  settings.py       — алиасы поверх ENVIRONMENTS["develop"/"stage"]
  environments.py   — реестр окружений, логин, кэш сессий/storage_state
utils/
  logger.py         — логирование
  retry.py          — retry_until_success (ожидания в UI без sleep)
```

`tests/e2e` — это переименованный бывший `tests/stage`: набор тот же, но привязка к
окружению теперь идёт через маркер `@pytest.mark.env("stage")`, а не через физическое
расположение папки, поэтому теоретически туда же могут добавляться сценарии и под другие
окружения.

## 5. Как добавить новое окружение

1. В `config/environments.py` добавить новую запись в `ENVIRONMENTS` через `_build_environment(...)`
   (по образцу `develop`/`stage`/`prod`) — имя, `cookie_name`, URL по умолчанию и (при
   необходимости) словарь `legacy` для обратной совместимости со старыми именами переменных.
2. Добавить в `.env` (и в `.env.example` — с пустыми значениями, для документации) переменные
   с новым префиксом `<ENV>_`: `<ENV>_API_URL`, `<ENV>_UI_URL`, `<ENV>_GLOBAL_URL`,
   `<ENV>_COOKIE`, `<ENV>_COOKIE_NAME`, `<ENV>_CAS_TOKEN`, `<ENV>_EXTERNAL_TOKEN`,
   `<ENV>_LPD_JWT`, `<ENV>_LOGIN`/`<ENV>_PASSWORD` (и при необходимости
   `<ENV>_ADMIN_LOGIN/PASSWORD`, `<ENV>_USER_LOGIN/PASSWORD`).
3. Если новое окружение должно быть ограничено как `prod` (например, тоже боевое) — расширить
   проверку в `ensure_prod_allowed` или завести для него свою логику по аналогии.
4. `--env` в `pytest.ini`/`conftest.py` ничего менять не нужно — `pytest_addoption` берёт список
   допустимых значений прямо из `ENVIRONMENTS.keys()`.

## 6. Как обновить куки

Ручные куки — запасной вариант на случай, если логин по логину/паролю не сработал. Хранятся
в `.env` как `DEVELOP_COOKIE` / `STAGE_COOKIE` / `PROD_COOKIE` (сама кука, без имени) плюс
`<ENV>_COOKIE_NAME`, если имя куки на портале нестандартное.

Обновление вручную:

1. Залогиниться в браузере на нужном окружении, скопировать значение сессионной куки.
2. Записать его в `.env` в переменную `<ENV>_COOKIE` (не в `.env.example` и не в README).
3. Удалить устаревший кэш в `.cache/` для этого окружения (`session_<env>_<role>.json`,
   `storage_state_<env>_<role>.json`) — иначе тесты продолжат использовать закэшированную
   (возможно, тоже протухшую) сессию.

Основной путь — не куки, а логин/пароль (`<ENV>_LOGIN`/`<ENV>_PASSWORD` в `.env`):
`get_session()` в `config/environments.py` сперва проверяет валидный кэш в `.cache/` (запрос
`GET /auth/me`), при его отсутствии/невалидности логинится через `login()` (CSRF-токен со
страницы `/auth/main` + `POST /auth/login`) и кэширует результат; ручная кука используется
только если логин не удался — в лог тогда пишется `warning`. Для UI-тестов та же сессия
конвертируется в Playwright `storage_state` (`build_storage_state`/`get_storage_state_path`)
и тоже кэшируется в `.cache/` — так UI-тесты не логинятся через форму на каждый прогон.

`.cache/` в `.gitignore` — при протухшей сессии/куке можно просто удалить нужные файлы в
`.cache/`, и следующий прогон пересоздаст их (или заново залогинившись, или через ручную
куку). Если и логин, и кука не срабатывают одновременно — это, скорее всего, проблема данных
в `.env` (устаревший пароль/кука), а не кода `login()`/`get_session()`: сервер в ответ на
неверные учётные данные возвращает осмысленную ошибку с формой логина, и `login()` эту
ситуацию распознаёт (`LoginError`) и корректно откатывается на ручную куку.

## 7. Запуск в Docker

Образ собирается на базе `mcr.microsoft.com/playwright/python` (Chromium и системные
зависимости уже внутри), версия образа привязана к `playwright` из `requirements.txt`.
`.env` в образ не попадает: он пробрасывается при запуске через `env_file`.

```bash
docker compose build
docker compose run --rm tests --env develop
docker compose run --rm tests --env stage -m "smoke and api"
docker compose run --rm tests --env prod -m smoke
```

Внутри контейнера запускается тот же `scripts/run.sh`, UI-тесты идут в headless-режиме
(`HEADLESS=1`), результаты остаются на хосте в `results/<env>/<timestamp>/`, кэш сессий —
в `.cache/`. Локально без Docker `HEADLESS` не задан, и браузер открывается с окном, как раньше.
