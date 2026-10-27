# Тест-кейсы: LRS (OpenLRS)

| Параметр | Значение |
|---|---|
| Область | tests/ui/lrs, tests/e2e/lrs (конструктор и SCORM) |
| Стенд | ревью-стенды `https://lrs-<ветка>.d2.devspark.ru/lrs-admin` (вход SSO из `portal-<ветка>`; эталон — vshgu2-2420-filters, 27.10.2026) и k8s (выведен); develop — после регистрации OAuth-клиента LRS в Passport (сейчас `invalid_client`, см. docs/lrs/lrs_recon.md) |
| Роли | admin — пользователь LMS с правом `logs-index` («Логи»); user — слушатель без доступа в админку |

<!-- Кейсы написаны вручную по разведке docs/lrs/lrs_recon.md (14.10.2026) и описанию
     функционала от владельца; tools/test_cases/generate.py их не создавал. Хранилище для
     тестов — `default store` (id 1). Отчёты, созданные тестами, удалять через
     `DELETE /api/v1/exports/mass-delete`; statements/states не удалять. -->

### TC-LRS-001 Переход из LMS в LRS по кнопке «Перейти в LRS» (SSO)
- Автотест: tests/ui/lrs/test_lrs_navigation.py::TestLrsNavigation::test_admin_opens_lrs_from_logs
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: admin авторизован в LMS формой (web-сессия; API-кука для OAuth не подходит)
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть админку → «Логи» → вкладка «Изменения» (`/admin/logs/changes`) | Над таблицей справа есть кнопка-ссылка «Перейти в LRS», `href` = `https://lrs-<стенд>/oauth2/auth/callback`, открывается в новой вкладке (`target=_blank`); на `/admin/logs` кнопки нет |
| 2 | Нажать кнопку | В новой вкладке цепочка: `302` → LMS `GET /api/v1/oauth/authorize?client_id=…&scope=user-info user-role&approval_prompt=auto` → `302` обратно на callback с `code` → страница `/lrs-admin`, заголовок «Панель управления :: OpenLRS» |
| 3 | Проверить шапку OpenLRS | ФИО и организация текущего пользователя LMS (например «Вера Сергеев / Главная»), форма входа не показывалась |

### TC-LRS-002 Прямой переход на callback без кнопки
- Автотест: tests/ui/lrs/test_lrs_navigation.py::TestLrsNavigation::test_callback_logs_in_authorized_user
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: admin авторизован в LMS формой
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть `https://lrs-<стенд>/oauth2/auth/callback` | Попадаем в `/lrs-admin` под тем же пользователем (тот же результат, что по кнопке) |
| 2 | Открыть `/lrs-admin/store` в той же сессии | Список хранилищ открывается без повторного входа |

### TC-LRS-003 Без сессии LMS OpenLRS требует вход
- Автотест: tests/ui/lrs/test_lrs_navigation.py::TestLrsNavigation::test_lrs_admin_without_session_shows_login
- Приоритет: medium   Тип: ui   Роли: -
- Предусловия: чистый контекст браузера
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть `https://lrs-<стенд>/lrs-admin` | Редирект на `/lrs-admin/login`, заголовок «Войти :: OpenLRS», поля email/password/remember |
| 2 | Открыть `/oauth2/auth/callback` | Редирект на LMS `/api/v1/oauth/authorize`, LMS без web-сессии не выдаёт код (страница входа LMS / 401), в LRS не пускает |

### TC-LRS-004 Слушатель без прав админки не видит «Перейти в LRS» и не входит в LRS
- Автотест: tests/ui/lrs/test_lrs_navigation.py::TestLrsNavigation::test_user_without_admin_rights_cannot_enter_lrs
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: `prepared_user` (свежий слушатель), авторизован в LMS формой
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть `/admin/logs/changes` | Доступ в админку закрыт (редирект/«нет прав»), кнопки «Перейти в LRS» нет |
| 2 | Открыть `https://lrs-<стенд>/oauth2/auth/callback` | OpenLRS не пускает: форма входа, сообщение об отказе или обрыв навигации (на k8s — `net::ERR_ABORTED`); `/lrs-admin/store` недоступен. Если LRS впускает слушателя — зафиксировать как кандидата в дефект (scope `user-role` должен ограничивать) |

### TC-LRS-005 Возврат в LMS по кнопке «Перейти в LMS»
- Автотест: tests/ui/lrs/test_lrs_navigation.py::TestLrsNavigation::test_back_to_lms_button
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS (TC-LRS-001)
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | В боковом меню OpenLRS нажать «Перейти в LMS» | В новой вкладке (`target=_blank`) открывается `https://portal-<стенд>/admin/programs`, пользователь по-прежнему авторизован в LMS (без формы входа); вкладка OpenLRS остаётся |

### TC-LRS-006 Список хранилищ и переход в хранилище
- Автотест: tests/ui/lrs/test_lrs_stores.py::TestLrsStores::test_stores_list_and_open_default_store
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть «Хранилища» (`/lrs-admin/store`) | Таблица с колонками Название, Папка, Размер, Количество states, Количество statements; есть `default store`; кнопка «Добавить Хранилище» |
| 2 | Нажать на `default store` | Открывается `/lrs-admin/store/1/client` («Клиенты хранилища»), вкладки: Клиенты хранилища, Statements, States, Activity profiles, Agents; в боковом меню хранилище подсвечено |
| 3 | Сравнить «Количество statements» из шага 1 с числом записей на вкладке Statements (`recordsFiltered` из `POST …/statement/search`; `recordsTotal` там — размер страницы) | Счётчик в списке — кэш, отстаёт от таблицы (2420, 27.10.2026: «6» при 8 statements; при нуле — «-», размер 0 MB): число в списке не больше `recordsFiltered`, после обновления кэша совпадает |

### TC-LRS-007 Клиенты хранилища: xAPI-endpoint и Launch-ссылка
- Автотест: tests/ui/lrs/test_lrs_stores.py::TestLrsStores::test_store_clients_launch_link
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS, у `default store` есть клиент
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть «Клиенты хранилища» | Таблица: Логин, Пароль, Дата создания, Launch, Действия (Предпросмотр, Редактировать, Удалить); кнопка «Добавить Клиент» |
| 2 | Прочитать `href` ссылки «Launch» | Query-строка `?endpoint=https://lrs-<стенд>/xAPI&auth=Basic+<base64 логин:пароль>&actor=…&registration=<uuid>&activity_id=` (пробел закодирован `+`, `activity_id` пустой) — base64 совпадает с логином/паролем из строки |
| 3 | `GET https://lrs-<стенд>/xAPI/about` с этим Basic | Ответ 200, JSON с `version` (xAPI 1.0.x) |

### TC-LRS-008 Вкладка Statements: таблица, предпросмотр, ссылка в карточку пользователя LMS
- Автотест: tests/ui/lrs/test_lrs_statements.py::TestLrsStatements::test_statements_table_preview_and_agent_link
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS; в `default store` есть хотя бы один statement
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть `/lrs-admin/store/1/statement` | Колонки Agent, Verb, Activity, Дата создания statement-а, Действия; записи отсортированы по дате убыванием; аккордеон «Скачать архив», кнопка «Генерация отчета», ссылка «Сбросить» у заголовка (сброс состояния таблицы), панель фильтров Agent ID / Verb / Activity ID / Registration / Date; пагинация и «записей на странице» |
| 2 | Нажать «Предпросмотр» у первой записи | Страница `/statement/{id}/show`: поля Agent, Verb, Activity, Дата, Registration, Voided, Payload и JSON statement'а: `actor.account.name` = Agent из таблицы, `actor.account.homePage` = `https://portal-<стенд>/accounts/userid`, `verb.id` = `http://adlnet.gov/expapi/verbs/<verb>`; кнопка «Вернуться к списку» |
| 3 | В таблице нажать на значение Agent | В новой вкладке (`target=_blank`) открывается карточка пользователя LMS `https://portal-<стенд>/admin/users/{agent}`, id в URL = Agent |

### TC-LRS-009 Фильтры Statements: Agent ID, Verb, Date
- Автотест: tests/ui/lrs/test_lrs_statements.py::TestLrsStatements::test_statements_filters
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS; известен agent со statements (например из TC-LRS-013)
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Раскрыть фильтр «Agent ID», ввести id агента в поиск select2, выбрать опцию | Через ~1 с (debounce) `POST …/statement/search?agent_id=["<id>"]`, URL страницы получает `agent_id=["<id>"]`; в таблице только строки этого Agent; в панели появляется «Сбросить» |
| 2 | Раскрыть фильтр «Date», в daterangepicker выбрать пресет «Сегодня» | URL получает `statement_timestamp={"from":…,"to":…}`; все даты строк сегодняшние |
| 3 | «Сбросить» в панели фильтров | URL без параметров, `recordsTotal` как до фильтрации, «Сбросить» скрыта |
| 4 | Раскрыть фильтр «Verb», ввести `passed`, выбрать | Только строки с verb `passed`. На ветке 2420-filters (27.10.2026) виджет без опций (`#filter_verb` пуст, «Совпадений не найдено»), хотя прямой `?verb=["http://adlnet.gov/expapi/verbs/passed"]` фильтрует — дефект, автотест → xfail |

### TC-LRS-010 Вкладка Agents: ссылки Statements / State по агенту и переход в карточку LMS
- Автотест: tests/ui/lrs/test_lrs_statements.py::TestLrsStatements::test_agents_tab_links
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS; есть агент со statements
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть `/lrs-admin/store/1/agent` | Колонка `account_name` (id пользователя LMS) и кнопки Statements, State у каждой строки |
| 2 | Нажать `account_name` | В новой вкладке карточка пользователя LMS `/admin/users/<id>` |
| 3 | Нажать Statements у агента | Открывается `/statement?agent_id=<id>`, в таблице только его записи. На ветке 2420-filters (27.10.2026) `agent_id` передаётся скаляром и фильтр не применяется (видны все агенты; виджет пишет `agent_id=["<id>"]` и работает) — дефект, автотест → xfail |

### TC-LRS-011 Генерация отчёта из Statements → отчёт в LMS «Отчёты»
- Автотест: tests/ui/lrs/test_lrs_report.py::TestLrsReport::test_generate_report_appears_in_lms_exports
- Приоритет: high   Тип: e2e   Роли: admin
- Предусловия: admin в OpenLRS (SSO); отчёты, созданные тестом, удаляются в teardown через `DELETE /api/v1/exports/mass-delete`
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | На вкладке Statements выбрать фильтр «Date» (без него сервер отвечает 422: `statement_timestamp` обязателен) и нажать «Генерация отчета» | `POST …/store/1/statement/report_generation?statement_timestamp=…` → 2xx, ошибок нет. На k8s (14.10) и 2420 (27.10.2026) — **500**, отчёт не создаётся — дефект, автотест → xfail |
| 2 | `GET /api/v1/exports` в LMS под тем же админом (сразу) | Появился отчёт `type: 14`, `name` = `lrs_statement_export_<дата>_<ts>.xlsx`, `status` = `pending` или `in_progress`, `download_url` пустой |
| 3 | Опрашивать `GET /api/v1/exports` до 3 минут | `status` = `completed`, `download_url` заполнен (`…/static/tmp/<uuid>/…zip`) |
| 4 | Скачать файл по `download_url` | ZIP с xlsx внутри; в xlsx есть строки statements (при фильтре по агенту — только его) |
| 5 | Открыть в LMS «Отчёты» (`/admin/reports` или раздел «Отчёты» в меню) | Отчёт виден в списке со статусом «Готов», скачивается |

### TC-LRS-012 «Скачать архив» на вкладке Statements
- Автотест: tests/ui/lrs/test_lrs_report.py::TestLrsReport::test_download_archive
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Раскрыть аккордеон «Скачать архив», выбрать день (поле «День», архив за один день) и нажать «Скачать» | `GET https://lrs-<стенд>/store/1/archive/download?date=YYYY-MM-DD` → zip, размер > 0. За день без собранного архива — 302 назад без файла (на свежем стенде архивов нет — автотест ищет день за последние 30 дней и скипается, если ни одного) |

### TC-LRS-013 Сквозной: слушатель проходит тест в LMS → statement в LRS с его id
- Автотест: tests/e2e/lrs/test_statement_after_test_pass.py::TestLrsStatementFlow::test_passed_test_creates_statements
- Приоритет: high   Тип: e2e   Роли: admin, user
- Предусловия: через API создан тест (конструктор, как в `tests/ui/test_constructor`) и назначен `prepared_user`; admin — для LRS. Statements не удаляются
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Слушатель в UI проходит назначенный тест до результата | Тест пройден (экран результата) |
| 2 | admin в OpenLRS → Statements, фильтр Agent ID = id слушателя (ретраи до 60 с) | Есть записи с verb `launched`, `answered`, `passed`/`failed`; `actor.account.name` = id слушателя |
| 3 | Предпросмотр statement'а `passed`/`answered` | В JSON `actor.account.homePage` = `https://portal-<стенд>/accounts/userid`, `result`/`object` заполнены |
| 4 | Вкладка Agents | Появился агент с `account_name` = id слушателя |

### TC-LRS-014 Вкладка States: записи плеера и ссылки
- Автотест: tests/ui/lrs/test_lrs_statements.py::TestLrsStatements::test_states_tab
- Приоритет: low   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS; в хранилище есть states (tincan-курс Courseditor)
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть `/lrs-admin/store/1/state` | Колонки Agent, State key, Activity IRI, Registration, Действия (Предпросмотр, Удалить); панель фильтров ID agent / State key / Activity / Registration (`agent_id`, `activity_iri`, `registration` — текст, `state_key` — select2). Без states (тесты конструктора их не пишут, нужен SCORM/xAPI-курс) автотест скипается |
| 2 | Нажать на Agent | В новой вкладке карточка пользователя LMS `/admin/users/<id>` |
| 3 | «Предпросмотр» | Страница `/state/{id}/show` с содержимым state (JSON) |

### TC-LRS-015 Форма входа OpenLRS не принимает учётку LMS (документированное поведение)
- Автотест: tests/ui/lrs/test_lrs_navigation.py::TestLrsNavigation::test_lrs_login_form_rejects_lms_credentials
- Приоритет: low   Тип: ui   Роли: admin
- Предусловия: чистый контекст
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | На `/lrs-admin/login` ввести email/пароль админа LMS, «Войти» | Остаёмся на форме входа (OpenLRS хранит своих пользователей отдельно, штатный вход — SSO). Если форма впускает — поведение изменилось, кейс пересмотреть |

### TC-LRS-016 Сквозной: слушатель проходит SCORM-курс → statements и state в LRS с его id
- Автотест: tests/e2e/lrs/test_scorm_statements_in_lrs.py::TestLrsScormFlow::test_scorm_pass_creates_statements_and_state
- Приоритет: high   Тип: e2e   Роли: admin, user
- Предусловия: через API создан курс SCORM 2004 (`test_data/test_lms_scorm_2004.zip`) и назначен `prepared_user` в инд. обучение; admin — для OpenLRS (SSO). Statements/states не удаляются, курс удаляется
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Слушатель проходит курс в UI (TC-COURSES-004, шаги 1–5) | Results «Your Score: 100%», SCORM completed/passed/100, «Повторить» |
| 2 | admin в OpenLRS → default store → Statements, фильтр Agent ID = id слушателя (ретраи до 60 с) | Записи с verb `initialized`, `launched`, `responded`, `passed`, `completed` (плюс `suspended` после закрытия плеера); Activity в таблице «-» |
| 3 | Предпросмотр statement `passed` | JSON: `actor.account.name` = id слушателя, `actor.account.homePage` = `https://portal-<стенд>/accounts/userid`, `object.id` = `https://portal-<стенд>/content/<id курса>`, `object.definition.type` = `…/activities/course`, `context.registration` заполнен |
| 4 | Вкладка States, фильтр «ID agent» = id слушателя | Есть запись: State key `activitystate`, Activity IRI = `https://portal-<стенд>/` (драйвер делает `PUT /xAPI/activities/state`) |
| 5 | Сверить счёт: `result.score.raw` в statement `passed` и `cmi.score.raw` в SCORM API | Совпадают (100). На 2420 (27.10.2026) statement уходит с `result.score.raw = 0` при `cmi.score.raw = 100`, `cmi.score.scaled = 1` — кандидат в дефект конвертации SCORM → xAPI, автотест → xfail |
