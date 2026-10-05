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

## Структура файлов (обязательно, как в дереве проекта)

Область → папка, внутри API-тесты по смыслу, UI-тесты по ролям `admin/` и `user/`
(как `tests/ui/aos/admin`, `tests/ui/cas/user`). Никаких тестов в корне `tests/api` или `tests/ui`.

```
api/endpoints/notifications.py           # NotificationsEndpoint: list, create, view, resend, delete,
                                         #   templates_*, register_templates_*, review_templates_*, dictionaries
api/endpoints/tickets.py                 # TicketsEndpoint: create, my_tickets, messages, add_message, close
api/helpers/data_generator.py            # generate_notification_payload(), generate_ticket_payload()

tests/api/notifications/
  conftest.py                            # notifications_endpoint, created_notification (teardown delete),
                                         #   created_template (teardown delete)
  test_notifications_lists_api.py        # GET /notifications, /creators, /receivers, /text-variables
  test_notifications_crud_api.py         # create → view → user sees → resend → delete
  test_notifications_negative_api.py     # 422 без получателей/текста, 403/404 чужое и несуществующее
  templates/
    test_notification_templates_api.py   # POST → GET → PUT → delete, список
    test_register_review_templates_api.py# register-templates и review-templates (чтение; PUT только с откатом)

tests/api/tickets/
  conftest.py                            # tickets_endpoint, created_ticket (teardown close)
  test_tickets_crud_api.py               # create → my-tickets → close → статус «закрыто»
  test_tickets_messages_api.py           # add message → messages порядок и содержимое
  test_tickets_negative_api.py           # 422 пустые поля, чужой id, действия с закрытым

tests/ui/notifications/
  admin/test_admin_notifications_table.py   # созданное через API уведомление видно в таблице админки
  user/test_user_sees_notification.py       # пользователь открывает «Уведомления», видит тему и текст
tests/ui/tickets/
  user/test_user_creates_ticket.py          # пользователь создаёт обращение через форму «Техподдержка»

ui/pages/user_notifications_page.py
ui/pages/user_support_page.py
ui/pages/admin_notifications_page.py
```

Имена файлов `test_<что>_api.py` / `test_<роль>_<что>.py`, классы `Test<Что>API` /
`Test<Роль><Что>`, как в соседних папках. `__init__.py` в новых папках `tests/ui/...` —
как у соседей (посмотреть `tests/ui/aos`).
