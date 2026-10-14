# LRS (OpenLRS) — разведка 14.10.2026

Проверено на k8s (`lrs-k8s-release.v2.gosedu.ru`, релизная сборка; владелец разрешил
посмотреть) и develop (`lrs-develop.d2.devspark.ru`). Только чтение: отчёты не генерировались,
ничего не создавалось и не удалялось.

## Вход

- OpenLRS — отдельное Laravel Backpack-приложение (`/lrs-admin`, тема tabler, DataTables —
  тот же стек, что у хелпдеска). Своя форма `/lrs-admin/login` (email/password/remember);
  учётки LMS она **не принимает** ни на develop, ни на k8s (OpenLRS хранит пользователей у
  себя: раздел «Пользователи» — `admin1/3/5@org2.ru`, созданы SSO-входами).
- **Штатный вход — SSO через OAuth2 (Laravel Passport)**, OpenLRS = OAuth-клиент LMS:
  1. админка LMS → «Логи» → кнопка «Перейти в LRS» = `<a href="https://lrs-<стенд>/oauth2/auth/callback">`
     (на k8s есть, на develop кнопки нет);
  2. `GET /oauth2/auth/callback` без `code` → 302 на LMS
     `GET /api/v1/oauth/authorize?client_id=9cc31531-bfd4-4b4a-b1b0-9869ccbaf489&scope=user-info%20user-role&response_type=code&approval_prompt=auto&state=…&redirect_uri=https://lrs-<стенд>/oauth2/auth/callback`;
  3. LMS под web-сессией пользователя отдаёт `code` → callback → OpenLRS логинит LMS-пользователя
     (`Панель управления :: OpenLRS`, в шапке ФИО и тенант «Главная»).
  Для автотестов: `LoginPage.login` в LMS формой → `page.goto(<LRS>/oauth2/auth/callback)` →
  мы в `/lrs-admin`. Под requests-сессией (API-кука) LMS отвечает `401` — нужен браузер.
- **develop:** LMS отвечает `401 {"error":"invalid_client","error_description":"Client authentication failed"}` —
  OAuth-клиент `9cc31531-…` не зарегистрирован в Passport develop. До правки девопсом UI LRS на
  develop недоступен; `lrs_uri` в `GET /auth/me` = callback (есть на обоих стендах).
- «Перейти в LMS» в меню OpenLRS → `https://portal-<стенд>/admin/programs` (без авторизации — просто ссылка).
- Выход: `/lrs-admin/logout`; «Мой аккаунт»: `/lrs-admin/edit-account-info`.

## Структура OpenLRS (k8s, 14.10)

| Раздел | URL | Что есть |
|---|---|---|
| Хранилища | `/lrs-admin/store` | таблица: Название, Папка, Размер, Количество states, Количество statements; кнопка «Добавить Хранилище» (форма `/lrs-admin/store/create`: `name`, `folder`). На k8s одно — `default store` (папка `default`, 0.4 MB, 5 states, 515 statements) |
| Пользователи | `/lrs-admin/users` | E-mail, Имя, Действия (Редактировать `/users/{id}/edit`, Удалить); «Добавить Пользователь» |
| Хранилище → Клиенты | `/lrs-admin/store/1/client` | Логин, **Пароль открытым текстом**, Дата создания, Launch; «Добавить Клиент». Клиент = учётка xAPI-endpoint'а для плееров: Launch-ссылка содержит `endpoint=https://lrs-<стенд>/xAPI&auth=Basic <base64 login:pass>` |
| Хранилище → Statements | `/lrs-admin/store/1/statement` | колонки Agent (ссылка → `https://portal-<стенд>/admin/users/{id}`), Verb, Activity, Дата создания statement-а, Действия (Предпросмотр `/statement/{id}/show`). Кнопки **«Скачать»**, **«Генерация отчета»** (JS, маршрут `POST …/store/1/statement/report_generation`; архив — `/store/1/archive/download`). Фильтры: `date`, `filter_agentId` (select с поиском), `filter_verb` (13 verb'ов: exited, interacted, answered, initialized, failed, completed, viewed, launched…), `filter_lmsActivityId`, `daterangepicker-statementTimestamp`; «Сбросить». Список грузится DataTables `POST /lrs-admin/store/1/statement/search` |
| Хранилище → States | `/lrs-admin/store/1/state` | Agent (ссылка в LMS), State key (`globalState`), Activity IRI (`https://courseditor.ru/xapi/courses/lp_course_93519`), Registration; фильтры по agent/stateKey/activityIri/registration; Предпросмотр/Удалить |
| Хранилище → Activity profiles | `/lrs-admin/store/1/activity_profile` | Profile ID, Activity profile ID — на k8s пусто |
| Хранилище → Agents | `/lrs-admin/store/1/agent` | `account_name` (ссылка → карточка пользователя LMS), кнопки Statements (`/statement?agent_id=N`) и State (`/state?agent_id=N`) |
| Предпросмотр statement | `/lrs-admin/store/1/statement/{id}/show` | Agent, Verb, Activity, дата, Registration, Voided, Payload, полный JSON xAPI (`actor.account.name` = id пользователя LMS, `homePage` = `https://portal-<стенд>/accounts/userid`, `verb.id` = `http://adlnet.gov/expapi/verbs/answered`, `result`…) |

## Откуда берутся statements (важно для e2e)

На k8s все свежие statements — **от наших автотестов**: Agent 902/898/896/894 = пользователи
прогона #67 (13.10, 16:50–16:52), verb `answered`/`passed` — прохождение тестов в
конструкторе (плеер шлёт xAPI в `default store`). States — от tincan-курсов Courseditor
(`lp_course_93519`). Значит сквозной сценарий «слушатель прошёл тест/курс → statement в LRS с
его `account_name`» на k8s воспроизводим без подготовки.

## Отчёты

`GET /api/v1/exports` в LMS: на k8s типы 16/13/2, на develop 16/13/24/30 — отчётов LRS
(`type 14`, `lrs_statement_export_*`) нет ни на одном стенде, генерация из LRS никем не
запускалась. Кнопка «Генерация отчета» не нажималась (создаёт запись в LMS) — её сценарий
проверять в миссии: после нажатия в LMS «Отчёты» должен появиться `lrs_statement_export_…`
со статусами `pending → in_progress → completed` и `download_url`.

## Замечания (кандидаты в дефекты)

- «Клиенты хранилища»: пароль xAPI-клиента показан открытым текстом в таблице и уходит в
  Launch-ссылку в base64 — любой, кто видит страницу, получает доступ к записи statements.
- Переход LMS → LRS на develop сломан (`invalid_client`) и кнопки нет — конфигурация стенда.
