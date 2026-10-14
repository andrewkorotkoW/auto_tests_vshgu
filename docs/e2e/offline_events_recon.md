# Разведка: очные мероприятия (поток и индивидуальный трек), develop, 14.10.2026

Для черновиков TC-E2E-020/021 из `docs/plans/2026-10-14_e2e_markers_mission.md`. Всё
проверено живыми запросами и Playwright на develop; тестовые данные удалены.

## Поток: мероприятие = элемент расписания модуля

- **Создание (API):** `POST /api/v1/programs/{program}/streams/{stream}/modules/{module}/schedule-items`
  — уже есть `ScheduleItemsEndpoint.create` и `generate_schedule_item_payload`
  (`tests/api/programs/test_create_schedule_item_api.py`). Тип — enum `App\Enums\ScheduleItemType`:
  `webinar` работает, `offline`/`zzz` → **500** `ValueError … not a valid backing value` (не 422 —
  кандидат в дефект валидации). Остальные значения enum смотреть в форме админки; для e2e достаточно
  `webinar` с `content_type: offline` (в UI слушателя подпись «Вебинар»).
- **Модуль:** если `must_use_module_region=true` без региона, в «Расписании» админки поле «Регион
  реализации» красное — для e2e создавать модуль с регионом (`region_id` 33) или снять галочку
  «Модуль реализуется в одном регионе».
- **Админка:** `/admin/programs/{program}/streams/{stream}` → вкладка «Расписание» → у модуля кнопки
  **«О»** (очная часть) и **«Д»** (дистант). «Д» — таблица активити (`GET …/modules/{id}/contents`),
  **«О»** — недельный календарь мероприятий (`GET …/modules/{id}/schedule-items`, `GET /streams/{stream}/
  schedule-items/visitors`, `GET /users/teachers`), кнопки «Копировать», «Выбрать». Созданное через
  API мероприятие видно в календаре: название, место, `10:05 - 11:05`, преподаватель. Вкладка
  «Слушатели» — колонки «Очка»/«Дистант» (фильтр `event_types=distant`). Прямых URL вида
  `/admin/…/schedule-items/create` нет (пустая страница) — page object
  `ui/pages/admin_event_mts_page.py` строит несуществующие адреса (TODO там и остался).
- **Назначение слушателя:** `AssignmentsEndpoint.assign(program, stream, [user])` — после этого
  слушатель есть в `GET /api/v1/streams/schedule-item/{item}/users` с
  `registration_type: not_registered`, `state: 0`.
- **Отметка посещения (админ):** `POST /api/v1/schedule-item/{item}/user/{user}/update-registration-status`
  с телом `{"data":{"attributes":{"is_registered":true}}}` → `{"data":{"status":"success"}}`.
  Без `is_registered` → 422. `GET` на тот же путь (`/streams/schedule-item/…/update-registration-status`)
  → 500 `updateUserRegistrationStatus does not exist` (мёртвый маршрут). Есть QR-вариант
  `POST /schedule-item/{item}/update-registration-status` и `GET /streams/{stream}/schedule-registration-link/{linkType}`.
  `GET /streams/schedule-item/{item}/user/{user}/registration-form` — карточка «мероприятие + пользователь».
- **Слушатель:** «Моё обучение» → «Перейти к программе» → `/education/program/{assignment_uuid}/module/{module}`
  → вкладка **«Расписание»** (`…/module/{module}/schedule`): API
  `GET /api/v1/my-programs/{assignment}/modules/{module}/schedule-items?per-page=9999` и
  `POST /api/v1/schedule-item/check-user-registration` → `[{"event_id":877,"status":true}]` после отметки.
  В UI карточка мероприятия в календаре (Вебинар, название, место, преподаватель), после отметки —
  зелёная галочка на карточке и в правой панели. На вкладке при первом входе есть тур
  «1 из 3 … В календаре отображаются ближайшие мероприятия» с демо-данными «Пример мероприятия» —
  закрывать `dismiss_popups()` после перехода на страницу программы, иначе scrim перехватывает клики.
- **Очистка:** `ScheduleItemsEndpoint.delete`, программа — `ProgramsEndpoint.mass_delete`
  (`DELETE /programs/{id}` не поддерживается).

## Индивидуальный трек: «очное обучение» = offline-активити пользователя

- **Создание (API, админ):** `POST /api/v1/users/content/offline`, тело
  `{"data":{"user_ids":[uid],"attributes":{"content_type":"offline","name":"…","date_time_from":"YYYY-MM-DDTHH:MM",
  "date_time_to":"…","location":"Москва","teacher_ids":[4]}}}` → `201/200`, `data.id` = id контента
  (`content_type: offline`, `iri: …/content/{id}`). Обязательные: `user_ids`, `name`, `date_time_from`,
  `date_time_to`; `content_type` только `offline` (иначе 400 «Неправильный тип контента»).
- **Список/изменение:** `GET /users/content/offline/user-content/{user}`, `PUT /users/content/offline/{id}`.
- **Слушатель:** `GET /api/v1/offline` (список своих очных занятий), UI — «Индивидуальное обучение» →
  «Расписание» (`/education/personal/schedule?d={id}&e={id}`): карточка с датой, местом, преподавателем.
  На главной «Моё обучение» при одном очном занятии без программ написано «У вас нет программ» — очное
  занятие видно только в «Расписании» инд. обучения.
- **Отметка посещения в инд. треке:** отдельного маршрута не нашёл (у schedule-items он есть); проверить
  в админке карточку пользователя → «Назначения» (вкладки карточки: Общая информация, Назначения,
  Сертификаты, Отчеты ЛПД, Документы о квалификации) — в разведку не вошло.
- **Очистка:** `DELETE /users/content/offline/detach-activities` с `{"data":{"attributes":{"user_ids":[…],
  "content_ids":[…]}}}` → 200; сам контент удаляется общим `DELETE /tests` с `{"contents_ids":[…]}`
  (как `AosEndpoint.mass_delete`). `DELETE /users/content/offline/{id}` → 404 (ищет модель Activity).

## Что положить в кейсы

- **TC-E2E-020 (поток):** API: программа → поток (с регионом модуля) → модуль → мероприятие `webinar`;
  назначить `prepared_user`; UI слушателя: программа → «Расписание» → карточка без галочки;
  API админа: `is_registered=true`; UI слушателя после перезагрузки: галочка на карточке
  (и `check-user-registration` → `status:true`); админка: «Расписание» → «О» → мероприятие в календаре.
- **TC-E2E-021 (инд. трек):** API: `POST /users/content/offline` на `prepared_user`; UI слушателя:
  «Индивидуальное обучение» → «Расписание» → карточка; API `GET /offline` содержит занятие;
  teardown: detach + `DELETE /tests`.
- Кандидаты в дефекты: 500 вместо 422 на неверном `type` элемента расписания; мёртвый `GET …/update-registration-status`.
