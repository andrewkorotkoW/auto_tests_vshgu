# Автотесты LMS в Docker: инструкция для DevOps

Ветка: `feature/ak_auto_tests`. Актуально на 23.09.2026. Вопросы: Андрей Коротков (QA).

## 1. Что это

API- и UI-автотесты портала ВШГУ (pytest + Playwright, отчёты Allure). Один образ, один стенд на запуск:
ключ `--env develop|stage|prod`. Всего 201 тест, в обычный прогон входят 180 (без юнит-тестов генератора данных).
Полный прогон на develop идёт около 70 минут, smoke около 7 минут.

## 2. Образ

`Dockerfile` в корне. База `mcr.microsoft.com/playwright/python:v1.44.0-jammy`: внутри Python 3, Chromium и все
системные зависимости браузера. Версия базового образа привязана к версии `playwright` в `requirements.txt`,
менять только парой.

```bash
docker build -t auto_tests_vshgu:latest .
```

Размер около 2,5 ГБ. Если сборщик не ходит в `mcr.microsoft.com`, базовый образ нужно зеркалировать в
`git.devspark.ru:5005` и поменять первую строку Dockerfile. Образ на `python:3.12-slim` не подходит: без
системных библиотек Chromium UI-тесты не стартуют.

Секреты в образ не попадают: `.env`, `.cache`, `results` исключены через `.dockerignore`.

## 3. Запуск

Точка входа `scripts/run.sh`, аргументы передаются в pytest.

```bash
# локально, через compose (учётки из ./.env)
docker compose run --rm tests --env develop
docker compose run --rm tests --env develop -m smoke
docker compose run --rm tests --env stage -m "smoke and api"

# без compose
docker run --rm --env-file .env --shm-size=1g \
  -v "$PWD/results:/tests/results" -v "$PWD/.cache:/tests/.cache" \
  auto_tests_vshgu:latest --env develop -m smoke
```

Обязательно `--shm-size=1g` (или `shm_size` в compose), иначе Chromium падает на длинных прогонах.

Результаты: `results/<env>/<timestamp>/` — allure-results и `junit.xml`; если в образе есть Allure CLI,
там же собирается `results/<env>/allure-report/`. Allure-history между прогонами хранится в `results/<env>/allure-history`.

`.cache/` — кэш сессий логина, чтобы каждый прогон не логинился заново. Можно не монтировать, тогда логин на каждый запуск.

## 4. Переменные окружения

Полный список с комментариями в `.env.example`. Для одного стенда достаточно своего блока:

| Группа | Переменные | Что это |
|---|---|---|
| Адреса | `<ENV>_API_URL`, `<ENV>_UI_URL`, `<ENV>_GLOBAL_URL` | API, портал, глобальный API стенда |
| Учётки | `<ENV>_LOGIN`, `<ENV>_PASSWORD` (админ), `<ENV>_USER_LOGIN`, `<ENV>_USER_PASSWORD` (слушатель) | логин по паролю, куки не нужны |
| Интеграции | `<ENV>_CAS_TOKEN`, `<ENV>_EXTERNAL_TOKEN`, `<ENV>_LPD_JWT`, `<ENV>_BUK_TOKEN` | токены внешних систем; без `BUK_TOKEN` тесты БУК пропускаются |
| Общее | `REQUEST_TIMEOUT`, `UI_TIMEOUT`, `HEADLESS=1` | таймауты и безоконный режим (в образе уже `HEADLESS=1`) |

`<ENV>` = `DEVELOP`, `STAGE`, `PROD`. В GitLab: Settings → CI/CD → Variables, masked + protected, имена как в `.env.example`.
Переменные `*_COOKIE*` устаревшие, оставлены для совместимости, задавать не нужно.

## 5. Правила по стендам

- **develop**: полный прогон, можно по расписанию.
- **stage**: только вручную по решению владельца автотестов. Там БУК, LPD и e2e-сценарии, тестовые данные общие с командой.
- **prod**: только `-m smoke`. Полный прогон заблокирован в коде (`ensure_prod_allowed`), pytest откажется стартовать.

Тесты сами создают данные через API и удаляют их после себя; имена сущностей начинаются с «Автотест»/«автотест».

## 6. GitLab CI

`.gitlab-ci.yml`: стадия `dockerize` собирает и пушит образ `${CI_REGISTRY_IMAGE}:${CI_COMMIT_REF_SLUG}`
(оставлена как была), стадия `test` — три задания на его основе:

| Задание | Стенд | Запуск |
|---|---|---|
| `tests:develop` | develop | по расписанию (Schedules) или вручную |
| `tests:stage` | stage | только вручную |
| `tests:prod-smoke` | prod, `-m smoke` | только вручную |

Артефакты: `results/` на 14 дней, `junit.xml` подхватывается во вкладку Tests пайплайна. Раннеру нужны:
тег `devspark-builder` (как у сборки, поправить под ваш), сетевой доступ к стендам `*.devspark.ru`
и `*.ranepa.ru`, около 2 ГБ памяти на задание (Chromium).

## 7. Проверка после развёртывания

```bash
docker run --rm --env-file .env --shm-size=1g auto_tests_vshgu:latest --env develop tests/api/test_health.py
```

Два теста health должны пройти за несколько секунд. Затем smoke: `--env develop -m smoke`, ожидаемо около 7 минут.

## 8. Известные ограничения

- Тесты БУК и LPD помечены `env("stage")`: на develop пропускаются, это нормально.
- Часть тестов помечена `xfail` с причиной в отчёте: известные дефекты стендов, не ошибки инфраструктуры.
- Параллельный запуск (`-n auto`) поддерживается, но UI-тесты на одном стенде лучше гонять в 2–4 потока, не больше.
