# auto_tests_vshgu

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

Тесты БУК (`tests/api/buk`, `tests/ui/buk`) и LPD (`tests/api/create_activity/lpd`, `tests/ui/test_user_lpd_*`,
`tests/api/programs/test_assign_activities_api.py`) помечены `env("stage")`: БУК и LPD есть только на stage,
на develop и prod они пропускаются автоматически.

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

## 8. Интеграция БУК (входящий REST)

Тесты `tests/api/buk/` покрывают `POST/PUT/DELETE /api/v1/external/buk/users` по контракту
asuo-buk-api-contracts (§ 2, § 4): автосопоставление по email, ручное по `user_id`,
`rejected` для администраторов, `conflict` для связи 1:1, `DELETE` с идемпотентным повтором,
перепривязка после разрыва, валидация и 403 без токена.

Нужен JWT интеграции в `.env`: `<ENV>_BUK_TOKEN` (передаётся в `Authorization` как есть,
без Bearer). Без токена тесты пропускаются (skip). Сопоставление на сервере асинхронное,
`GET` в контракте нет, поэтому состояние читается повторным `PUT` с тем же телом
(`ExternalBukEndpoint.wait_for_match` / `put_and_wait`), первый опрос — через 6 секунд.
Все переданные `buk_user_id` снимаются `DELETE` в teardown фикстуры `external_buk_endpoint`.

```bash
pytest --env=stage tests/api/buk
```

## 9. Генерация тестовых данных

Единый CLI `test_data_generation/generate.py` создаёт на стенде через `api/endpoints/*.py`
и `api/helpers/data_generator.py` связанные цепочки сущностей (программа → поток → модуль →
слушатели → ... в зависимости от сценария), печатает читаемый итог в консоль и сохраняет
манифест созданного в `test_data_generation/manifests/<env>_<scenario>_<ts>.json`.

```
python test_data_generation/generate.py --env <develop|stage> --scenario <имя> \
    [--count N] [--tenant ID] [--prefix STR] [--dry-run] [--list] [--cleanup manifest.json]
```

- `--env` — `develop` (по умолчанию) или `stage`.
- `--scenario` — имя сценария (см. таблицу ниже), обязателен, если не указаны `--list`/`--cleanup`.
- `--count` — сколько сущностей на единицу плана (смысл зависит от сценария, по умолчанию 1).
- `--tenant` — `tenant_organization_id`, если нужен конкретный тенант.
- `--prefix` — суффикс имён создаваемых сущностей: `Автотест_<prefix>_<ts>`.
- `--dry-run` — без единого сетевого вызова: план шагов и синтетические id в лог, манифест не
  сохраняется (удалять нечего).
- `--list` — вывести список сценариев с описанием и выйти.
- `--cleanup manifest.json` — не создавать, а удалить сущности из ранее сохранённого манифеста.

### Сценарии

| Сценарий | Что делает |
| --- | --- |
| `cas` | программа CAS -> поток -> синхронизация -> модуль -> N пользователей на каждый статус зачисления |
| `users` | N пользователей на каждую роль (слушатель/преподаватель/проверяющий/менеджер/контент-менеджер/админ тенанта) |
| `program_full` | программа -> поток -> модуль -> элемент расписания -> N слушателей -> сертификатный шаблон программы |
| `activities` | программа -> поток -> модуль -> по одной активности каждого типа (tincan/scorm/внешний контент/ДЗ 5-10-зачёт/тест/опрос/АОС/LPD на stage/материал БЗ + достижение) |
| `learner_progress` | слушатель -> назначение на программу с ДЗ в модуле -> отправка ответа (только через UI — нет API) |
| `buk` | N пользователей -> входящий REST БУК (`POST /external/buk/users`) с ожиданием сопоставления по email |
| `certificates` | шаблон сертификата для потока программы (program_stream) и для активности (activity) + назначение |
| `banner_and_partners` | включение инфо-баннера + выдача доступа Alpina/MIF N пользователям |
| `demo` | демо-наполнение стенда: `users` + `program_full` + `activities` + `certificates` + `banner_and_partners` (count=1 на каждый шаг) |

`buk` и активность LPD внутри `activities` реально доступны только на stage (см. раздел 8) —
на develop эти шаги пишутся в манифест как `skipped` с причиной, а не падают.

Пароль создаваемых тестовых пользователей — общий `DEFAULT_PASSWORD` (`test_data_generation/lib.py`,
по умолчанию `SecurePass123`, переопределяется переменной `DEFAULT_PASSWORD` в `.env`); это не секрет
живого стенда, и его можно упоминать в README/логах открыто. А вот куки/токены/логины-пароли живых
учёток из `.env` в README и коммиты по-прежнему не идут (см. раздел 2).

Примеры:

```bash
python test_data_generation/generate.py --list
python test_data_generation/generate.py --env develop --scenario cas --dry-run
python test_data_generation/generate.py --env develop --scenario users --count 2 --prefix smoke
python test_data_generation/generate.py --cleanup test_data_generation/manifests/develop_users_1695312345.json
```

### Манифест и очистка

Манифест — JSON `{"env", "scenario", "created": [{"entity", "id", "how_to_delete"}, ...], "skipped": [...]}`.
`--cleanup` читает его и удаляет записи из `created` в обратном порядке (последняя созданная —
первая удаляемая), для каждой печатая результат (`удалено` / `НЕ удалено` / `пропущено — нет
DELETE-метода`); `--cleanup ... --dry-run` только печатает план без реальных вызовов.

Не для всех сущностей в API есть `DELETE`: например, `stream_assignment`/`certificate_assignment`
не имеют обработчика вообще, а `program` реально удаляется через mass-delete с одним id, потому что
`DELETE /programs/{id}` отдаёт 405. Такие записи `cleanup` явно помечает как пропущенные — это
ожидаемо, часть созданного нужно оценивать по выводу `cleanup`, а не считать удалённым автоматически.

**Правило владельца:** `--env stage` поддерживается кодом (БУК и LPD есть только на stage), но
реальные прогоны генератора на stage выполняются только по команде владельца — при разработке и
проверке этой функциональности запуски делались исключительно на `develop`.

## 10. Перенесено из ветки коллеги

Из ветки `feature/my-tests` коллеги Игоря Захарова (репозиторий `/Users/andreykorotkow/Projects/lms`)
перенесены три блока UI-функциональности, которых в нашем слое не было: практические задания
в админке (создание, прохождение слушателем, проверка, индивидуальное и групповое назначение),
онбординг (первичный и повторный) и база знаний/достижения. Перенос — не копирование файлов:
локаторы коллеги превращены в Page Object'ы на `expect()` (без `is_visible()`-опросов,
`networkidle`/`sleep`), подготовка данных — через наши API-фикстуры с teardown вместо JSON-файлов
на диске.

### Источник → приёмник

Page Object'ы и хелперы:

| Источник (`lms`, `feature/my-tests`) | Приёмник |
| --- | --- |
| `tests/ui/admin/practical_tasks/helpers/create_practical_task.py`, `src/ui/locators/admin_activities_locators.py` | `ui/pages/admin_activities_page.py` |
| `src/ui/locators/admin_programs_locators.py`, `tests/ui/admin/practical_tasks/helpers/{module_schedule,stream_listeners,navigation}.py` | `ui/pages/admin_programs_page.py` |
| `src/ui/locators/admin_stream_groups_locators.py` | `ui/pages/admin_stream_groups_page.py` |
| `src/ui/locators/admin_users_locators.py` | `ui/pages/admin_users_page.py` (поиск по email, карточка → вкладка «Назначения») |
| `src/ui/locators/user_programs_locators.py` | `ui/pages/practical_task_page.py` |
| `src/ui/locators/reviewer_homeworks_locators.py` | `ui/pages/reviewer_page.py` |
| `src/ui/pages/onboarding_page.py`, `src/ui/locators/onboarding_locators.py` | `ui/pages/onboarding_page.py` |
| `src/ui/locators/{library,support,personal_education}_locators.py` | `tests/ui/onboarding/locators.py` (плоские константы, единственный потребитель — тесты онбординга) |
| `tests/ui/knowledge_base_achievements/test_01_admin_create_achievement_material_count.py`, `test_02_admin_create_article_material.py` (действия были прямо в тестах, отдельного locators-файла не было) | `ui/pages/admin_knowledge_base_page.py` |
| `tests/api/helpers/user_prepare_api.py` | `api/helpers/user_prepare_api.py` (под наш `ApiClient`/`config.environments.login`/`expect_status`) |
| — (новая инфраструктура под перенос) | `conftest.py` — хук `pytest_runtest_makereport` (скриншот страницы в allure при падении UI-теста); `pytest.ini` — маркеры `practical_tasks`/`groups`/`onboarding`/`knowledge_base`/`reviewer` |

Тесты, блок «Практические задания»:

| Источник (`lms`, `feature/my-tests`) | Приёмник |
| --- | --- |
| `tests/ui/admin/practical_tasks/test_01_create_practical_task.py` | `tests/ui/practical_tasks/test_create_practical_task.py` |
| `tests/ui/admin/practical_tasks/test_02_create_program_stream_module.py` | `tests/ui/practical_tasks/test_create_program_stream_module.py` |
| `tests/ui/admin/practical_tasks/test_03_add_practical_task_to_module.py` | `tests/ui/practical_tasks/test_add_practical_task_to_schedule.py` |
| `tests/ui/admin/practical_tasks/test_04_add_user_to_stream.py` | `tests/ui/practical_tasks/test_add_listener_to_stream.py` |
| `tests/ui/admin/practical_tasks/test_05_complete_practical_task.py` | `tests/ui/practical_tasks/test_complete_practical_task.py` |
| `tests/ui/admin/practical_tasks/test_06_review_practical_task.py` | `tests/ui/practical_tasks/test_review_practical_task.py` |
| `tests/ui/admin/practical_tasks/personal_assignment/test_10_assign_personal_practical_task.py`, `test_11_create_user_and_assign_personal_practical_task.py` | `tests/ui/practical_tasks/personal_assignment/test_assign_from_user_card.py` |
| `tests/ui/user/personal_practical_tasks/test_12_complete_personal_practical_task.py`, `tests/ui/reviewer/personal_practical_tasks/test_13_review_personal_practical_task.py` | `tests/ui/practical_tasks/personal_assignment/test_complete_and_review_personal_assignment.py` |
| `tests/ui/admin/practical_tasks/groups/test_14_create_group_for_stream.py` | `tests/ui/practical_tasks/groups/test_create_group_for_stream.py` |
| `tests/ui/user/group_practical_tasks/test_15_complete_group_practical_task.py`, `test_15_1_edit_group_practical_task_by_second_user.py`, `tests/ui/reviewer/group_practical_tasks/test_16_review_group_practical_task.py` | `tests/ui/practical_tasks/groups/test_group_practical_task_flow.py` |

Тесты, блок «Онбординг»:

| Источник (`lms`, `feature/my-tests`) | Приёмник |
| --- | --- |
| `tests/ui/onboarding/test_00_my_learning_page_first_time_onboarding.py`, `test_01_knowledge_base_first_time_onboarding.py`, `test_02_support_page_after_onboarding.py`, `test_03_personal_education_first_time_onboarding.py` | `tests/ui/onboarding/test_primary_onboarding.py` |
| `tests/ui/onboarding/test_04_repeat_onboarding_close_button.py`, `test_05_knowledge_base_repeat_onboarding.py`, `test_06_personal_education_repeat_onboarding.py`, `test_07_support_repeat_onboarding.py` | `tests/ui/onboarding/test_repeat_onboarding.py` |
| `tests/ui/onboarding/conftest.py` (как справочник по составу фикстур, не дословно — см. докстринг файла) | `tests/ui/onboarding/conftest.py` |

Тесты, блок «База знаний»:

| Источник (`lms`, `feature/my-tests`) | Приёмник |
| --- | --- |
| `tests/ui/knowledge_base_achievements/test_01_admin_create_achievement_material_count.py` | `tests/ui/knowledge_base/test_create_achievement.py` |
| `tests/ui/knowledge_base_achievements/test_02_admin_create_article_material.py` | `tests/ui/knowledge_base/test_create_article_and_verify_in_user_ui.py` |

### Новые маркеры

- `practical_tasks` — создание/прохождение/проверка практических заданий, включая индивидуальное
  назначение (`tests/ui/practical_tasks/`, в т.ч. `personal_assignment/`).
- `groups` — группы потока и групповые практические задания (`tests/ui/practical_tasks/groups/`).
- `onboarding` — первичный и повторный онбординг (`tests/ui/onboarding/`).
- `knowledge_base` — база знаний: достижения и статьи (`tests/ui/knowledge_base/`).
- `reviewer` — зарезервирован под сценарии роли «Проверяющий»; на момент переноса ни один тест
  им не помечен, роль проверяющего пока покрыта тестами с маркером `practical_tasks`
  (`test_review_practical_task.py`, `personal_assignment/test_complete_and_review_personal_assignment.py`).

```bash
pytest --env=develop -m practical_tasks
pytest --env=develop -m groups
pytest --env=develop -m onboarding
pytest --env=develop -m knowledge_base
```

### Итог прогона на develop

Всего перенесено 20 тестов: 8 зелёных, 12 помечены `xfail(strict=False)` — во всех 12 причина
в дефектах стенда develop, а не в переносе:

- `test_create_program_stream_module` — после «Сохранить» форма потока остаётся на
  `/streams/create` с текстом «обязательно для заполнения» под всеми пятью select-полями, хотя
  клик по каждому и выбор пункта проходят без исключений.
- `test_complete_practical_task` — после API-назначения программа не появляется в «Моё обучение»
  слушателя (видны только 2 демо-карточки).
- `test_review_practical_task` — тот же дефект, что в `test_complete_practical_task`: подготовка
  ответа слушателя перед проверкой зависит от появления программы в «Моё обучение».
- `personal_assignment/test_complete_and_review_personal_assignment` — тот же класс дефекта:
  индивидуально назначенное ПЗ не появляется в разделе «Индивидуальное обучение» слушателя.
- 4 теста `test_primary_onboarding.py` — модалка «Интерактивное руководство» после клика
  «Пройти обучение» не всегда переходит к слайду «Далее» (до 5 повторных кликов не помогают).
- 4 теста `test_repeat_onboarding.py` — кнопка перезапуска онбординга не открывает модалку тура
  повторно; тот же класс проблемы, что и в первичном онбординге.

Зелёные: `test_create_practical_task`, `test_add_practical_task_to_schedule`,
`test_add_listener_to_stream`, `personal_assignment/test_assign_from_user_card`,
`groups/test_create_group_for_stream`, `groups/test_group_practical_task_flow`,
`test_create_achievement`, `test_create_article_and_verify_in_user_ui`.

### Что не переносилось

- JSON-контексты на диске (`chain_context.py`, `group_context.py`, `personal_pz_context.py`) —
  у коллеги данные между шагами сценария передавались через файлы; у нас то же состояние живёт
  в API/UI-фикстурах с teardown (`created_user`, `created_program` и т.п.), без файлов на диске.
- Скриншоты и `.docx`/`.xlsx` коллеги из git — заменены на свои маленькие (<2 КБ) файлы в
  `test_data/`, чтобы не тащить чужие бинарники в наш git.
- `test_99_cleanup_practical_tasks_chain.py` — ручная очистка по `chain_context.py`; у нас каждый
  тест убирает за собой сам через API-teardown фикстур, отдельный cleanup-тест не нужен.
- Дублирующийся хук `pytest_runtest_makereport` — у коллеги он объявлен в нескольких
  `conftest.py`; у нас один, в корневом `conftest.py`.
- `headless=False`/`slow_mo` в коде — у коллеги браузер жёстко запускался видимым с искусственной
  задержкой ~700 мс на шаг; у нас headless берётся из окружения (`HEADLESS` в Docker, см. раздел 7),
  захардкоженной паузы нет.

## 11. Перенесено из feature/dashboard-autotests

Из ветки `origin/feature/dashboard-autotests` (тот же репозиторий `lms` коллеги Игоря Захарова,
что и в разделе 10, но отдельная, несведённая с нашей история — код брался точечно через
`git show <sha>:<путь>`) перенесены материалы и достижения базы знаний в админке, тест дашбордов
статистики программ/курсов и логика очистки группового практического задания. Перенос — не
копирование файлов: `cleanup_manager` и ручные локаторы коллеги превращены в наши Page Object'ы
на `expect()`, подготовка данных — в наши API-фикстуры с `yield`-teardown вместо JSON-хелперов
коллеги (`dashboard_prepare_api.py`, `knowledge_base_material_prepare_api.py`) и отдельного
теста-очистки `test_99_*`.

### Источник → приёмник

Материалы и достижения БЗ (админка):

| Источник (`lms`, `feature/dashboard-autotests`) | Приёмник |
| --- | --- |
| `tests/ui/knowledge_base/materials/test_01_admin_create_article_material.py` | не переносился повторно — уже перенесён в разделе 10 как `tests/ui/knowledge_base/test_create_article_and_verify_in_user_ui.py` |
| `tests/ui/knowledge_base/materials/test_02_admin_create_video_material.py` | `tests/ui/knowledge_base/test_create_material_video.py` |
| `tests/ui/knowledge_base/materials/test_03_admin_create_audio_material.py` | `tests/ui/knowledge_base/test_create_material_audio.py` |
| `tests/ui/knowledge_base/materials/test_04_admin_create_book_material.py` | `tests/ui/knowledge_base/test_create_material_book.py` |
| `tests/ui/knowledge_base/materials/test_05_admin_create_file_material.py` | `tests/ui/knowledge_base/test_create_material_file.py` |
| `tests/ui/knowledge_base/materials/test_06_admin_create_course_material.py` | `tests/ui/knowledge_base/test_create_material_course.py` |
| `tests/ui/knowledge_base/achievements/test_01_admin_create_achievement_material_count.py` (условие «статья») | `tests/ui/knowledge_base/test_create_achievement.py::test_create_achievement` |
| `tests/ui/knowledge_base/achievements/test_02..06_admin_create_achievement_material_count_{video,audio,book,file,course}.py` | `tests/ui/knowledge_base/test_create_achievement.py::test_create_achievement_material_count_for_type` (`parametrize` по 5 типам материала) |

Дашборды:

| Источник (`lms`, `feature/dashboard-autotests`) | Приёмник |
| --- | --- |
| `src/ui/pages/dashboard_page.py` (локаторы) | `ui/pages/admin_dashboard_page.py` |
| `tests/api/helpers/dashboard_prepare_api.py`, `tests/ui/dashboards/conftest.py` (JSON-подготовка данных коллеги — не копировалась дословно) | `tests/ui/dashboards/conftest.py` — фикстуры `dashboards_admin_page`/`dashboard_data` на наших API-фикстурах/эндпоинтах (`created_schedule_item`, `created_tincan`, `created_user`, `assignments_endpoint`, `modules_endpoint`, `schedule_items_endpoint`, `dashboards_endpoint`) |
| `tests/ui/dashboards/test_01_admin_checks_program_and_course_dashboards.py` | `tests/ui/dashboards/test_admin_checks_program_and_course_dashboards.py` |

Практические задания — перенос очистки:

| Источник (`lms`, `feature/dashboard-autotests`) | Приёмник |
| --- | --- |
| `tests/ui/cleanup/test_99_cleanup_practical_tasks_chain.py` (отдельный тест-очистка, запускался последним по всей цепочке) | teardown фикстуры `group_practical_task` (`tests/ui/practical_tasks/groups/conftest.py`) |

Тест правки группового ПЗ вторым пользователем (`test_15_1_edit_group_practical_task_by_second_user.py`
коллеги из ветки `feature/my-tests`, см. раздел 10) на момент этой задачи уже был встроен в
`tests/ui/practical_tasks/groups/test_group_practical_task_flow.py` шагом 4 — отдельный файл не
потребовался, только рефакторинг: тест переведён на фикстуру `group_practical_task` вместо
ручного `try/finally` с `homework_endpoint.mass_delete()`.

Достижения БЗ — слушатель и админ-статистика:

| Источник (`lms`, `feature/dashboard-autotests`) | Приёмник |
| --- | --- |
| `tests/ui/knowledge_base/user_achievements/test_01..09_*.py` (9 тестов: получение достижения слушателем по каждому из 6 типов материала + 3 составных сценария) | `tests/ui/knowledge_base/user_achievements/conftest.py` (фикстуры `material_for_type`, `achievement_for`, teardown) + `test_user_gets_achievement_by_material.py` (`parametrize` по 6 типам: статья/аудио/видео/книга/файл/курс) + `test_user_gets_complex_achievement.py` (3 составных сценария: аудио+книга, файл+книга, две книги) |
| `tests/ui/knowledge_base/admin_statistics/test_01_admin_sees_user_achievement_history.py` | `tests/ui/knowledge_base/admin_statistics/test_admin_sees_user_achievement_history.py` |
| `tests/ui/knowledge_base/admin_statistics/test_02_admin_sees_user_in_knowledge_base_rating.py` | `tests/ui/knowledge_base/admin_statistics/test_admin_sees_user_in_knowledge_base_rating.py` |

### Новые маркеры

- `dashboards` — тесты дашбордов статистики программ/курсов в админке (`tests/ui/dashboards/`).

### Итог прогона на develop

- Материалы БЗ (5 новых тестов: видео/аудио/книга/файл/курс) и достижения БЗ (6 тестов: статья +
  5 типов параметризацией) — суммарно 12 сценариев (5 новых материалов, тест статьи, задетый
  рефакторингом `select_material_type`, и 6 достижений), все зелёные, 2/2 на develop, `HEADLESS=1`.
- `test_admin_checks_program_and_course_dashboards` — `xfail(strict=False)`: из 3 прогонов на
  develop (бюджет исчерпан) 1 прошёл чисто за 62.8с, 1 упал на поиске строки программы в таблице
  дашборда (30с таймаут, хотя API уже подтвердил появление строки), 1 упал в setup на обрыв
  соединения при создании программы (`ConnectionError`). Разведочным прогоном подтверждено, что
  поиск/рендер строки в целом работает (строка с верными значениями появляется за ~8с) — похоже
  на нестабильность стенда develop, а не на дефект теста/Page Object.
- `test_group_practical_task_flow` (после перевода на фикстуру `group_practical_task`) — 2/2
  зелёных прогона на develop (`--env=develop`, `HEADLESS=1`): 249.73с, 235.46с.
- `test_user_gets_achievement_by_material` (6 параметров: статья/аудио/видео/книга/файл/курс) —
  6 passed. Вариант `course` сначала был помечен xfail как «дефект стенда» (клик по «Приступить к
  изучению» уводил вкладку на `/404`), но причина оказалась в тестовых данных: курс создавался с
  захардкоженным `archive_uuid`, для такого контента `GET /content/launch/{id}` отвечает 404
  «курс не найден». С 25.09.2026 фикстура `material_for_type("course")` загружает архив
  `test_data/course_tincan.zip` заново, launch отвечает 200 и курс открывается в новом окне
  (проверено на develop, в том числе на материале 469). Xfail снят; на первом заходе вариант
  `course` может упасть по таймингу попапа и проходит с повтора.
- `test_user_gets_complex_achievement` (3 составных сценария: аудио+книга, файл+книга, две книги) —
  3 passed, стабильно 2/2.
- `admin_statistics/test_admin_sees_user_achievement_history`,
  `admin_statistics/test_admin_sees_user_in_knowledge_base_rating` — 2 passed, стабильно 2/2 (в
  одном из прогонов сработал 1 rerun — проектный `flaky(reruns=1)` для маркера `ui`, не
  специфично для этой задачи).
- Итого по 11 тестам достижений/статистики БЗ: **10 passed + 1 xfail(strict=False)** одинаково в
  обоих прогонах, ни одного error/failed мимо xfail-причины. Teardown проверен отдельным запросом
  к API по фикстурным префиксам (`Автотест_Достижение`/`Автотест_Материал`) — 0 «осиротевших»
  записей после обоих прогонов.

## 12. Статистика обучения → Курсы

Автотесты раздела админки «Статистика обучения → Курсы»
(`/admin/learning-statistics/courses/{id}/info`: карта РФ + диаграммы, фильтр, итоговая таблица
слушателей, выгрузка в xlsx) написаны по плану `docs/plans/statistics_courses_plan.md` — в
репозитории нет текста ПМИ/ДТТ по этому разделу, план составлен по номерам блоков от владельца
(карта 1-9, фильтрация 10-17, столбцы таблицы 18, прогресс 19-21, выгрузка 22-25) и по факту
того, что реально работает на develop. Перед реализацией владелец дал `docs/plans/statistics_courses_stand_facts.md`
со скриншотами фактических столбцов таблицы (состав столбцов зависит от курса: SCORM/TinCan без
разделов — 8 столбцов, TinCan с разделами, эталон id=4393 — 9 столбцов + блок повторений
прохождения контента) — эти факты закрыли открытый в плане вопрос о составе столбцов (ДТТ п.3.2.2
в репозитории не было).

### Источник → приёмник

| План/факты (`docs/plans/`) | Приёмник |
| --- | --- |
| `statistics_courses_plan.md`, шаги 1-9 (карта — общий вид) | `tests/ui/learning_statistics/test_courses_map.py` |
| `statistics_courses_plan.md`, шаги 10, 15-17 (фильтрация, UI) | `tests/ui/learning_statistics/test_courses_filters.py` |
| `statistics_courses_plan.md`, шаги 11-12 (фильтрация, API) | `tests/api/learning_statistics/test_courses_dashboard_filters.py` |
| `statistics_courses_plan.md`, шаг 18 + `statistics_courses_stand_facts.md` (фактические столбцы курса с разделами) | `tests/ui/learning_statistics/test_courses_table_columns.py` |
| `statistics_courses_plan.md`, шаги 19-21 (прогресс прохождения) | `tests/ui/learning_statistics/test_courses_table_progress.py` |
| `statistics_courses_plan.md`, шаги 22-24 (выгрузка) | `tests/ui/learning_statistics/test_courses_export.py` |
| Инфраструктура (Page Object карты/диаграмм/фильтра/таблицы/выгрузки, эндпоинт) | `ui/pages/admin_dashboard_page.py` (`AdminDashboardPage.open_course_statistics`/`open_course_statistics_by_id`, `AdminCourseStatisticsPage`), `api/endpoints/dashboards.py` |
| Общие фикстуры данных (`course_with_listeners`/`course_without_listeners`) | `tests/conftest.py` (видны и API-, и UI-тестам раздела) |

Разведкой перед написанием тестов (одноразовые скрипты вне pytest, не сохранены в репозитории)
уточнены реальные ограничения стенда develop, из-за которых часть шагов плана переоформлена или
осталась непокрытой:

- шаги 5-6 (подсветка/интенсивность региона по данным слушателей) — заливка `<path>` региона на
  карте одинаковая у региона с данными и без (`getComputedStyle(el).fill`), никакого CSS-класса/
  атрибута, зависящего от % прохождения, в вёрстке нет (кроме `_selected`, который появляется
  только по клику) — не автоматизируется через DOM;
- шаг 7 (тултип региона при наведении) — `hover()` виснет в бесконечном ретрае actionability,
  обходной `dispatch_event('mouseover')` создаёт элемент `[class*='tooltip']`, но невидимый и с
  пустым текстом — не покрыт;
- шаг 19 (статус «в процессе» через API) — `AssignmentsEndpoint.change_state` на develop
  принимает только `state=2` (`CONTENT_STATE_PASSED`), `CONTENT_STATE_LAUNCHED=1` и остальные
  значения отклоняются 422 — `xfail`;
- шаг 21 («Время прохождения, мин» с допуском) — без реального прохождения в UI-плеере
  `completion_time_in_minutes` остаётся пустым даже после перевода в «Пройдено» через API;
  реальное прохождение заблокировано известными xfail-дефектами `test_user_tincan_flow.py` и
  `test_user_tincan_individual_flow.py` — `xfail`;
- шаг 24 (состав выгрузки после фильтра/поиска) — кнопка «Выгрузить» всегда отдаёт полный список
  слушателей независимо от применённого фильтра, воспроизведено дважды за 3 прогона — `xfail` с
  точным описанием;
- шаги 8 (drill-down по клику на регион), 13-14 (фильтр по периоду/региону — `DashboardsEndpoint`
  не поддерживает такие параметры) и 25 (выгрузка большого набора без потери строк) не покрыты —
  вне бюджета задачи или прямо помечены в плане «требует ручной сверки с ДТТ».

xlsx-выгрузка (шаги 22-24) проверяется без добавления `openpyxl` в `requirements.txt` (открытый
вопрос №3 плана закрыт без новой зависимости): xlsx — ZIP-архив с XML внутри, `test_courses_export.py`
читает его стандартным `zipfile` — строковый пул `xl/sharedStrings.xml` для проверки текста ячеек
(ФИО слушателя, метка потока) и подсчёт `<row>` в `xl/worksheets/sheet1.xml` минус 2 строки
заголовков для числа строк слушателей.

### Новые маркеры

Новый маркер в pytest.ini для этой задачи не добавлялся — тесты используют `statistics`
(«Карточка статистики курса: карта, фильтр, таблица, выгрузка»), заведённый раньше вместе с
инфраструктурой (`AdminDashboardPage`/`AdminCourseStatisticsPage`, `api/endpoints/dashboards.py`),
плюс обычные `api`/`ui`.

### Итог прогона на develop

Бюджет — не больше 3 прогонов на файл, `HEADLESS=1`, `--env develop`:

- `test_courses_map.py` — 3/3 green (стабильно, 2 прогона подряд).
- `test_courses_filters.py` (UI) — 3/3 green на 3-м (последнем) прогоне, после двух найденных и
  исправленных гонок в тестовом коде; повторного подтверждающего прогона не осталось — бюджет
  исчерпан.
- `test_courses_dashboard_filters.py` (API) — 2/2 green (стабильно, 2 прогона подряд).
- `test_courses_table_columns.py` — 2/2 green (стабильно, 2 прогона подряд).
- `test_courses_table_progress.py` — 1 green + 2 xfailed (стабильно, 2 прогона подряд).
- `test_courses_export.py` — 2 green + 1 xfailed на 3-м (последнем) прогоне.

### Не автоматизировано

- **Цвет региона на карте по пикселям/скриншоту.** Проверяется не визуально, а через DOM
  (`getComputedStyle`/CSS-класс), которые на практике оказались одинаковыми для региона с
  данными и без — см. xfail-заметку по шагам 5-6 выше; скриншот-сравнение изначально
  отклонено как хрупкое к визуальному шуму и не дающее содержательной ошибки при падении.
- **«Время прохождения, мин» — точное совпадение.** Планировалось сравнение с допуском ±N минут
  вместо посекундного из-за лага между действием слушателя и пересчётом статистики (тот же класс
  дефекта, что и `xfail` в `test_admin_checks_program_and_course_dashboards`, раздел 11); на
  практике поле вообще осталось пустым без реального UI-прохождения — шаг 21 оформлен `xfail`,
  а не проверкой с допуском.
- **Состав столбцов таблицы (ДТТ п.3.2.2) и структура xlsx-отчёта (ДТТ п.3.3.1).** Этих
  документов нет в репозитории. Столбцы для курса с разделами зафиксированы `test_courses_table_columns.py`
  как регрессионный снимок факта (по `statistics_courses_stand_facts.md`), а не как сверка с ДТТ;
  состав данных в выгрузке (шаг 24 плана) по этой же причине не сверялся построчно с ДТТ, только
  на уровне «файл валиден и содержит ожидаемые строки/текст».
- **Drill-down по клику на регион карты (шаг 8).** Поведение неочевидно ни из кода, ни из
  доступных описаний — сверка со стороны владельца.

## 13. Уведомления и техподдержка: что покрыто

По плану `docs/plans/2026-09-24_notifications_tickets_mission.md` разведаны и реализованы
API-клиенты `NotificationsEndpoint` (`api/endpoints/notifications.py`, 19 методов на все
подтверждённые разведкой маршруты `/api/v1/notifications/*`) и `TicketsEndpoint`
(`api/endpoints/tickets.py`, 5 методов на `/api/v1/tickets/*`), генераторы данных
`generate_notification_payload`/`generate_notification_template_payload`/`generate_ticket_payload`
(`api/helpers/data_generator.py`), по методике проб (временные ad-hoc скрипты вне pytest, не
сохранены в репозитории; для `POST /notifications/create` тело запроса подсмотрено через
перехват сетевого запроса Playwright в форме создания уведомления в админке).

**API-тесты «Обращения в техподдержку»** (`tests/api/tickets/`, 11 тестов, план «Часть 3»
п.1-5) написаны и зелёные на develop (2 прогона подряд, `pytest tests/api/tickets --env develop
-q` → 7 passed, 4 xfailed, ~90с): `test_tickets_crud_api.py` (создание → id находится через
`my-tickets`, статус `open` → `close` → статус `closed`, + 2 xfail на повторное закрытие/
сообщение в закрытый тикет), `test_tickets_messages_api.py` (порядок сообщений в переписке),
`test_tickets_negative_api.py` (422 на пустые title/text/весь payload, + 2 xfail на IDOR с
двумя по-настоящему разными пользователями).

Маршрут `POST /notifications/register-templates/{type}` в плане не значился явным списком
(в мишн-доке — только 8 GET-эндпоинтов разведки), но обнаружен пробой методов (405 с
`Supported methods`) и подтверждён рабочим round-trip-вызовом. Итоговое число маршрутов
`/notifications/*`, подтверждённых пробой (`PATCH`/`DELETE` на каждый путь → сообщение Laravel
`Supported methods: ...`) — 19, а не заявленные в плане 23; расхождение не расследовалось глубже
(вероятно, число 23 в плане включало нейтральные HEAD-варианты или маршруты вне `/notifications/*`
префикса, к которым у задачи не было доступа) — при написании тестов дополнительные маршруты можно
доразведать тем же способом.

### Часть 1 (API-тесты уведомлений) — реализована

`tests/api/notifications/` (22 теста, `pytest tests/api/notifications --env develop -q` →
**18 passed, 4 xfailed**, стабильно на 2 прогонах подряд), маркер `notifications`. Покрыты
маршруты: `GET /notifications` (список + поля свежесозданного уведомления), `GET
/notifications/{id}`, `GET /notifications/creators`, `GET /notifications/receivers`, `GET
/notifications/text-variables`, `POST /notifications/create`, `POST /notifications/resend/{id}`,
`POST /notifications/delete`, `GET /notifications/templates` (+ `/{id}`), `POST
/notifications/templates`, `PUT /notifications/templates/{id}`, `POST
/notifications/templates/delete`, `GET /notifications/register-templates` (+ `/{type}`), `POST
/notifications/register-templates/{type}` (round-trip с восстановлением исходных значений в
`finally`), `GET /notifications/review-templates`.

Попутно найден и исправлен реальный дефект в `NotificationsEndpoint.list()`
(`api/endpoints/notifications.py`): `GET /notifications` пагинирован (25 записей на страницу,
663+ уведомлений на develop) без сортировки «новые сверху» — без `per-page=<большое число>`
`list()`/`find_by_name()` не находили только что созданные уведомления (ложноотрицательный
результат). Добавлен параметр `per_page: int = 2000`.

Не покрыто в рамках этой задачи: `GET /notifications/review-templates/{id}` и его `PUT` —
на develop список review-templates пуст, безопасного существующего id для round-trip нет
(создать шаблон через API нельзя — эндпоинта создания в разведанном списке маршрутов нет).

### Часть 2 и 3 (UI-тесты) — реализована

`tests/ui/notifications/` и `tests/ui/tickets/`, маркер `ui` (+ `notifications` для
уведомлений), Page Object из `ui/pages/notifications_page.py` /
`ui/pages/admin_notifications_page.py` / `ui/pages/tickets_page.py` (задача t4).
`pytest tests/ui/notifications tests/ui/tickets --env develop -q` → **2 passed, 1
xfailed** (~100с), стабильно на 2 прогонах каждой папки по отдельности перед объединением.

- `tests/ui/notifications/user/test_user_sees_notification.py` — уведомление создаётся через
  `NotificationsEndpoint.create` с получателем `current_user_id` (id аккаунта, под которым
  авторизован `user_page`, определяется через `GET /auth/me`, без хардкода); в
  `/portal-notifications` проверяются тема и текст. Разведкой (ad-hoc скрипт вне pytest)
  установлено, что реальная лента слушателя работает через отдельный, не описанный в плане
  API `GET /api/v1/my-notifications` (не `/notifications/*` из Части 1 — тот закрыт для роли
  слушателя, см. ниже), и что тема, которую показывает карточка (`.portal-notification__title`),
  — это поле `caption`, а не `name` (`name` в карточке не отображается вовсе, это только
  внутренний идентификатор для админского списка `/notifications`). Появляется в ленте сразу
  после создания, без заметной задержки.
- `tests/ui/notifications/admin/test_admin_notifications_table.py` — опциональный тест из
  плана; xfail (см. кандидат в дефект ниже).
- `tests/ui/tickets/user/test_user_creates_ticket.py` — обращение создаётся через реальную
  UI-форму (не через API), находится в списке (докручиваем `#rooms-list` до появления строки —
  список общего тестового аккаунта develop уже содержит 100+ обращений и не отсортирован по
  дате, см. кандидат в дефект в §13 выше), переписка открывается и своё сообщение в ней видно.
  Текст обращения для этого теста без `"_"` (см. кандидат в дефект ниже) — только тема
  сохраняет префикс `Автотест_` через `generate_ticket_payload`. Teardown закрывает обращение
  через `TicketsEndpoint.close` по id, найденному через `find_by_title` сразу после создания
  (не после UI-проверок) — так teardown срабатывает, даже если сама UI-проверка упадёт.

### Кандидаты в дефекты (подтверждены тестами, xfail(strict=False))

- **`GET /notifications/{id}` и `GET /notifications/register-templates/{type}` на несуществующий
  id/type** — `id` отдаёт 404 с полным стек-трейсом Laravel-исключения в теле ответа (утечка
  деталей реализации наружу), а `type` вместо 404 отдаёт 200 с `{"type": null, "title": null,
  "body": null}` — непоследовательно между похожими эндпоинтами.
- **`POST /notifications/delete` и `POST /notifications/templates/delete` — непредсказуемая
  задержка удаления, не просто «несколько секунд».** Ответ `200 {"status": "success"}` приходит
  сразу, но объект ещё какое-то время виден в `GET /notifications/{id}`/`GET
  /notifications/templates`. При написании тестов Часть 1 задержка перепроверена дважды на
  develop: один раз объект пропадал за ~2 c, другой раз оставался видимым больше 100 c —
  разброс на два порядка, не «5-10 c», как показала более ранняя разведка. Надёжного окна
  ожидания для синхронного assert нет — `test_delete_notification_removes_it` и
  `test_delete_template_removes_it_from_list` ждут до 12 c и уходят в `xfail(strict=False)`,
  если объект не пропал.
- **`POST /notifications/create` без получателей/программ/потоков — план ждал 422, факт 201.**
  `generate_notification_payload(users=[], programs=[], streams=[])` создаёт «уведомление в
  никуда» с кодом 201 вместо ожидаемой валидационной ошибки — сервер не проверяет, что у
  уведомления есть хоть одна аудитория (`test_create_without_receivers_returns_422`, xfail).
- **`POST /notifications/create` — `users` в ответе создания.** В ответе на сам `POST /create`
  (201) поле `users` приходит пустым (`[]`), хотя в теле запроса передавались получатели и
  `GET /notifications/{id}` сразу после создания их уже показывает — расхождение между ответом
  create и последующим get.
- **`POST /tickets`, `POST /tickets/{id}/messages` не возвращают ID.** Ответ обоих — плоское
  `{"message": "Ok"}`, без id созданного тикета/сообщения — тестам нужно искать созданный тикет по
  теме через `my-tickets` (см. `TicketsEndpoint.find_by_title`).
- **`GET /tickets/{id}/messages`, `PUT /tickets/{id}/close`, `POST /tickets/{id}/messages` —
  подтверждённый IDOR.** Перепроверено (не разведкой, а тестами `test_tickets_negative_api.py`)
  с двумя по-настоящему разными пользователями: второй создан через `UsersEndpoint.create` и
  залогинен отдельно (`config.environments.login`), а не через `admin_session`/`user_session`,
  которые на develop — один и тот же аккаунт (в `.env` нет `DEVELOP_ADMIN_LOGIN`/
  `DEVELOP_USER_LOGIN`, обе роли фолбэк-ятся на общий `DEVELOP_LOGIN`, id=3). Второй пользователь
  свободно читает переписку, закрывает и пишет сообщения в чужое обращение — все три маршрута
  отвечают 200 вместо ожидаемых 403/404, без какой-либо проверки владения тикетом. xfail в
  `test_foreign_ticket_messages_forbidden`/`test_foreign_ticket_close_forbidden`.
- **`PUT /tickets/{id}/close` и `POST /tickets/{id}/messages` на уже закрытый тикет.** Оба
  отвечают 200 без ошибки (повторное закрытие и сообщение в закрытый тикет не блокируются) — план
  ожидал 4xx, реальность мягче. xfail в `test_repeat_close_is_rejected`/
  `test_message_to_closed_ticket_is_rejected`.
- **`PUT /tickets/{id}/close` — спорадический 500.** Один раз из нескольких прогонов вернул
  `500 {"message": "The HTTP status code \"0\" is not valid.", "exception":
  "InvalidArgumentException", ...}` (симфони/Laravel exception) вместо обычного `200 {"message":
  "Ok"}`; на повторном вызове того же запроса прошёл штатно — не воспроизводится стабильно,
  похоже на редкую нестабильность стенда develop, не зафиксировано отдельным тестом (не
  воспроизводится детерминированно), но teardown тестов ловит и логирует такие сбои, а не роняет
  тест.
- **`GET /tickets/my-tickets` — пагинация без поддержки reverse-сортировки.** `per_page=25`,
  сортировка по возрастанию `created_at`/`id`; `?sort=-created_at`, `?sort=-id`, `?order=desc`
  сервером молча игнорируются (ответ идентичен запросу без параметров) — узнать «последний
  созданный тикет» можно только листая страницы вручную. Не дефект стенда сам по себе, но ломает
  наивный `TicketsEndpoint.find_by_title` (был на первой странице) на аккаунте с историей больше
  25 обращений — обычное дело для общего тестового аккаунта develop уже через десяток прогонов.
  Исправлено в этой задаче: `find_by_title` листает страницы от последней к первой (см.
  `api/endpoints/tickets.py`).
- **`admin_session`/`user_session` на develop — один и тот же аккаунт.** В `.env` нет
  `DEVELOP_ADMIN_LOGIN`/`DEVELOP_USER_LOGIN`, поэтому обе роли фолбэк-ятся на общий
  `DEVELOP_LOGIN` (аккаунт с ролями `admin`+`manager`, id=3) — сценарии «пользователь видит только
  свои уведомления/тикеты, не чужие» физически нельзя проверить без создания отдельного тестового
  пользователя через `UsersEndpoint.create` и логина под ним. В Часть 1 (`tests/api/notifications`)
  негативный тест доступа обошёл это через `UsersEndpoint.create` + `config.environments.login` (тот
  же приём, что уже применялся в `tests/api/users/test_users_permissions_api.py`) — и выяснилось,
  что весь раздел `/notifications/*` целиком закрыт для обычной роли слушателя без
  админ/менеджерских прав (`GET /notifications/{id}` отдаёт 403 «У Вас нет доступа к данному
  разделу» независимо от того, адресовано ли конкретное уведомление этому пользователю). Так что
  `/notifications/*` — не персональный inbox слушателя, а админский инструмент рассылки; личная
  лента уведомлений слушателя (пункт «Уведомления» в сайдбаре, `/portal-notifications`, см.
  `ui/pages/user_sidebar_page.py`) работает через другой API — `GET /api/v1/my-notifications`
  (разведано в Части 2, см. `tests/ui/notifications/user/test_user_sees_notification.py`), не
  через `/notifications/*`.
- **Уведомление не появляется в таблице админки после отправки.** Уведомление, созданное через
  `POST /notifications/create` (`send_at=null`) и затем явно отправленное через `POST
  /notifications/resend/{id}` (ответ 200 `{"status": "success"}`), не появляется в таблице
  «Все уведомления» (`/admin/notifications?i=3`) ни сразу, ни после ~20 c ожидания с
  перезагрузкой страницы — воспроизведено ad-hoc скриптом вне pytest и тестом
  `test_admin_sees_created_notification_in_table` (`xfail`). Не выяснено, сохраняется ли это
  дольше (по аналогии с задержкой удаления выше разброс может быть на порядки).
- **Переписка обращения (`.vac-format-message-wrapper`) вырезает `"_"` как markdown-курсив,
  непредсказуемо для строк с несколькими `"_"`.** `_текст_` рендерится без подчёркиваний, но
  сам текст остаётся видимым; для строки с нечётным числом `"_"` (например, стандартного вида
  `generate_ticket_payload().text`, который включает title с 3 подчёркиваниями) простое
  `text.replace("_", "")` не совпадает с фактическим рендером — часть текста теряет
  подчёркивания парами, а «лишнее» с конца остаётся как есть. UI-тест обращения
  (`test_user_creates_ticket.py`) обходит это, задавая текст обращения без `"_"` явно, вместо
  того чтобы предсказывать результат разбора markdown.

## 14. Справочники: что покрыто

По плану `docs/plans/2026-09-25_dictionaries_mission.md` разведан единый REST-ресурс
`/dictionaries` (не набор отдельных сущностей — один Laravel-ресурс на backing-enum
`Dictionaries\Enums\DictionaryType`, общий для восьми известных типов: `project`,
`program_level`, `program_department`, `program_type`, `learning_format`, `tag`, `region`,
`municipality`). Клиент — `DictionariesEndpoint` (`api/endpoints/dictionaries.py`), генератор
данных — `generate_dictionary_payload` (`api/helpers/data_generator.py`).

**API-тесты** (`tests/api/dictionaries/`, 29 тестов, маркер `dictionaries`) зелёные на develop
(4 прогона подряд, `pytest tests/api/dictionaries --env develop -q` → **25 passed, 4 xfailed**,
~45с): `test_dictionaries_crud_api.py` (create/find_by_name/list_by_type/постраничный
list/update/delete по типам без обязательного доп. `meta` — `program_type`,
`program_department`, `learning_format`, `tag`; отдельно 405 на `GET`/`PUT` по id),
`test_dictionaries_negative_api.py` (422 на пустой `name`, права доступа, + 2 xfail-кандидата в
дефект ниже), `test_dictionaries_association_api.py` (поток программы с новым элементом
`program_type` хранит связь через вложенный объект в ответе; пользователь с существующими
`region_id`/`municipality_id` — связь сверяется со справочником `region` по `dictionary_id`).

`region`/`municipality` — read-only справочники ФИАС на develop (мишн-док), тестами не
создаются; связь с ними проверяется на уже существующих элементах через профиль пользователя.

### Модель прав

В отличие от `/notifications/*` (403 целиком для не-админов, см. §13), справочники читаются
любым авторизованным пользователем: `GET /dictionaries/by-type/{type}` под реально другим,
только что созданным обычным пользователем (`UsersEndpoint.create` + `config.environments.login`,
не `admin_session`/`user_session` — на develop это один и тот же аккаунт) отвечает 200.
Запись (`POST`/`PATCH`/`DELETE`) — админский раздел: тот же пользователь получает 403 «У Вас нет
доступа к данному разделу» на `POST /dictionaries`.

### Кандидаты в дефекты (подтверждены тестами, xfail(strict=False))

- **`POST /dictionaries` для `type=project`/`program_level` без `meta.experts_entity_id` ломает
  чтение всего типа для всех пользователей.** По коду (и по мишн-доку) типы `project` и
  `program_level` дополнительно хранят `meta.experts_entity_id`, но `POST /dictionaries {name,
  type}` не требует и не валидирует это поле — создание проходит нормально (201). После этого
  `GET /dictionaries/by-type/{type}` и постраничный `GET /dictionaries?filters[type]=...`
  отвечают **500** `"Undefined array key \"experts_entity_id\""`
  (`Dictionaries/Models/Casts/Meta/ExpertsDictionaryMeta.php`) — сервер падает при сериализации
  на кастинге meta **любого** элемента этого типа, не только сломанного, то есть один
  некорректно созданный элемент вырубает чтение всего справочника (в проде это ломает выпадающий
  список «Проект»/«Стоимостная группа» в форме создания потока программы для всех
  администраторов). Обнаружено во время разведки к этой задаче: элемент случайно остался без
  `meta` после ad-hoc-проверки, стенд develop был на несколько минут в сломанном состоянии для
  чтения типа `project`, пока не найден и не удалён напрямую по id (`find_by_name`/`list_by_type`
  для восстановления не годятся — сами падают, пока сломанный элемент жив). Тест
  `test_create_experts_type_without_meta_breaks_type_reads` (параметризован по обоим типам)
  воспроизводит дефект и тут же лечит стенд в `finally` (`delete` по id из ответа `create()`,
  без похода через `list`/`find_by_name`) — самоизлечивающийся xfail, безопасен для повторных
  прогонов и для параллельных тестов на том же стенде.
- **`PATCH /dictionaries/{id}` для `type=program_department` — детерминированный 500.**
  Штатный `PATCH {"name": "..."}"` на элементе `program_department` (в отличие от
  `program_type`/`learning_format`/`tag`, которые обновляются нормально) отвечает 500 `"0" is not
  a valid backing value for enum Dictionaries\Enums\DictionaryType`
  (`UpdateDictionaryRulesBuilder.php`) — та же по формулировке ошибка приведения enum из
  отсутствующего значения, что и у `POST` без `type` (см. ниже), но здесь воспроизводится на
  update конкретно этого типа. `test_update_program_department_name`, xfail.
- **`POST /dictionaries` без поля `type` — план ждал 422, факт 500.** `"0" is not a valid backing
  value for enum Dictionaries\Enums\DictionaryType` — сервер падает на приведении отсутствующего
  значения к enum до валидации, вместо ожидаемой валидационной 422 (`POST` без `name` при этом
  корректно отвечает 422). `test_create_without_type_returns_422`, xfail.
- **Ссылка на элемент справочника несовпадающего типа в потоке программы — принимается молча,
  без 422.** `generate_stream_payload` требует `project`/`program_level`/`program_department`/
  `program_type`/`learning_format` как обязательные числовые id, но сервер не проверяет, что id
  реально принадлежит ожидаемому типу справочника: id элемента типа `tag`, подставленный в поле
  `project`, не отклоняется (201), просто соответствующее поле в ответе тихо становится `null` —
  как и id несуществующего/из другого типа элемента вовсе. Не оформлено отдельным тестом (риск
  зависеть от подобранных id, замеченного поведения достаточно для отчёта задачи) — при желании
  можно воспроизвести детерминированно через `created_dictionary_item(dictionary_type="tag")` +
  `generate_stream_payload(project=<tag_item_id>)`.

### UI

`tests/ui/dictionaries/` (5 тестов, маркер `dictionaries`) поверх `AdminDictionariesPage`
(`ui/pages/admin_dictionaries_page.py`, раздел «Справочники» в боковом меню админки, 6
подстраниц `/admin/catalogs/*`) — зелёные на develop, **2 прогона подряд**,
`pytest tests/ui/dictionaries --env develop -q -m dictionaries` (HEADLESS=1) → **5 passed**
каждый раз (~4.5–5 мин/прогон, в основном ожидания Vuetify-модалок и селектов).

- `admin/test_admin_dictionaries_crud.py` — CRUD через форму на типе `program_type`
  («Вид программы», единственный безопасный тип для UI-round-trip, см. выше «Модель прав»/
  `SAFE_DICTIONARY_TYPES`): создание, редактирование, удаление — каждый раз с перезагрузкой
  страницы после мутации, чтобы не поверить DOM, ещё не подтверждённому сервером.
- `admin/test_dictionary_program_type_selection.py` — интеграция со формой создания потока
  программы: элемент, созданный в «Справочники», сразу выбирается в поле «Вид программы»
  через `AdminProgramsPage.select_program_type_value(value)` (метод, допечатывающий точное
  имя, а не берущий первый пункт списка, как `select_program_type()`).
- `user/test_dictionaries_admin_access_restricted.py` — обычный пользователь (реально другой
  аккаунт, `second_user_page`, не `user_page`, см. «Модель прав» выше) при прямом переходе на
  `/admin/catalogs/programs` детерминированно редиректится на `/programs` — SPA-роутер не
  пускает в «Админку» целиком, согласуется с 403 на запись API для той же роли. `page.goto`
  здесь на `wait_until="domcontentloaded"`, а не дефолтном `"load"`: под нагрузкой (весь
  каталог тестов разом) SPA держит сеть активной и событие `"load"` не всегда успевает за 30с.

## 15. Тест-кейсы и Test IT

По плану `docs/plans/2026-09-25_test_cases_testit_mission.md`: у каждого автотеста есть
тест-кейс в человеческом виде (шаги и ожидаемые результаты словами, а не именами локаторов),
кейсы хранятся в репозитории и синхронизируются с Test IT.

Кейсы лежат в `docs/test_cases/<area>.md` — один файл на область (соответствует папкам
`tests/api/<area>` и `tests/ui/<area>`), у каждого файла шапка (область/стенд/роли) и набор
блоков `### TC-<AREA>-<NNN> <Название>`. Формат блока и шапки — см. `docs/test_cases/TEMPLATE.md`;
живой образец — `docs/test_cases/notifications.md` и `docs/test_cases/tickets.md` (эти две области,
плюс `learning_statistics`, доведены вручную до читаемого вида, остальные — черновики).

### Черновик кейсов из allure-разметки

`tools/test_cases/generate.py` собирает тесты через `pytest --collect-only` (без запуска),
читает `@allure.feature/story/title/severity`, маркеры и докстринг, шаги — из
`with allure.step("…")` статически (`ast`, без импорта тестовых файлов), и пишет/обновляет
черновики по областям:

```
python tools/test_cases/generate.py [--area <name> ...] [--tests-dir DIR] [--docs-dir DIR]
```

- `--area` — ограничить одной или несколькими областями (можно указывать флаг несколько раз);
  без флага генератор проходит по всему `tests/`.
- `--tests-dir` / `--docs-dir` — переопределить корень тестов/кейсов (по умолчанию `tests/` и
  `docs/test_cases/`).

Повторный запуск идемпотентен: кейсы ищутся по ключу `- Автотест: <node id>`, вручную
отредактированные поля (Приоритет/Роли/Предусловия и текст шагов/результатов) не
перезаписываются. Если шаги автотеста разошлись с прошлой генерацией — в заголовке кейса
появляется пометка `<!-- обновить -->`, сам текст правит человек.

### Синхронизация с Test IT

`tools/test_cases/testit_sync.py` читает `docs/test_cases/*.md` и для каждой области готовит
секцию проекта Test IT, а для каждого кейса — work item типа «Test case» (шаги, приоритет,
теги область/api-ui/роли и тег с путём автотеста). Поиск перед созданием — по названию и тегу
автотеста (а если в кейсе уже записан `- Test IT: <id>` — по нему), поэтому повторный запуск
обновляет существующие work items, а не плодит дубли.

Посмотреть план без единого сетевого вызова:

```
python tools/test_cases/testit_sync.py --dry-run [--area <name> ...]
```

Печатает по каждой области, сколько кейсов создать/обновить, и пишет
`workspace/testit_export.json` с телами запросов (без токена — он никогда не попадает ни в
payload, ни в печать) — по этому файлу владелец сверяет, что реально уйдёт в Test IT.

Реальная заливка:

```
python tools/test_cases/testit_sync.py --apply [--area <name> ...]
```

**`--apply` выполняет только владелец проекта, и только после того как проверил
`workspace/testit_export.json` от `--dry-run`.** После заливки id созданного/обновлённого work
item дописывается обратно в md-кейс (`- Test IT: <id>`) — по этой ссылке `conftest.py`
(`_load_testit_id_map` / `pytest_runtest_setup`) сам проставляет allure-label `testit_id`
привязанным тестам, без установки дополнительных пакетов.

Доступ к Test IT — только через `.env` (см. `.env.example`): `TESTIT_URL`, `TESTIT_TOKEN`
(PrivateToken), `TESTIT_PROJECT_ID`. Без них `testit_sync.py` работает в сухом режиме и
печатает, каких переменных не хватает; значения в код, логи, README и коммиты не пишутся.

### Официальный testit-adapter-pytest (опционально)

Привязка `testit_id` в отчёт Allure через `conftest.py` работает без него. Если нужен
нативный отчёт Test IT (запуск тестов напрямую с публикацией результатов в Test IT, а не
только заливка кейсов), можно локально поставить `testit-adapter-pytest` и запускать pytest с
его опциями — по умолчанию пакет в `requirements.txt` не добавлен, чтобы не тянуть
зависимость всем, кому нужна только заливка кейсов.

### Процесс для новых фич

Порядок для нового функционала: сначала тест-кейс в `docs/test_cases/<area>.md` (вручную или
черновиком через `generate.py` с последующей правкой), ревью и правка формулировок владельцем,
и только потом автотест — со ссылкой на TC-id в `@allure.title` или через allure-label
(например, `allure.dynamic.label("tc_id", "TC-NOTIFICATIONS-001")`), чтобы кейс и автотест
оставались связаны в обе стороны.
