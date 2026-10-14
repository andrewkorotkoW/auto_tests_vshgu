# Миссия: автотесты раздела LRS (черновик, 14.10.2026)

Источник требований — описание функционала LRS от владельца (передано в чате 14.10.2026,
в репозитории не хранится: взаимодействие LRS↔LMS, переходы по кнопкам и ID-ссылкам,
`LmsClient`, генерация отчёта и API `external/lrs/report`). Правила — как в
`docs/plans/2026-10-05_helpdesk_cases_mission.md`: сначала разведка и кейсы, потом
автотесты по образцу существующих областей; **прогоны только на develop**.

## Что уже известно (разведка 14.10, develop)

- **LRS — отдельное приложение OpenLRS** (Laravel Backpack, тема tabler):
  `https://lrs-develop.d2.devspark.ru/` → редирект на `/lrs-admin` → форма входа
  `/lrs-admin/login` (`Войти :: OpenLRS`), есть `/lrs-admin/password/reset`.
  **Сессия LMS в LRS не действует** — кука `.d2.devspark.ru` админа портала даёт ту же
  форму входа, что и без куки. Нужны отдельные учётные данные LRS (см. «Нужно от владельца»).
- **Вход из LMS — SSO через OAuth2 (Laravel Passport), отдельная учётка OpenLRS не нужна.**
  Кнопка «Перейти в LRS» в админке («Логи», справа над таблицей) есть **только на k8s**
  (релизная сборка; на develop её нет — вкладки «Авторизация/Изменения/Согласие на ПДн/
  Дисциплины» и всё). Механика: `GET https://lrs-<стенд>/oauth2/auth/callback` без кода →
  302 на LMS `GET /api/v1/oauth/authorize?client_id=9cc31531-…&scope=user-info user-role&
  response_type=code&approval_prompt=auto&redirect_uri=…/oauth2/auth/callback` → LMS под
  web-сессией отдаёт code → OpenLRS логинит пользователя LMS (на k8s админ-3 вошёл как
  «Зоя Агафонова / Главная»; меню: Хранилища, Пользователи, Перейти в LMS, хранилище
  `default store`). `lrs_uri` в `GET /auth/me` = этот callback.
  **На develop SSO сломан на бэкенде:** LMS отвечает `401 {"error":"invalid_client",
  "error_description":"Client authentication failed"}` — OAuth-клиент `9cc31531-…`, прописанный
  в lrs-develop, не зарегистрирован в Passport портала develop (проверено и requests-сессией,
  и настоящим браузером после входа через форму). Это задача девопсу/разработке.
  Форма `/lrs-admin/login` под учёткой LMS не пускает ни на develop, ни на k8s (OpenLRS хранит
  своих пользователей отдельно) — но при рабочем SSO она не нужна.
  Обратно: в боковом меню LRS кнопка «Перейти в LMS» — ссылка на главную LMS без авторизации.
- **Маршруты LMS для LRS** (`qa_analysis/cases/VSHGU2-2354_routes/routes.tsv`):
  - `POST /api/v1/external/lrs/users` (`lrs.users.index`) — пользователи по AccountName;
  - `GET /api/v1/external/lrs/contents/by_iri`, `POST /api/v1/external/lrs/contents/by_id` — активити по IRI/ID;
  - `POST /api/v1/external/lrs/report` (`lrs.report.edit`) — создание/статус/файл отчёта
    (`status=pending|in_progress|completed|error`, `export_id`, `file`), тип отчёта в LMS — `type: 14`;
  - `GET /api/v1/exports` — список «Отчётов» LMS (пагинация, поля `id,name,type,status,created_at,download_url,tenant`),
    `DELETE /api/v1/exports/mass-delete` — очистка. На develop сейчас отчётов `type 14` нет
    (есть 16/13/24/30) — генерация из LRS на develop давно не запускалась или записи удалены.
- **Авторизация external-маршрутов:** наш `EXTERNAL_SYSTEM_CLIENT_TOKEN` (используется CAS/игровой
  сессией) на `POST /external/lrs/report` даёт `403 Unauthorized` (как и без токена) — у LRS
  свой `oauth.jwt.token` + параметр `token={vshgu.jwt.token}`. Для API-части нужен этот токен
  или подтверждение, что external-токен должен подходить (тогда это дефект прав).
- **Sentry:** проект `vshgu-dev-lrs` (env `development`) — за 14 дней только инфраструктурные
  ошибки (postgres/redis «host not found», ~800 событий, последние 13.10 18:51 UTC) — LRS на
  develop периодически теряет базу/редис, это надо учитывать в ожиданиях тестов.
- **Исходники statements — подтверждено на k8s** (разведка `docs/lrs/lrs_recon.md`): в
  `default store` лежат statements от наших же тестов (Agent = id пользователей прогона #67,
  verb `answered`/`passed` — плеер конструктора тестов), states — от tincan-курсов Courseditor.
  Плееры шлют xAPI на `https://lrs-<стенд>/xAPI` с Basic-авторизацией клиента хранилища
  («Клиенты хранилища»: логин/пароль видны в UI). Структура OpenLRS, URL-ы разделов, фильтры,
  DataTables `POST …/statement/search`, маршрут отчёта `…/statement/report_generation` — в
  recon-документе.

## Нужно до старта

1. **Девопс/разработка: починить SSO LRS↔LMS на develop** — зарегистрировать OAuth-клиент
   OpenLRS (`client_id 9cc31531-bfd4-4b4a-b1b0-9869ccbaf489`, redirect `https://lrs-develop.d2.devspark.ru/oauth2/auth/callback`)
   в Passport портала develop; сейчас `invalid_client`. Плюс выкатить на develop кнопку
   «Перейти в LRS» в «Логах» (есть только на k8s). Пока этого нет, UI-часть LRS гоняется
   только на k8s (а прогоны на k8s — по согласованию с владельцем).
2. Для API-части (`external/lrs/*`) — `client_id`/`client_secret` OAuth-клиента LRS для
   `POST /api/v1/oauth/token` (grant `client_credentials`) → `.env` `DEVELOP_LRS_CLIENT_ID/SECRET`;
   наш HS256 `EXTERNAL_SYSTEM_CLIENT_TOKEN` (`sub: external_system-client`) там даёт 403 —
   другой тип токена. Альтернатива — проверять отчёты только через UI LRS → `GET /exports`.
3. Тестовое хранилище в LRS (на k8s видно одно — `default store`): можно ли создавать своё
   через «Хранилища», или писать в `default store`.
4. Подтверждение scope: только админские сценарии LRS (слушатель с LRS не взаимодействует).

## Части миссии

### Часть 0 — разведка (сделана 14.10, `docs/lrs/lrs_recon.md`) + кейсы
Осталось: нажать «Генерация отчета» один раз руками/скриптом и зафиксировать, что уходит в LMS
(`POST …/statement/report_generation` → `/exports` type 14, статусы, время джобы, содержимое
xlsx), и написать кейсы `docs/test_cases/lrs/*.md` по образцу helpdesk.

### Часть 1 — API LMS для LRS (`tests/api/lrs/`)
- `POST /external/lrs/report`: цикл `pending → in_progress → completed` с файлом: запись
  появляется в `GET /exports` с `type 14`, `status` меняется, `download_url` заполняется,
  файл скачивается; `status=error`; негативы — без токена 403, неизвестный `export_id`,
  неверный статус (422). Очистка — `DELETE /exports/mass-delete`.
- `POST /external/lrs/users` по `account_name` созданного `created_user`; `GET/POST
  /external/lrs/contents/by_iri|by_id` по созданному tincan-контенту.
- Эндпоинт-класс `api/endpoints/external_lrs.py` по образцу `external_cas.py`, фикстура
  `external_lrs_client` по образцу `external_system_client` (свой токен).

### Часть 2 — UI OpenLRS (`tests/ui/lrs/`, page objects `ui/pages/lrs_*.py`)
- Логин в OpenLRS (форма `/lrs-admin/login`), выбор хранилища, вкладки Statements/Agents:
  таблицы открываются, фильтры (ID пользователя, ID активити, действие, интервал) применяются;
- ссылка из колонки Agent / `account_name` ведёт в карточку пользователя админки LMS
  (открывается, это тот же пользователь);
- «Перейти в LMS» → главная LMS; из LMS «Логи → Перейти в LRS» → OpenLRS;
- «Генерация отчета» → в LMS «Отчёты» появляется отчёт `lrs_statement_export_*`, статус
  доходит до `completed`, файл скачивается (xlsx в zip), содержимое — statements по фильтру.
  Очистка отчётов — через `/exports/mass-delete`.

### Часть 3 — сквозной сценарий (e2e, маркер `e2e`)
Слушатель проходит tincan-курс (есть `test_user_tincan_flow`) → в LRS в Statements появляется
запись с его `account_name` и IRI активити → отчёт по фильтру этого пользователя содержит
строку. Делать только если в части 0 подтвердилось, что develop шлёт statements.

### Часть 4 — тест-кейсы и импорт
Кейсы в `docs/test_cases/lrs/` (md по шаблону helpdesk), пометки «- Автотест:», импорт в
test_hub (проект VSHGU, раздел `lrs`), README: раздел LRS (учётки, токен, хранилище).

## Ограничения

- Только develop; k8s/stage не трогать. LRS на develop периодически теряет postgres/redis
  (Sentry) — ожидания с ретраями, падения классифицировать как стенд.
- `.env.example` — новые переменные с пустыми значениями; секреты только в `.env`.
- Не удалять чужие statements/отчёты: очистка только того, что создал тест (по имени
  `lrs_statement_export_*` с нашим `export_id` / тестовому пользователю).
