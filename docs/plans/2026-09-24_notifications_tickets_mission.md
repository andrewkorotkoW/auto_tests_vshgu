# Миссия: автотесты «Уведомления» и «Обращения в техподдержку» (develop)

Записано 24.09.2026. Две области портала с нулевым покрытием по test_hub:
`/api/v1/notifications/*` (23 маршрута) и `/api/v1/tickets/*` (5 маршрутов).

## Правила (обязательны)

- Стенд только `--env develop` (`HEADLESS=1`). Stage, prod и ЛПД не трогать.
- Учётки и токены только из `.env` через `config/environments.py` (`get_credentials`,
  `api_client`, `admin_session`, `user_session`). Значения `.env` в код, логи и коммиты не писать.
- Структура как в проекте: клиенты в `api/endpoints/<area>.py`, тесты в
  `tests/api/<area>/` и `tests/ui/<area>/`, фикстуры в `conftest.py` рядом с тестами,
  генерация данных в `api/helpers/data_generator.py`, маркеры `api`/`ui`, allure
  `@allure.feature/@allure.story/@allure.title` на русском, `expect_status`.
- Каждый тест независим: сам создаёт данные с префиксом `Автотест_` и удаляет их в
  teardown, даже при падении. Никаких хардкодов id из БД, кроме уже принятых в settings.
- Запускать только свои тесты (`pytest tests/api/notifications ...`), не полный прогон.
- Если эндпоинт ведёт себя не так, как ожидалось, — не подгонять assert под факт: пометить
  `xfail(strict=False)` с причиной и записать в отчёт задачи как кандидата в дефекты.

## Часть 1. Уведомления — API

Сначала разведка: вызвать GET `/notifications`, `/notifications/text-variables`,
`/notifications/creators`, `/notifications/receivers`, `/notifications/templates` от админа и
зафиксировать реальные схемы ответов и обязательные поля `POST /notifications/create`
(подсмотреть в UI админки: раздел «Уведомления», кнопка создания — через Playwright
перехватить запрос). Потом тесты:

1. Списки: `GET /notifications`, `/creators`, `/receivers`, `/text-variables` → 200, JSON,
   непустые справочники, у уведомления есть id/тема/дата/получатели.
2. Создание: админ `POST /notifications/create` (получатель — тестовый пользователь из
   `user_session`) → 200/201; уведомление появляется в `GET /notifications` и
   `GET /notifications/{id}` с теми же полями.
3. Пользователь видит уведомление: от `user_session` `GET /notifications` содержит созданное.
4. Повторная отправка `POST /notifications/resend/{id}` → 200.
5. Удаление `POST /notifications/delete` → 200, уведомление исчезает из списка.
6. Шаблоны: `POST /notifications/templates` → `GET /templates/{id}` → `PUT` (смена темы/текста)
   → `POST /templates/delete`; список `GET /templates` содержит/не содержит шаблон.
7. Негатив: создание без получателей и без текста → 422 с сообщением; `GET /notifications/{id}`
   от пользователя, которому оно не адресовано → 403/404; чужой id → 404.
8. Шаблоны регистрации и ревью: `GET /register-templates`, `GET /register-templates/{type}`,
   `GET /review-templates` → 200 и схема; `POST/PUT` только если разведка покажет безопасный
   round-trip (вернуть исходное значение в teardown).

## Часть 2. Уведомления — UI (1–2 теста)

- Пользователь: после создания уведомления через API открыть портал, пункт «Уведомления»
  в сайдбаре (`ui/pages/user_sidebar_page.py`), увидеть тему уведомления, открыть, текст
  совпадает. Использовать `dismiss_popups`.
- Админ: раздел «Уведомления» в админке показывает созданное уведомление в таблице.

## Часть 3. Обращения в техподдержку — API + UI

1. `POST /tickets` от пользователя (тема, текст) → 200/201, id.
2. `GET /tickets/my-tickets` содержит обращение со статусом «открыто».
3. `POST /tickets/{id}/messages` (текст) → 200; `GET /tickets/{id}/messages` содержит
   первое и добавленное сообщение в правильном порядке.
4. `PUT /tickets/{id}/close` → 200; в `my-tickets` статус «закрыто»; повторное закрытие и
   сообщение в закрытое обращение → 4xx (зафиксировать фактический код).
5. Негатив: пустая тема/текст → 422; чужой ticket id от другого пользователя → 403/404.
6. UI: пользователь открывает «Техподдержка» в сайдбаре, создаёт обращение через форму,
   видит его в списке, открывает переписку. Хелпдеск-админку (`helpdesk-develop`) не тестировать.

## Сдача

- Все новые тесты зелёные на develop (или xfail с причиной), прогон приложить
  (`pytest tests/api/notifications tests/api/tickets tests/ui/notifications tests/ui/tickets
  --env develop -q`).
- В `README.md`/`docs/` — короткий раздел «Уведомления и техподдержка: что покрыто».
- Отчёт задачи: список маршрутов, которые теперь покрыты, и кандидаты в дефекты.
