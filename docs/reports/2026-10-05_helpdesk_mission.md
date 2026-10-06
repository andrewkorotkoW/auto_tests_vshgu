# Итоговый отчёт по миссии Helpdesk

Миссия `docs/plans/2026-10-05_helpdesk_cases_mission.md`. На момент этого отчёта в репозитории
выполнены часть 1 (разведка, `docs/helpdesk_recon.md`, коммиты `6760620`/`6b652f0`), часть 2
(кейсы + Test IT v.3, коммиты `1a57338`/`cf0c65e`), часть 3 (автотесты, коммиты
`97ab740`/`89ed1b1` — инфраструктура, `5e06578`/`67f3d02` — API-тесты, `7ff8f70`/`2cb043b` —
UI-тесты, `a85cd05` — попутный фикс CSRF-регэкспа) и часть 4 (эта задача: починка инфраструктуры
Backpack-форм, коммит `79e841b`, t1; снятие xfail, коммиты `1a343de`/`f20fc24`, t2; автоматизация
10 оставшихся ручных кейсов, коммиты `85dce6a`/`0f8c717`, t3; финальный прогон, product_map и
документация — t4, эта задача). **44 из 48 кейсов, помеченные `- Автотест:`, реализованы кодом в
`tests/api/helpdesk/` и `tests/ui/helpdesk/admin/`; 4 кейса помечены `- Статус: ждёт подтверждения
владельца функционала` и не автоматизируются.** Раздел 6 ниже фиксирует фактический вывод прогона
pytest на `--env develop` (06.10.2026, после всех 51 тестов): 39 passed, 12 xfailed, 0 xpassed,
0 failed/error — ни одного неожиданного падения.

## 1. Таблица переноса кейсов v.2 → v.3

Источник — `docs/helpdesk_recon.md`, §4 (таблица актуальности 24 элементов выгрузки v.2:
21 test case + 3 shared steps). «Исправлен» = recon помечала `⚠️` и правка внесена в текст кейса
v.3; «устарел» = `❌`, не перенесён.

| ID v.2 | Название v.2 | Статус | Куда вошло (TC v.3) | Что изменилось |
|---|---|---|---|---|
| 9626 | Переход на таблицу тикетов | актуален | TICKETS-001 | без изменений |
| 9510 | Переход на «Системные группы» (shared steps) | актуален | GROUPS-001 | развёрнут в первый шаг кейса |
| 9511 | Создание группы | исправлен | GROUPS-002 (API), GROUPS-003 (UI) | добавлено необязательное поле «Пользователи» в форме |
| 9512 | Удаление группы | исправлен | GROUPS-006 (API), GROUPS-007 (UI) | текст модалки не хардкодится (не зафиксирован надёжно на разведке) — проверяется факт модалки/удаления |
| 9513 | Редактирование группы | актуален | GROUPS-005 | без изменений |
| 9514 | Просмотр группы | актуален | GROUPS-004 | без изменений |
| 9590 | Просмотр карточки пользователя | актуален | USERS-002 | без изменений |
| 9591 | Настройка таблицы тикетов для пользователя (shared steps) | актуален | USERS-003, USERS-004 | развёрнут в первые шаги двух кейсов (из списка и из карточки) |
| 9592 | Назначение роли(ролей) пользователю (shared steps) | актуален | USERS-005 (API), USERS-006 (UI) | развёрнут в первые шаги кейсов |
| 9605 | Поиск пользователя | исправлен | USERS-007 | переписано: email — прогрессивная фильтрация с 1-го символа; поиск по ФИО одним словом не работает (многословный случай вынесен в новый USERS-008, см. ниже) |
| 9606 | Поиск заявителя | исправлен | APPLICANTS-002, APPLICANTS-003 | разбит на два кейса (email — только полное совпадение; ФИО — нужно ≥2 слова), ожидаемый результат переписан |
| 9593 | Назначение ролей из карточки пользователя | **устарел** | — | в блоке «Действия» карточки (`/admin/user/{id}/show`) осталась только иконка «Редактировать» — шестерёнки назначения ролей больше нет, функциональность осталась только в списке (см. 9592 → USERS-005/006) |
| 9598 | Настройка таблицы тикетов из карточки пользователя | актуален | USERS-004 | без изменений |
| 9607 | Просмотр карточки заявителя | актуален | APPLICANTS-004 | без изменений (на деле детальнее описанного) |
| 9608 | Добавление нового заявителя | актуален | APPLICANTS-005 | без изменений |
| 9609 | Зачесть активити Программы/Потока из карточки пользователя | актуален | APPLICANTS-006 | без изменений, ручной (учебный домен вне скоупа) |
| 9610 | Зачесть активити индивидуального обучения из карточки пользователя | актуален | APPLICANTS-007 | без изменений, ручной |
| 9611 | Переход из карточки заявителя в карточку пользователя («Обучение») | актуален | APPLICANTS-008 | точное совпадение |
| 9620 | Переход на «Шаблоны» | исправлен | TEMPLATES-001 | колонка факт. называется «Группы» (мн. число), в v.2 — «Группа» |
| 9621 | Создание шаблона | актуален | TEMPLATES-002 (API), TEMPLATES-003 (UI) | без изменений |
| 9622 | Просмотр шаблона | актуален | TEMPLATES-004 | без изменений |
| 9623 | Редактирование шаблона | исправлен | TEMPLATES-005 | URL в выгрузке v.2 был ошибочным (`.../create`) — исправлен на `.../{id}/edit` |
| 9624 | Удаление шаблона | исправлен | TEMPLATES-006 | текст модалки не хардкодится, как и у 9512 |
| 9625 | Переход на «Дашборды» | исправлен | DASHBOARDS-001, DASHBOARDS-002, DASHBOARDS-003 | разбит на 3 кейса; добавлена 3-я метрика «Принято ответов от ИИ»; состав фильтров модалки (6 полей по DOM, а не 7 как в v.2) требует визуальной перепроверки |

23 из 24 элементов v.2 перенесены (один — shared-steps-основа без собственного UI — не теряется, см.
выше), 1 (`9593`) устарел.

### Новые кейсы, которых не было в v.2

Сверх перенесённых 23 добавлено 25 кейсов, не имеющих прообраза в выгрузке v.2 (итог — 48,
см. раздел 4): `USERS-001`/`APPLICANTS-001`/`TICKETS-001`/`TEMPLATES-001`/`DASHBOARDS-001` (переходы
по разделам меню — в v.2 были только частью shared steps, здесь выделены в отдельные кейсы
навигации), `TICKETS-002` (список тикетов — AJAX-паттерн DataTables, найден в разведке, в v.2 не
описан), `TICKETS-003`–`TICKETS-009` (7 базовых CRUD-кейсов для подтверждённых на стенде
справочников — требование плана миссии п.3), `USERS-008` (поиск пользователя многословным ФИО —
HTTP 500, кандидат в дефект, выделен из находки разведки отдельным кейсом), 9 негативных кейсов
(422/403/404 по группам, заявителям, шаблонам, пользователям).

## 2. Маршруты хелпдеска: что покрыто сейчас

Хелпдеск — не JSON REST API, а сервер-рендерящаяся Laravel Backpack-админка (см.
`docs/helpdesk_recon.md` §1): список `GET /admin/<entity>`, подгрузка строк `POST
/admin/<entity>/search` (DataTables), CRUD через `/admin/<entity>/create|{id}/edit|{id}/show` +
`POST`/`PUT`/`DELETE`, роли — через `GET`/`POST /admin/user/{id}/assign-role` (iframe-модалка),
дашборды — `POST /admin/dashboard/data/<metric>`.

**Автотесты с реальными проверками на этих маршрутах реализованы** (см. раздел 6): 51 тест в
`tests/api/helpdesk/` и `tests/ui/helpdesk/admin/`, использующие `HelpdeskEndpoint`
(`api/endpoints/helpdesk.py`) и `ui/pages/helpdesk_*.py`. Часть маршрутов (CRUD групп/шаблонов,
назначение роли, поиск пользователя) реально заблокирована инфраструктурными дефектами стенда —
покрыта тестом, но тест помечен `xfail(strict=False)` с описанием причины (раздел 3).

| Раздел | Маршруты | Кейсы (markdown) | Инфраструктура (t3) |
|---|---|---|---|
| Тикеты | `GET /admin/ticket`, `POST /admin/ticket/search` | TICKETS-001, 002 | `HelpdeskTicketsPage`, список в `HelpdeskEndpoint` |
| Группы | `/admin/group` (list/search/create/{id}/edit/{id}/show, `DELETE`) | GROUPS-001…010 | `HelpdeskEndpoint.create_group/find_group/get_group/update_group/delete_group`, `HelpdeskGroupsPage` |
| Пользователи | `/admin/user` (list/search), `/admin/user/{id}/show`, `/admin/user/{id}/edit`, `/admin/user/{id}/assign-role` | USERS-001…009 | `HelpdeskEndpoint` — поиск пользователя/заявителя, назначение роли; `HelpdeskUsersPage` |
| Заявители | `/admin/identity` (list/search/create/{id}/show) | APPLICANTS-001…009 | `HelpdeskEndpoint` — поиск/добавление заявителя; `HelpdeskApplicantsPage` |
| Шаблоны | `/admin/mail-template` (list/search/create/{id}/edit/{id}/show, `DELETE`) | TEMPLATES-001…008 | `HelpdeskEndpoint.*_template`, `HelpdeskTemplatesPage` |
| Дашборды | `/admin/dashboard`, `POST /admin/dashboard/data/<metric>` | DASHBOARDS-001…003 | `HelpdeskDashboardsPage` (навигация) |
| Справочники (7 шт.) | `/admin/dict/*`, `/admin/tag`, `/admin/blacklist` | TICKETS-003…009 | `HelpdeskDictEndpoint` (общий Backpack CRUD-паттерн, `test_dictionaries_api.py`), `HelpdeskDictPage` (`test_dictionaries.py`) — задача t3 |

Генераторы тестовых данных готовы: `generate_helpdesk_group_payload`,
`generate_helpdesk_template_payload`, `generate_helpdesk_applicant_payload`,
`generate_helpdesk_role_assignment_payload` (`api/helpers/data_generator.py`).

`tests/product_map.yml`: `int_helpdesk.tests` заполнен всеми 51 nodeid (сверено `--collect-only`
после задачи t3, пункт 2 части 4 этой задачи выполнен).

## 3. Кандидаты в дефекты

Обновлено по факту прогона из задачи t4 (раздел 6, `HEADLESS=1 pytest ... --env develop`,
06.10.2026). Три кандидата из прежней версии отчёта — **A, E, F** — **исправлены в рамках этой
миссии** коммитом `79e841b` («michael: Починить инфраструктуру хелпдеска: контракт Backpack-форм и
локаторы page-объектов», t1): затронутые тесты теперь зелёные. **B, C, D** остаются подтверждёнными
дефектами стенда — их правка вне скоупа задачи (чинит только бэкенд Laravel-админки, не purview
автотестов). Ниже также зафиксирован **G** — отдельный дефект, который раньше маскировался дефектом
A (CSRF-ошибка не давала запросу дойти до сервера) и стал виден только после фикса A.

**A. Инфраструктурный CSRF-дефект `HelpdeskEndpoint._csrf_token` — ИСПРАВЛЕНО (коммит `79e841b`,
t1).** Был: на develop реальная разметка — самозакрывающийся `<meta name="csrf-token"
content="..."/>`, а регэксп `_CSRF_META_RE` в `api/endpoints/helpdesk.py` ожидал `">` — токен не
находился, метод ронял `AssertionError` на любом create/update/delete/assign-role. Подтверждение
фикса фактическим прогоном: `test_applicants_api.py` (все 3) и `test_templates_api.py` (все 4) —
теперь **passed**, CSRF-токен читается корректно и запрос реально доходит до сервера.
`test_groups_api.py::test_create_group/view/update/delete` **остаются xfail**, но уже не из-за A — см.
дефект **G** ниже, который фикс A обнажил.

**B. `POST /admin/user/search` стабильно отдаёт `500` шире, чем предполагала разведка** — не
только на многословную ФИО-строку, а на любой запрос, не совпадающий с уже проиндексированными
сид-пользователями (`Undefined array key "data"`, `UserCrudController.php:82`); для тикетов тот же
паттерн поиска работает. Подтверждено повторно после фикса A (t1) — поведение не изменилось, дефект
не связан с CSRF/Accept. 4 nodeid: `tests/api/helpdesk/test_users_api.py::test_assign_role` (поиск
пользователя падает первым, не доходя до `assign_role()`), `::test_search_user_by_email`,
`tests/api/helpdesk/test_users_negative_api.py::test_search_user_multiword_returns_500_known_defect`
(исходный кандидат из разведки, п.1 ниже — подтверждён и расширен), `tests/ui/helpdesk/admin/test_users.py::test_assign_role`
(UI: свежесозданный пользователь не появляется в `/admin/user`, `recordsTotal` не меняется).

**C. `assign-role` на несуществующего пользователя — `500`, а не `404`.**
`RolesRepository::hasOneOfRoles()` получает `null` вместо `User` и бросает `TypeError`
(`UserCrudController.php:252`) — контроллер не проверяет существование пользователя. 1 nodeid:
`tests/api/helpdesk/test_users_negative_api.py::test_assign_role_not_found`.

**D. `user_session` и `admin_session` резолвятся в одного и того же пользователя на develop** —
подтверждено `GET /auth/me` для обеих фикстур; отдельного непривилегированного аккаунта для
негативного 403-кейса через эти фикстуры получить нельзя, запрос реально уходит от администратора
и получает 422 (валидация), а не 403. 1 nodeid:
`tests/api/helpdesk/test_groups_negative_api.py::test_create_group_forbidden_for_non_admin`.

**E. Вёрстка форм создания (группы, шаблоны): `<label>` не связан с `<input>` — ИСПРАВЛЕНО
(коммит `79e841b`, t1).** Был: ни через `for`/`id`, ни через обёртку — `page.get_by_label(...,
exact=True)` находил 0 элементов, таймаут 30с. Затронутые page-объекты (`ui/pages/helpdesk_groups_page.py`,
`ui/pages/helpdesk_templates_page.py`) переведены на устойчивые локаторы. Подтверждение фикса:
`tests/ui/helpdesk/admin/test_groups.py::test_create_group`, `::test_delete_group`,
`tests/ui/helpdesk/admin/test_templates.py::test_create_template` — теперь **passed**.

**F. Кнопка «Управление обучением» в карточке заявителя — на деле `<a href=... target="_blank">`,
а не `<button>` — ИСПРАВЛЕНО (коммит `79e841b`, t1).** Был: `get_by_role("button", ...)` находил 0
элементов (`get_by_role("link", ...)` — 2 совпадения), переход вдобавок открывался в новой вкладке.
`ui/pages/helpdesk_applicants_page.py` переведён на поиск по роли `link` и обработку новой вкладки.
Подтверждение фикса: `tests/ui/helpdesk/admin/test_applicants.py::test_navigate_to_user_education_tab`
— теперь **passed**.

**G. `GroupCrudController::store()`/`update()` бросает `500` (`TypeError`) при `Accept:
application/json` — подтверждённый дефект стенда, не исправлен (API-слой, вне скоупа задачи).**
Контроллер на успешном создании/обновлении группы возвращает `JsonResponse` вместо ожидаемого
Laravel `RedirectResponse`, из-за чего сам PHP-фреймворк бросает `TypeError` (HTTP 500) — группа при
этом реально создаётся/обновляется в БД. До фикса A (CSRF-регэксп) этот дефект был не виден: запрос
не доходил до сервера. Шаблоны/заявители/справочники с тем же заголовком `Accept` работают
нормально — дефект локален для `GroupCrudController`. 4 nodeid: `tests/api/helpdesk/test_groups_api.py::test_create_group`,
`::test_view_group`, `::test_update_group`, `::test_delete_group` (все требуют рабочего
`create_group` в предусловии, поэтому все 4 xfail). UI-слой (`tests/ui/helpdesk/admin/test_groups.py`)
дефект не задевает — браузерная форма не шлёт `Accept: application/json`, получает обычный редирект.

Прочие находки разведки (t1, `docs/helpdesk_recon.md` §5), не покрытые тестом:

1. **Пароль IMAP вводится в `type="text"`, а не `type="password"`** при создании/редактировании
   группы — значение видно открытым текстом. Минорная UX/security-заметка, не оформлена отдельным
   тестом (зафиксирована в предусловии `TC-HELPDESK_GROUPS-003`).
2. Второстепенные находки без отдельного кейса (§5.4–5.5): `<title>` не всегда обновляется при
   прямой навигации (не проверять `page.title()` в UI-тестах), пункт меню «Типы результата» не
   совпадает с заголовком страницы «Результаты обработки».

## 4. Статус Test IT

Проект «ВШГУ v.3» (globalId 9712), раздел **Helpdesk** — создан, в нём 48 кейсов во всех 6
подразделах (id из `testit_sync.py --apply`, записаны в `docs/test_cases/helpdesk/*.md` как
`- Test IT: <guid>`):

| Подраздел | Файл | Кейсов | С автотестом | Ждут подтверждения владельца |
|---|---|---|---|---|
| Тикеты | `tickets.md` | 9 | 9 | 0 |
| Группы | `groups.md` | 10 | 10 | 0 |
| Пользователи | `users.md` | 9 | 9 | 0 |
| Заявители | `applicants.md` | 9 | 7 | 2 |
| Шаблоны | `templates.md` | 8 | 8 | 0 |
| Дашборды | `dashboards.md` | 3 | 1 | 2 |
| **Всего** | | **48** | **44** | **4** |

Числа сверены по факту (`grep` по `docs/test_cases/helpdesk/*.md` после правок задачи t4), не взяты
из сообщения коммита. Рост с 33 до 44 автоматизированных кейсов — результат задачи t3 (10
ручных кейсов из коммита `0f8c717`/`85dce6a`: 7 справочников `TC-HELPDESK_TICKETS-003..009`,
настройка таблицы тикетов и карточка пользователя `TC-HELPDESK_USERS-002..004`, карточка заявителя
`TC-HELPDESK_APPLICANTS-004`). Оставшиеся 4 кейса (`TC-HELPDESK_APPLICANTS-006/007`,
`TC-HELPDESK_DASHBOARDS-002/003`) помечены «ждёт подтверждения владельца функционала» — зачисление
активити завязано на учебный домен вне скоупа миссии Helpdesk, а состав фильтров дашборда снят с
DOM без подтверждённого клика (см. предусловие `TC-HELPDESK_DASHBOARDS-003`). `TC-9593` (назначение
ролей из карточки, устарело) не перенесён — записано и в таблице раздела 1, и в примечании
`users.md`.

`python3 tools/test_cases/testit_sync.py --dry-run --docs-dir docs/test_cases/helpdesk
--parent-section Helpdesk` прогнан повторно после всех правок этой задачи (строки «- Автотест:» и
«- Статус:» не ломают парсинг): «6 областей, 48 кейсов, создать 0, обновить 48, ручных 4» — план
записан в `workspace/testit_export.json` без ошибок, `--apply` не запускался.

## 5. Статус test_hub

Коммит `cf0c65e` (т2) озаглавлен «md-кейсы Helpdesk → Test IT v.3 → **test_hub**» — подразумевает,
что шаг 5 плана (`POST /api/projects/VSHGU/testcases/import`) выполнялся. **В этой сессии результат
импорта не перепроверялся повторно** — у среды, где пишется этот отчёт (изолированный git-worktree),
нет сетевого доступа к `127.0.0.1:8700` (запросы к test_hub блокируются песочницей). Прямого
артефакта/лога импорта в репозитории не сохранилось (сам импорт ничего не пишет обратно в md).
Содержательно для импорта всё готово и согласовано с правилом «без дублей с `api/tickets`/
`ui/tickets`»: все 48 кейсов лежат в `docs/test_cases/helpdesk/` (разделы `tickets`, `groups`,
`users`, `applicants`, `templates`, `dashboards` — ровно подразделы Helpdesk, тикеты пользовательской
части лежат в отдельном `docs/test_cases/tickets.md` и не затрагивались). Статус — **заявлен в t2,
не подтверждён независимо в этом отчёте**.

## 6. Итог прогона автотестов (задача t4, финальный — после t1+t2+t3)

Эта версия раздела заменяет снятый снимок на 33 теста (до задачи t3): задача t3 добавила 10 новых
автоматизированных кейсов (справочники, карточка пользователя, настройки таблицы тикетов, карточка
заявителя — коммиты `85dce6a`/`0f8c717`), подняв общее число тестов helpdesk с 33 до **51**.
Прогнано 06.10.2026, `--env develop`, `HEADLESS=1`; API и UI запущены отдельными командами, чтобы не
превысить таймаут одного прогона.

```
HEADLESS=1 python3 -m pytest tests/api/helpdesk --env develop -q
```
```
collected 29 items
tests/api/helpdesk/test_applicants_api.py ...
tests/api/helpdesk/test_applicants_negative_api.py .
tests/api/helpdesk/test_dictionaries_api.py ......x
tests/api/helpdesk/test_groups_api.py xxxx
tests/api/helpdesk/test_groups_negative_api.py .x.
tests/api/helpdesk/test_templates_api.py ....
tests/api/helpdesk/test_templates_negative_api.py ..
tests/api/helpdesk/test_tickets_api.py .
tests/api/helpdesk/test_users_api.py xx
tests/api/helpdesk/test_users_negative_api.py xx
19 passed, 10 xfailed in 52.10s
```

```
HEADLESS=1 python3 -m pytest tests/ui/helpdesk --env develop -q
```
```
collected 22 items
tests/ui/helpdesk/admin/test_applicants.py ..
tests/ui/helpdesk/admin/test_dictionaries.py ......x
tests/ui/helpdesk/admin/test_groups.py ..
tests/ui/helpdesk/admin/test_navigation.py ......
tests/ui/helpdesk/admin/test_templates.py .
tests/ui/helpdesk/admin/test_users.py x...
20 passed, 2 xfailed in 229.75s (0:03:49)
```

**Итого: 51 собранных теста (29 API + 22 UI), 39 passed, 12 xfailed, 0 xpassed, 0 failed, 0 error.**
Ни одного неожиданного падения. 10 xfail в API: `test_dictionary_crud[blacklist]` (справочники, см.
прежний кандидат в дефекты про чёрный список), 4× `test_groups_api` (дефект **G**, раздел 3),
`test_create_group_forbidden_for_non_admin` (дефект D), `test_assign_role` + `test_search_user_by_email`
(дефект B), `test_search_user_multiword_returns_500_known_defect` (дефект B),
`test_assign_role_not_found` (дефект C). 2 xfail в UI: `test_dictionary_crud[blacklist]` (тот же
дефект справочника чёрного списка), `test_assign_role` (дефект B, UI-слой). Полные причины xfail —
текст `pytest -rA`, без хардкода; `exit code` обоих прогонов — `0` (`xfailed` со `strict=False` не
красит прогон).

## 7. Сверка раздела «Сдача» мишн-документа

| Пункт «Сдача» | Статус | Комментарий |
|---|---|---|
| Все новые тесты зелёные на develop (или xfail с причиной), вывод прогона приложить | ✅ выполнено | 51/51 собраны, 39 passed + 12 xfailed (с причиной), 0 xpassed/failed/error — вывод в разделе 6 |
| В Test IT «ВШГУ v.3» есть раздел Helpdesk с кейсами | ✅ выполнено | 48 кейсов, id записаны в md, раздел 4; 44 с `- Автотест:`, 4 со `- Статус: ждёт подтверждения владельца` |
| В test_hub проект VSHGU содержит разделы `helpdesk/*` | ⚠️ заявлено, не перепроверено | коммит `cf0c65e` подразумевает импорт выполнен; в этой сессии нет сетевого доступа к test_hub для независимой проверки, раздел 5 |
| Отчёт: таблица переноса, список покрытых маршрутов, кандидаты в дефекты | ✅ выполнено | этот документ, разделы 1–3; A/E/F отмечены исправленными в этой миссии (t1), G — новый подтверждённый дефект |
| `README.md`/`docs/`: короткий раздел «Helpdesk: что покрыто, как запускать» | ✅ выполнено | `README.md`, раздел 18 — обновлён под факт 51 теста |

**Итог:** части 1–4 миссии выполнены (разведка, кейсы → Test IT, автотесты, инфраструктурный фикс +
снятие xfail + 10 новых кейсов + финальная документация); `int_helpdesk.tests` в
`tests/product_map.yml` заполнен всеми 51 nodeid (сверено `--collect-only`). Раздел «Сдача» выполнен
на 4 из 5 пунктов — импорт в test_hub остаётся заявленным, но не перепроверенным независимо
(ограничение сетевого доступа этой
сессии, раздел 5), остальное подтверждено фактическим прогоном и кодом.
