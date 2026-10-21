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
  `conftest.py`). Пример использования — `@pytest.mark.env("stage")` в `tests/stage_lpd/`.

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
  api/        — API-тесты по сущностям портала (cas/, programs/, users/, certificates/, ...)
  ui/         — UI-тесты (Playwright) по тем же сущностям
  e2e/        — сквозные сценарии НЕСКОЛЬКИХ систем (сейчас lrs/ — LRS+LMS), маркер `e2e`,
                стенд не привязан к папке (develop/k8s, см. раздел про `--env`)
  stage_lpd/  — бывший tests/stage: сценарии ЛПД/БУК (api/ и ui/ подпапки, conftest.py с
                фикстурами individual_lpd/program_lpd), помеченные @pytest.mark.env("stage") —
                привязка к стенду stage идёт по маркеру, а не по названию папки
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
  test_hub_plugin.py — плагин раннера test_hub, разметка [TH] и кадры UI-шагов (раздел 16)
```

`tests/stage_lpd` — это переименованный бывший `tests/stage`: набор тот же (ЛПД/БУК), но
привязка к окружению идёт через маркер `@pytest.mark.env("stage")`, а не через физическое
расположение папки. `tests/e2e` — отдельный набор сквозных сценариев нескольких систем
(маркер `e2e`), к конкретному стенду папкой не привязан.

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
python test_data_generation/generate.py --env <develop|stage|k8s|stand> --scenario <имя> \
    [--count N] [--tenant ID] [--prefix STR] [--dry-run] [--list] [--cleanup manifest.json] \
    [--json] [--manifest-out PATH]
```

- `--env` — `develop` (по умолчанию), `stage`, либо произвольный стенд `k8s`/`stand`
  (хост из `STAND_URL`, см. раздел 4) — так CLI зовёт test_hub для выбранного стенда.
- `--scenario` — имя сценария (см. таблицу ниже), обязателен, если не указаны `--list`/`--cleanup`.
- `--count` — сколько сущностей на единицу плана (смысл зависит от сценария, по умолчанию 1;
  `--list` печатает подсказку «--count: …» под каждым сценарием).
- `--tenant` — `tenant_organization_id`, если нужен конкретный тенант.
- `--prefix` — суффикс имён создаваемых сущностей: `Автотест_<prefix>_<ts>`.
- `--dry-run` — без единого сетевого вызова: план шагов и синтетические id в лог, манифест не
  сохраняется (удалять нечего).
- `--list` — вывести список сценариев с описанием и выйти.
- `--cleanup manifest.json` — не создавать, а удалить сущности из ранее сохранённого манифеста.
- `--json` — машинный режим для test_hub (вкладка «Данные» проекта): `--list` печатает JSON-список
  `[{name, description, count_help}]`; `--scenario`/`--cleanup` добавляют последней строкой stdout
  `__TH_DATAGEN_RESULT__ {json}` с манифестом (`ok`, `manifest`, `manifest_path`, при сбое —
  `partial: true` и `error`) или итогом удаления (`deleted`/`failed`/`skipped`, `results`), а сбой
  сценария не бросает исключение наружу — код возврата `1`.
- `--manifest-out PATH` — сохранить манифест по заданному пути (и частичный при сбое) вместо
  `test_data_generation/manifests/<env>_<scenario>_<ts>.json`.

### Сценарии

| Сценарий | Что делает |
| --- | --- |
| `cas` | программа CAS -> поток -> синхронизация -> модуль -> N пользователей на каждый статус зачисления |
| `users` | N пользователей на каждую роль (слушатель/преподаватель/проверяющий/менеджер/контент-менеджер/админ тенанта) |
| `program_full` | программа -> поток -> модуль -> элемент расписания -> N слушателей -> сертификатный шаблон программы |
| `activities` | программа -> поток -> модуль -> по одной активности каждого типа (tincan/scorm/внешний контент/ДЗ 5-10-зачёт/тест/опрос/АОС/LPD на stage/материал БЗ + достижение) |
| `learner_progress` | слушатель -> назначение на программу с ДЗ в модуле -> отправка ответа (только через UI — нет API) |
| `individual_track` | N слушателей + по одной активности каждого назначаемого типа (Tincan/SCORM/ДЗ 5-10-зачёт/тест/опрос/LPD на stage), все назначены каждому на индивидуальный трек; игровой сессии нет — её на инд. трек назначить нельзя; внешнего контента тоже нет (после назначения его DELETE отдаёт 500 на develop — см. докстринг сценария) |
| `buk` | N пользователей -> входящий REST БУК (`POST /external/buk/users`) с ожиданием сопоставления по email |
| `certificates` | шаблон сертификата для потока программы (program_stream) и для активности (activity) + назначение |
| `banner_and_partners` | включение инфо-баннера + выдача доступа Alpina/MIF N пользователям |
| `demo` | демо-наполнение стенда: `users` + `program_full` + `activities` + `certificates` + `banner_and_partners` (count=1 на каждый шаг) |
| `tests` | N тестов (по два вопроса single, порог 60 %), без программы |
| `polls` | N опросов (один вопрос), без программы |
| `aos` | программа -> поток -> модуль -> N элементов расписания, на каждом анкета обратной связи (АОС) с вопросом, активированная в потоке |
| `courses` | N курсов Tincan (архив `test_data/course_tincan.zip`) + материал БЗ «курс» на каждый, без программы |
| `scorm` | N курсов SCORM 2004 (архив `test_data/test_lms_scorm_2004.zip`), без программы |
| `materials` | N материалов БЗ каждого типа: статья / книга / файл / аудио / видео (файлы из `test_data/`) |
| `achievements` | N достижений с условием «изучено N материалов-статей», активные, стандартная иконка |
| `homework` | N практических заданий каждого типа оценки (5-балльное / 10-балльное / зачёт-незачёт), без программы |
| `lpd` | N активностей LPD, без программы — только на stage (на остальных окружениях шаг `skipped`) |

Сценарии сгруппированы по категориям (`CATEGORIES` в `generate.py`: «Пользователи и
программы», «Активности», «База знаний», «Сертификаты», «Интеграции», «Наборы»), у каждого есть
короткое человеческое название — `--list` печатает их по группам, `--list --json` отдаёт поля
`category`/`title`, а test_hub показывает селект с `optgroup` по этим категориям.

Сценарии `tests` … `lpd` — «точечные»: одна сущность нужного вида без цепочки
программа → поток → модуль, для ручных проверок и наполнения стенда через test_hub.
Достижение в `activities` с 21.10.2026 создаётся по-настоящему (`KnowledgeBaseEndpoint.
create_achievement`), а не помечается «только через UI».

`buk` и активность LPD внутри `activities`/`lpd` реально доступны только на stage (см. раздел 8) —
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
- **`GET /tickets/{id}/messages` отдаёт сообщения по убыванию `created_at` — новое первым.**
  Контракт подтверждён владельцем 13.10.2026 (до 09.10 API отдавал по возрастанию, и
  `test_add_message_and_order` закреплял старый порядок — изменение намеренное, тест перевёрнут).
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
  перезагрузкой страницы — воспроизводилось ad-hoc скриптом вне pytest и тестом
  `test_admin_sees_created_notification_in_table`. **Закрыто 13.10.2026:** тест проходит на
  develop (ночной прогон) и на k8s (3 из 3 с `--runxfail`), пометка `xfail` снята.
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
теги область/api-ui/роли и тег с путём автотеста, либо `manual` для кейсов без автотеста).
Поиск перед созданием — по названию и тегу `autotest:<node id>` (для ручных кейсов — по
`tc:<TC-ID>`), а если в кейсе уже записан `- Test IT: <id>` — по нему; поэтому повторный запуск
обновляет существующие work items, а не плодит дубли. Строка кейса `- Требование: …` (если
есть) уходит первым шагом в `preconditionSteps`, перед обычными предусловиями.

Подпапки `docs/test_cases/mts_link/` и `docs/test_cases/p2p/` — области отдельных крупных
интеграций (в т.ч. кейсы без автотеста — ручные сценарии, которые не покрыты автотестами:
например `docs/test_cases/mts_link/14_dev_real_e2e.md`). Их заливают отдельным прогоном с
`--docs-dir`, указывающим на подпапку, и `--parent-section`, чтобы секции всех областей этой
подпапки легли вложенными в одну родительскую секцию, а не плоско в корень проекта Test IT:

```
python tools/test_cases/testit_sync.py --dry-run --docs-dir docs/test_cases/mts_link --parent-section "МТС Линк"
python tools/test_cases/testit_sync.py --dry-run --docs-dir docs/test_cases/p2p --parent-section "P2P"
```

Родительская секция ищется по имени среди секций проекта с `parentId=None` (и создаётся при
отсутствии); секция каждой области ищется/создаётся с `parentId` родителя, поэтому одинаковые
имена секций в разных подпапках не склеиваются. Если заголовок области в md отсутствует (title
совпал бы с именем файла вида `00_tenant_settings`), имя секции делается читаемым с сохранением
порядка файлов — `00. Tenant settings`.

Посмотреть план без единого сетевого вызова:

```
python tools/test_cases/testit_sync.py --dry-run [--area <name> ...] [--parent-section <name>]
```

Печатает по каждой области, сколько кейсов создать/обновить/из них ручных, и пишет
`workspace/testit_export.json` с телами запросов (без токена — он никогда не попадает ни в
payload, ни в печать) — по этому файлу владелец сверяет, что реально уйдёт в Test IT.

Реальная заливка:

```
python tools/test_cases/testit_sync.py --apply [--area <name> ...] [--parent-section <name>]
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

## 16. Плагин test_hub

`utils/test_hub_plugin.py` — pytest-плагин для внешнего раннера test_hub: печатает в stdout
разметку по каждому тесту и шагу и снимает скриншоты UI-шагов, чтобы раннер мог сопоставить
прогон pytest со своей моделью теста/шагов и показать кадры в интерфейсе.

Подключён в корневом `conftest.py` через `pytest_plugins = ["utils.test_hub_plugin"]`, но
активен только когда заданы все три переменные окружения `TH_URL`, `TH_RUN_ID`, `TH_RUN_TOKEN`
(их выставляет раннер test_hub перед стартом pytest). Без них модуль не делает вообще ничего —
ни print, ни сетевых вызовов, ни патча `allure.step` — обычные локальные и стендовые прогоны
через `pytest --env=...`/`scripts/run.sh` (раздел 3) не меняются.

Разметка идёт в stdout построчно (`flush=True`, чтобы раннер видел её в потоке, а не по
завершении процесса):

- `[TH] start <nodeid>` — начало теста (`pytest_runtest_logstart`);
- `[TH] step <nodeid> <n> <имя>` — вход в очередной `allure.step` (плагин подменяет
  `allure.step` на прозрачную обёртку на время сессии), `<n>` — порядковый номер шага в
  тесте начиная с 1;
- `[TH] end <nodeid> <passed|failed|skipped|xfailed>` — итог теста, определяется по фазам
  setup/call/teardown отчёта pytest (`pytest_runtest_logreport`), печатается один раз.

Кадры UI-шагов снимаются, если в фикстурах теста (`item.funcargs`) есть активная страница
Playwright под одним из имён `page`, `admin_page`, `user_page` — это покрывает основные
UI-роли проекта. На каждом `[TH] step` со страницы снимается `page.screenshot()` (PNG,
ширина кадра не больше 1280 px — при более широком viewport берётся `clip` по ширине), кадр
одновременно прикладывается к allure-отчёту как вложение `step <n>` и отправляется
`POST {TH_URL}/api/runs/{TH_RUN_ID}/frames` (multipart: `nodeid`, `step`, `file`,
заголовок `Authorization: Bearer {TH_RUN_TOKEN}`). Лимит — 40 кадров на тест, дальнейшие шаги
разметку `[TH] step` печатают по-прежнему, но кадры пропускаются. Отправка кадра сделана с
таймаутом 3 секунды и не роняет тест ни при недоступности `TH_URL`, ни при любой другой сетевой
ошибке — сбой только пишется в лог (`utils/logger.py`).

Для API-тестов страницы Playwright нет, поэтому кадров тоже нет — разметка ограничивается
`[TH] start`/`[TH] step`/`[TH] end`, а сами запросы по-прежнему видны в логе `api/client.py`
(`POST ...`, `Response [...]`) как и без плагина; раннер сопоставляет их с тестом по nodeid
между `[TH] start` и `[TH] end`.

### Живая трансляция (screencast)

Выключена по умолчанию — раннер test_hub включает её переменной `TH_LIVE` (любое значение,
кроме `0`/`false`/`no`, в т.ч. сам факт `TH_LIVE=1`; при отсутствии переменной трансляции нет).
Работает только поверх уже активного плагина, т.е. требует и `TH_URL`/`TH_RUN_ID`/`TH_RUN_TOKEN`,
и `TH_LIVE` одновременно. Как только у теста появляется активная страница Playwright
(`page`/`admin_page`/`user_page`), на ней открывается CDP-сессия (`Page.startScreencast`, JPEG,
quality 50, максимум 960×600 px) — кадры копятся в фоновом потоке и отправляются не чаще
`TH_LIVE_FPS` раз в секунду (по умолчанию 3) через
`POST {TH_URL}/api/runs/{TH_RUN_ID}/live` (multipart: `nodeid`, `ts`, `step` — имя текущего шага,
`file` — jpeg), с таймаутом 2 секунды. Если активная страница в тесте сменилась (новый контекст
для гостя/попапа), сессия переоткрывается на новой странице. Как и кадры шагов, трансляция не
роняет тест при сетевых ошибках; но после 20 ошибок подряд она отключается до конца теста (с
записью в лог), чтобы не крутить фоновый поток впустую. Для API-тестов (нет страницы Playwright)
трансляции нет вне зависимости от `TH_LIVE`.

### Видео теста

Запись видео (`record_video_dir`/`record_video_size` в фикстурах `page`/`admin_page`/`user_page`
в `conftest.py`, разрешение 1280×720) включается при активном плагине (`TH_URL`/`TH_RUN_ID`/
`TH_RUN_TOKEN`) **или** отдельно переменной `TH_VIDEO=1` — последнее позволяет записать видео
локально при обычном прогоне, без полноценного раннера test_hub. Файлы пишутся в
`workspace/video/<TH_RUN_ID или "local">/` (каталог в `.gitignore`). Если в тесте несколько
контекстов (`page`+`user_page`), на test_hub отправляется только основной контекст (первый из
`page`/`admin_page`/`user_page`, который использует тест), видео остальных просто удаляется.

После `context.close()` готовое видео отправляется в фоновом потоке на
`POST {TH_URL}/api/runs/{TH_RUN_ID}/tests/{nodeid}/video` (multipart: `duration_ms`, `file` —
webm), таймаут 10 секунд; файл удаляется с диска только при успешной отправке, при ошибке
остаётся на диске и пишется в лог. Отправка на test_hub требует полного набора `TH_URL`/
`TH_RUN_ID`/`TH_RUN_TOKEN` — при одном только `TH_VIDEO=1` видео записывается и остаётся
локально, никуда не отправляется. Дополнительно видео прикладывается к allure-отчёту
(`attachment_type.WEBM`) **только для упавших тестов**, чтобы не раздувать отчёт по зелёным
прогонам.

Юнит-тесты плагина (разметка, кадры шагов, троттлинг и отключение трансляции, отправка видео) —
без стенда и без сети наружу (все HTTP-вызовы в тестах идут на локальный мок-сервер):

```bash
pytest tests/tools -m tools -q
```

Отдельно есть локальный UI-тест трансляции и видео (`tests/tools/test_test_hub_plugin_live_ui.py`)
на мок-странице `file://` (`tests/tools/fixtures/live_timer.html`) с локальным мок-сервером —
тоже без стенда и без сети наружу, входит в ту же команду.

Реальные прогоны через раннер test_hub (сам сервис test_hub, его хранение прогонов/кадров/
трансляции/видео, UI на стороне раннера) в этом README не описываются — это зона
ответственности владельца раннера; здесь зафиксирован только контракт со стороны автотестов
(env-переменные `TH_URL`/`TH_RUN_ID`/`TH_RUN_TOKEN`/`TH_LIVE`/`TH_LIVE_FPS`/`TH_VIDEO`, формат
`[TH]`-строк, формат запросов кадра/трансляции/видео).

## 17. Интеграция МТС Линк (в ожидании ветки)

Миссия `docs/missions/2026-09-30_tz2026_mts_link.md`: подготовка тест-кейсов, плана тестирования
и каркаса автотестов для ещё не реализованной интеграции с МТС Линк (вебинары вместо очных
мероприятий). **Функционала и тестового стенда нет** — ничего из описанного ниже не запускалось
против develop/stage/prod, кроме read-only разведки существующих экранов (обычные мероприятия,
таблица слушателей, `request_log_audit`), нужной для проектирования кейсов и клиента.

- План тестирования: `docs/plans/2026-09-30_tz2026_mts_link_test_plan.md` (объект и границы,
  стратегия по уровням, матрица трассировки, открытые вопросы, критерии готовности/приёмки).
- Тест-кейсы: `docs/test_cases/mts_link/` (16 файлов, части 0–15 по ТЗ) — всего **96 кейсов**
  (TC-MTS-001–096), из них **83 с автотестом** (`- Автотест: <nodeid>` в тексте кейса) и 13
  принципиально ручных (часть 13, `14_dev_real_e2e.md` — сквозной цикл на dev с реальным
  аккаунтом МТС Линк).

Каркас автотестов (`tests/api/mts_link/`, `tests/ui/mts_link/`, клиент
`api/endpoints/mts_link.py`, page objects `ui/pages/`) лежит в репозитории заранее и собирается
(`pytest --collect-only`, 83 теста), но пропускает себя целиком, пока в `.env` не выставлен флаг
`MTS_LINK_READY` (см. `.env.example`, `config/environments.py::is_feature_ready`) — без флага
прогон даёт 83 skipped, 0 failed/error. Когда ветка с реализацией появится: поднять моки клиента
и сиды части 12, ответить на блокирующие вопросы плана (раздел 4), включить `MTS_LINK_READY=1`
(и `MTS_LINK_TENANT_ID`) на тестовом стенде — тесты начнут выполняться реальными шагами без
изменения кода каркаса.

## 18. Helpdesk: что покрыто, как запускать

Миссия `docs/plans/2026-10-05_helpdesk_cases_mission.md`, итоговый отчёт —
`docs/reports/2026-10-05_helpdesk_mission.md`. Хелпдеск — отдельная admin-панель (разведка:
`docs/helpdesk_recon.md`), сервер-рендерящаяся Laravel Backpack-админка на
`https://helpdesk-develop.d2.devspark.ru` (общая сессия с develop), без JSON REST API — список
`GET /admin/<entity>`, подгрузка строк `POST /admin/<entity>/search` (DataTables), CRUD через
create/{id}/edit/{id}/show + `POST`/`PUT`/`DELETE`. Пользовательская часть тикетов
(`/api/v1/tickets/*`) сюда не входит — она покрыта отдельно, см. `docs/test_cases/tickets.md`,
`tests/api/tickets`, `tests/ui/tickets/user`.

**51 автотест реализован** (44 из 48 кейсов в `docs/test_cases/helpdesk/{tickets,groups,users,
applicants,templates,dashboards}.md` — у каждого в md строка `- Автотест: <nodeid>`; оставшиеся 4
кейса про зачисление активити заявителя и фильтры дашборда помечены `- Статус: ждёт подтверждения
владельца функционала`, не автоматизируются), синхронизированы в Test IT «ВШГУ v.3» (раздел
Helpdesk, id в md) и импортированы в test_hub (проект `VSHGU`, разделы `helpdesk/*`). API-тесты —
`tests/api/helpdesk/` (29 тестов: группы/шаблоны/заявители/пользователи/тикеты/справочники, CRUD +
негативные), UI — `tests/ui/helpdesk/admin/` (22 теста: навигация по разделам меню, CRUD
справочников, создание/удаление группы и шаблона, назначение роли, карточка пользователя и
заявителя, настройка колонок таблицы тикетов, переход в карточку обучения заявителя). Используют
`HelpdeskEndpoint` (`api/endpoints/helpdesk.py` — CSRF/DataTables-механика Backpack CRUD),
генераторы данных (`generate_helpdesk_*_payload` в `api/helpers/data_generator.py`), page-объекты
`ui/pages/helpdesk_*.py`.

Запуск (нужен `HEADLESS=1` для UI-части, других стендов для хелпдеска нет — только `--env develop`;
API и UI стоит запускать отдельными командами — совместный прогон укладывается в несколько минут,
но может превысить таймаут одной foreground-команды):

```
HEADLESS=1 pytest tests/api/helpdesk --env develop -q
HEADLESS=1 pytest tests/ui/helpdesk --env develop -q
```

Фактический итог прогона (06.10.2026, после фикса инфраструктуры и автоматизации всех 10 оставшихся
ручных кейсов из плана): **39 passed, 12 xfailed, 0 xpassed, 0 failed** (29 API: 19 passed/10 xfailed;
22 UI: 20 passed/2 xfailed) — часть тестов помечена `xfail(strict=False)` из-за дефектов стенда, не
кода автотестов (полный список nodeid и причин — `docs/reports/2026-10-05_helpdesk_mission.md`,
раздел 3), в т.ч.:

- `POST /admin/user/search` стабильно отдаёт `500` на любой запрос без совпадения с сид-данными
  (не только на многословное ФИО, как предполагала разведка) — блокирует поиск/назначение роли
  новому пользователю и в API, и в UI;
- `GroupCrudController::store()`/`update()` при успешном создании/обновлении группы с
  `Accept: application/json` возвращает `JsonResponse` вместо `RedirectResponse` — Laravel бросает
  `TypeError` (500), хотя группа реально создаётся/обновляется в БД; блокирует весь API CRUD групп;
- `assign-role` на несуществующего пользователя отвечает `500` (`TypeError` в
  `RolesRepository::hasOneOfRoles()`), а не `404`;
- создание записи «Чёрного списка адресов» падает на сервере `500` при валидации уникальности email.

CSRF-регэксп `HelpdeskEndpoint._csrf_token` и несвязанные `<label>`/`<input>` в формах групп и
шаблонов, из-за которых раньше падали эти и другие тесты, исправлены в рамках этой миссии
(`ui/pages/helpdesk_*.py`, `api/endpoints/helpdesk.py`) — подробности и список исправленных nodeid в
отчёте, раздел 3.

## 19. Мобильная вёрстка

Миссия `docs/plans/2026-10-06_mobile_android_mission.md` (часть 1), отчёт —
`docs/reports/2026-10-06_mobile_mission.md`. Приложение «ДПО ПА» — WebView-оболочка вокруг
`portal.gosedu.ru`, поэтому автотесты мобильной вёрстки — это обычный Playwright с профилем
контекста Pixel 7, без Appium/эмулятора (решение и разбор apk — в плане, «Факты про приложение»).

`docs/mobile/layout_facts.md` — снятые на develop расхождения мобильной вёрстки с desktop по шести
экранам: 1. вход (`/auth/main`), 2. список программ (`/education`), 3. активити — тест/опрос
(`/testing/player`), 4. карточка программы (сертификат по этому сценарию отдельно не проверен —
блокер не мобильный, см. п. 4 файла), 5. профиль, 6. уведомления (`/portal-notifications`). Каждый
пункт — это кандидат в xfail/дефект мобильной вёрстки; прежде чем автоматизировать новый мобильный
экран, стоит проверить, не описаны ли там уже его особенности (например, у «Профиля» нет
отдельного URL и клик по вкладке работает только со страницы списка программ).

```bash
MOBILE=1 HEADLESS=1 pytest -m mobile --env develop
pytest --mobile --env develop tests/ui/mobile/test_mobile_login_my_programs.py   # конкретный тест/файл
```

Опция `--mobile` и переменная окружения `MOBILE=1` равнозначны (см.
`conftest.py::_is_mobile_mode`) — второй путь нужен, чтобы включать режим из test_hub без передачи
CLI-опций. Мобильный профиль контекста — константа `MOBILE_DEVICE` в `conftest.py`:
`playwright.devices["Pixel 7"]` для версии playwright из `requirements.txt` (viewport 412×839,
`device_scale_factor` 2.625, `is_mobile`/`has_touch` True, мобильный `user_agent`), видео-запись —
под тот же размер. Без флага/переменной поведение `page`/`admin_page`/`user_page` не меняется ни на
байт (desktop viewport 1366×768, видео 1280×720).

Как добавить мобильный тест:

- Фикстуры данных — те же, что в desktop UI-тестах (`created_user`, `created_program`,
  `assignments_endpoint`, `assigned_user`, `prepare_user_for_tests_via_api` и т.п.) — мобильный
  профиль касается только контекста браузера, не подготовки данных через API.
- Фикстура `is_mobile` — True, если прогон идёт с `--mobile`/`MOBILE=1`; использовать для мобильных
  веток в page objects вместо копирования page objects целиком (`if page.viewport_size["width"] <
  768` работает только внутри теста, где страница уже открыта — `is_mobile` доступна и раньше).
- Маркер `pytest.mark.mobile` — ставить только на тест, реально зелёный в прогоне с `--mobile` на
  develop (не «на выглядит адаптивным»); узел в `tests/product_map.yml` (зона `mobile`) обновлять
  вместе с тестом.
- Если экран в мобильной вёрстке в принципе не проходит (нет элемента/зависает) — `xfail` с причиной
  и запись в `docs/mobile/layout_facts.md`, это кандидат в дефект, а не повод пропускать тест молча.
- Своему conftest.py, которому нужна `_context_kwargs` из корневого `conftest.py`, использовать
  фикстуру `build_context_kwargs`, а не `import conftest` — у одноимённых `conftest.py` без
  `__init__.py` в директориях голый `import conftest` резолвится в себя же (self-import) под
  pytest `import-mode=prepend`, см. `tests/ui/dictionaries/conftest.py::second_user_page`.

Набор `tests/ui/mobile/` (5 тестов, все шесть экранов из `layout_facts.md`):
`test_mobile_login_my_programs.py` (вход → «Моё обучение» показывает назначенную программу),
`test_mobile_activity_simple_test.py` (активити — прохождение простейшего теста из 3 вопросов),
`test_mobile_program_card.py` (карточка программы после прохождения активити),
`test_mobile_notifications.py` (`/portal-notifications`), `test_mobile_profile_and_certificates.py`
(вкладка «Профиль» нижней панели и подвкладка «Мои сертификаты») — все пять зелёные стабильно
(версия про «зависающий спиннер» на «Профиле» не подтвердилась 07.10, см. `layout_facts.md` п. 5). Каждый тест ставит
`allure.dynamic.parameter("device", "Pixel 7")` и прикладывает финальный скриншот в Allure — не только
при падении.

## 20. LRS

Миссия `docs/plans/2026-10-14_lrs_mission.md`, разведка — `docs/lrs/lrs_recon.md`, итоговый отчёт —
`docs/reports/2026-10-14_lrs_autotests.md`. LRS — отдельное приложение **OpenLRS** (Laravel Backpack,
тема tabler, тот же DataTables-стек, что у хелпдеска, см. п. 18): хранилище statements/states xAPI,
своя панель `/lrs-admin`.

**Отдельной учётки LRS в тестах нет.** OpenLRS не принимает учётки LMS собственной формой
(`/lrs-admin/login`) — штатный вход всегда SSO через OAuth2 (Laravel Passport): сессия LMS →
`GET <lrs>/oauth2/auth/callback` → LMS под веб-сессией выдаёт код → OpenLRS логинит того же
пользователя LMS. В коде — `LrsAdminPage.login_via_sso` (`ui/pages/lrs_admin_page.py`): логинится
в LMS обычной формой, затем идёт на callback.

Хост OpenLRS вычисляется функцией `lrs_base_url(env)` из `env.ui_base_url` заменой `portal-`/`portal.`
→ `lrs-`/`lrs.` — без доп. настройки. Переменная **`LRS_URL`** (`.env.example`) — опциональный явный
override этого хоста, приоритетнее вычисленного значения; нужна только если хост LRS стенда не
подчиняется схеме `portal-<стенд>` → `lrs-<стенд>`.

**На develop UI-тесты LRS сейчас не запускаются**: callback `GET <lrs>/oauth2/auth/callback` ловит
`401 {"error":"invalid_client"}` от LMS — OAuth-клиент OpenLRS (`client_id 9cc31531-…`) не
зарегистрирован в Passport портала develop (кнопки «Перейти в LRS» в «Логах» там тоже нет — см.
`docs/lrs/lrs_recon.md`, раздел «Вход»). Починка — на стороне девопс/разработки. Поэтому все тесты
LRS (`tests/ui/lrs/`, `tests/e2e/lrs/`, маркеры `lrs`/`e2e` в `pytest.ini`) помечены
`@pytest.mark.env("k8s")` (кроме двух, не зависящих от SSO — форма логина и чистый контекст без
сессии) и собираются/прогоняются на k8s, а не на develop.

Отчёты, которые создаёт тест «Генерация отчета» (кейс TC-LRS-011) в LMS «Отчёты»
(`lrs_statement_export_*.xlsx`, `type: 14`, API `api/endpoints/exports.py::ExportsEndpoint`),
подчищаются в teardown фикстурой `lrs_reports_cleanup` (`conftest.py`) через
`DELETE /exports/mass-delete` — удаляются только id, накопленные тестом, посторонние отчёты не
трогаются. **Statements и states, которые тесты видят или создают прохождением теста/курса
(TC-LRS-013), автотестами не удаляются** — это данные хранилища `default store`, общие для стенда.

Кейсы — `docs/test_cases/lrs.md` (15 штук, TC-LRS-001…015, у каждого `- Автотест: <nodeid>`),
page object — `ui/pages/lrs_admin_page.py` (SSO, хранилища, клиенты, Statements/Agents/States),
тесты — `tests/ui/lrs/{test_lrs_navigation,test_lrs_stores,test_lrs_statements,test_lrs_report}.py`
и `tests/e2e/lrs/test_statement_after_test_pass.py` (15 тестов, `pytest --collect-only` проходит
без ошибок).

## 21. e2e-набор слушателя

Миссия `docs/plans/2026-10-14_e2e_markers_mission.md`, отчёт —
`docs/reports/2026-10-14_e2e_markers.md`. Маркер `e2e` объединяет сквозные сценарии слушателя
(регистрация/онбординг, прохождение контента, оценка, статистика, техподдержка), не привязанные
к одной папке — в отличие от `tests/stage_lpd` (см. раздел 4), это тесты из разных подпапок
`tests/ui/*` и `tests/e2e/`, собираемые по маркеру `@pytest.mark.e2e`, а не по физическому
расположению.

**Что входит** (21 тест, подтверждено `pytest --collect-only -q -m e2e`):
- 19 тестов из `tests/ui/*` — вход/онбординг, курс и тест в потоке, практические задания
  (включая групповые и в рамках ПЗ-проверяющего), АОС (авторизованный и по публичной ссылке),
  игровая сессия, уведомления, четыре сценария индивидуального трека (курс, опрос, ПЗ, курс из
  БЗ, «домашнее задание»), техподдержка (создание тикета слушателем) и замыкание статистикой
  (статус «пройдено» в статистике обучения после прохождения курса);
- 2 теста LRS — `tests/ui/lrs/test_lrs_report.py::TestLrsReport::test_generate_report_appears_in_lms_exports`
  и `tests/e2e/lrs/test_statement_after_test_pass.py` (см. раздел 20).

Список сценариев с nodeid — таблица «Часть 2» плана миссии; кейсы — `docs/test_cases/e2e.md`
(TC-E2E-019…035, по одному на тест, шаги переписаны из `allure.step` самих тестов) и
`docs/test_cases/lrs.md` (TC-LRS-011/013 — для двух LRS-тестов, здесь не дублируются). Два теста
с маркером `e2e` — техподдержка и замыкание статистикой — в `docs/test_cases/e2e.md` пока без
отдельного TC-кейса (известный пробел, см. отчёт миссии).

**Как запускать**: `pytest -m e2e --env k8s -n 0` (develop сейчас недоступен для LRS-части, см.
раздел 20; остальные e2e-тесты на develop собираются, но вместе с LRS набор гоняют на k8s). В
test_hub прогон идёт по маркеру `e2e`, без привязки к конкретным файлам.

**Чем отличается от `tests/stage_lpd`**: `tests/stage_lpd` (бывший `tests/stage`) — это
ЛПД/БУК-сценарии на отдельном стенде stage, физически лежащие в своей папке и помеченные
`@pytest.mark.env("stage")`; набор `e2e` — сквозные сценарии слушателя на develop/k8s, живущие
внутри обычных `tests/ui/*`/`tests/e2e/` рядом с остальными тестами тех же разделов и
выделяемые только маркером.

**Чего в наборе ещё нет** (черновики кейсов TC-E2E-036…040 в `docs/test_cases/e2e.md`, ждут
разведки владельца на k8s): очное мероприятие в потоке, очное мероприятие в индивидуальном
треке, опрос в потоке + неавторизованная попытка прохождения по ссылке, сертификат слушателя
программы — для этих четырёх автотестов нет. Пятый, достижение слушателя за материал базы
знаний (TC-E2E-040), уже автоматизирован (`tests/ui/knowledge_base/user_achievements/
test_user_gets_achievement_by_material.py`), но без маркера `e2e` — владельцу нужно решить,
добавлять ли маркер на существующий тест вместо нового.
