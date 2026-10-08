# Автотесты LMS в Docker: инструкция для DevOps

Ветка: `main`. Актуально на 08.10.2026. Вопросы: Андрей Коротков (QA).

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

Команда прогона задаётся явно: `scripts/run.sh --env <стенд> [аргументы pytest]`. У образа нет ENTRYPOINT, чтобы GitLab CI мог запускать в контейнере shell; по умолчанию (`CMD`) выполняется прогон на develop.

**В CI volume не нужны и не используются.** GitLab CI запускает джобу через `image: $IMAGE` — это
собственный docker-executor раннера, он сам монтирует рабочую директорию джобы и сам же забирает
`results/` как `artifacts:` после завершения скрипта. Внутри джобы это просто:

```bash
bash scripts/run.sh --env "${STAND}" ${PYTEST_ARGS}
```

`-v`/volume нужны только локально разработчику, чтобы руками вытащить `results/`/`.cache/` на хост —
это удобство для машины QA, к контуру CI отношения не имеет:

```bash
# локально, через compose (учётки из ./.env)
docker compose run --rm tests scripts/run.sh --env develop
docker compose run --rm tests scripts/run.sh --env develop -m smoke
docker compose run --rm tests scripts/run.sh --env stage -m "smoke and api"

# без compose, тоже только для локальной машины
docker run --rm --env-file .env --shm-size=1g \
  -v "$PWD/results:/tests/results" -v "$PWD/.cache:/tests/.cache" \
  auto_tests_vshgu:latest scripts/run.sh --env develop -m smoke
```

Обязательно `--shm-size=1g` (или `shm_size` в compose), иначе Chromium падает на длинных прогонах.

Результаты: `results/<env>/<timestamp>/` — allure-results и `junit.xml`; если в образе есть Allure CLI,
там же собирается `results/<env>/allure-report/`. Allure-history между прогонами хранится в `results/<env>/allure-history`.

`.cache/` — кэш сессий логина, чтобы каждый прогон не логинился заново. В CI не монтируется (эфемерен,
живёт только в рамках одной джобы) — это осознанно, каждая джоба логинится заново.

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

### 4.1 Универсальный набор для iac-конфигов (другие ЦОДы, файл переменных пайплайна)

Для прогона по шаблону `vshgu/lms/ci-cd` на произвольном ЦОДе нужен один файл переменных (тип `File`,
`KEY=VALUE` без кавычек — как `CI_TEST_ENV_FILE` в `.run_tests` нашего `.gitlab-ci.yml`) с префиксом
`STAND_` вместо `DEVELOP_`/`STAGE_`:

**Обязательные:**

| Переменная | Что это |
|---|---|
| `STAND_URL` | адрес портала стенда, например `https://portal-develop.d2.devspark.ru` |
| `STAND_COOKIE_NAME` | имя сессионной куки стенда |
| `STAND_ADMIN_LOGIN` / `STAND_ADMIN_PASSWORD` | учётка администратора |
| `STAND_USER_LOGIN` / `STAND_USER_PASSWORD` | учётка слушателя |

**Необязательные** (если не заданы — выводятся из `STAND_URL` автоматически: `portal-` → `global-`/`helpdesk-`):

| Переменная | Что это |
|---|---|
| `STAND_API_URL` | адрес API, если отличается от выведенного |
| `STAND_GLOBAL_URL` | глобальный API (например для cross-tenant статистики) |
| `HELPDESK_URL` | адрес хелпдеска, если отличается от выведенного |

**Необязательные, только под конкретные интеграционные тесты** (пусто = тест пропускается `skip`, не `fail`):
`STAND_CAS_TOKEN`, `STAND_EXTERNAL_TOKEN`, `STAND_LPD_JWT`, `STAND_BUK_TOKEN`.

На момент записи (08.10.2026) код автотестов ещё не умеет читать `STAND_*`/режим `--env stand` —
сейчас понимает только фиксированные `develop`/`stage`/`prod`/`k8s`. Это в работе на нашей стороне
(расширение `config/environments.py`), название переменных уже финальное — можно закладывать в iac
без риска, что имена потом поменяются.

## 5. Правила по стендам

- **develop**: полный прогон, можно по расписанию.
- **stage**: только вручную по решению владельца автотестов. Там БУК, LPD и e2e-сценарии, тестовые данные общие с командой.
- **prod**: только `-m smoke`. Полный прогон заблокирован в коде (`ensure_prod_allowed`), pytest откажется стартовать.

Тесты сами создают данные через API и удаляют их после себя; имена сущностей начинаются с «Автотест»/«автотест».

## 6. GitLab CI

`.gitlab-ci.yml`: стадия `dockerize` (`docker:build`, тег `devspark-builder`, ручная) собирает и пушит
образ `${CI_REGISTRY_IMAGE}:${CI_COMMIT_REF_SLUG}`, стадия `test` — четыре задания на его основе
(`.run_tests`, тег `devspark-docker`, `image: $IMAGE`):

| Задание | Стенд | Запуск |
|---|---|---|
| `tests:develop:api` | develop, `tests/api` | по расписанию (Schedules) или вручную, таймаут 2 ч |
| `tests:develop:ui` | develop, `tests/ui tests/e2e` | по расписанию (Schedules) или вручную, таймаут 2 ч |
| `tests:stage` | stage, полный | только вручную, таймаут 2 ч |
| `tests:prod-smoke` | prod, `-m smoke` | только вручную |

develop разбит на API/UI, чтобы каждая джоба укладывалась в часовой лимит проекта и шла параллельно.
Артефакты: `results/` на 1 день (`expire_in: 1 days`, `when: always` — остаются и при падении тестов),
`junit.xml` подхватывается во вкладку Tests пайплайна. Раннеру нужны: тег `devspark-builder` для сборки
и `devspark-docker` для прогона (поправить под ваши раннеры), сетевой доступ к стендам `*.devspark.ru`
и `*.ranepa.ru`, около 2 ГБ памяти на задание (Chromium).

## 7. Проверка после развёртывания

```bash
docker run --rm --env-file .env --shm-size=1g auto_tests_vshgu:latest scripts/run.sh --env develop tests/api/test_health.py
```

Два теста health должны пройти за несколько секунд. Затем smoke: `--env develop -m smoke`, ожидаемо около 7 минут.

## 8. Известные ограничения

- Тесты БУК и LPD помечены `env("stage")`: на develop пропускаются, это нормально.
- Часть тестов помечена `xfail` с причиной в отчёте: известные дефекты стендов, не ошибки инфраструктуры.
- Параллельный запуск (`-n auto`) поддерживается, но UI-тесты на одном стенде лучше гонять в 2–4 потока, не больше.
