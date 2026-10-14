# Тест-кейсы: LRS (OpenLRS)

| Параметр | Значение |
|---|---|
| Область | tests/ui/lrs, tests/e2e/lrs |
| Стенд | k8s (`https://lrs-k8s-release.v2.gosedu.ru/lrs-admin`, вход SSO из `portal-k8s-release`); develop — после регистрации OAuth-клиента LRS в Passport (сейчас `invalid_client`, см. docs/lrs/lrs_recon.md) |
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
| 1 | Открыть админку → «Логи» (`/admin/logs`) | Над таблицей справа есть кнопка-ссылка «Перейти в LRS», `href` = `https://lrs-<стенд>/oauth2/auth/callback` |
| 2 | Нажать кнопку | Цепочка: `302` → LMS `GET /api/v1/oauth/authorize?client_id=…&scope=user-info user-role&approval_prompt=auto` → `302` обратно на callback с `code` → страница `/lrs-admin`, заголовок «Панель управления :: OpenLRS» |
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
| 1 | Открыть `/admin/logs` | Доступ в админку закрыт (редирект/«нет прав»), кнопки «Перейти в LRS» нет |
| 2 | Открыть `https://lrs-<стенд>/oauth2/auth/callback` | OpenLRS не пускает: форма входа или сообщение об отказе; `/lrs-admin/store` недоступен. Если LRS впускает слушателя — зафиксировать как кандидата в дефект (scope `user-role` должен ограничивать) |

### TC-LRS-005 Возврат в LMS по кнопке «Перейти в LMS»
- Автотест: tests/ui/lrs/test_lrs_navigation.py::TestLrsNavigation::test_back_to_lms_button
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS (TC-LRS-001)
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | В боковом меню OpenLRS нажать «Перейти в LMS» | Открывается `https://portal-<стенд>/admin/programs`, пользователь по-прежнему авторизован в LMS (без формы входа) |

### TC-LRS-006 Список хранилищ и переход в хранилище
- Автотест: tests/ui/lrs/test_lrs_stores.py::TestLrsStores::test_stores_list_and_open_default_store
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть «Хранилища» (`/lrs-admin/store`) | Таблица с колонками Название, Папка, Размер, Количество states, Количество statements; есть `default store`; кнопка «Добавить Хранилище» |
| 2 | Нажать на `default store` | Открывается `/lrs-admin/store/1/client` («Клиенты хранилища»), вкладки: Клиенты хранилища, Statements, States, Activity profiles, Agents; в боковом меню хранилище подсвечено |
| 3 | Сравнить «Количество statements» из шага 1 с числом записей на вкладке Statements (сумма по страницам / `recordsTotal` из `POST …/statement/search`) | Числа совпадают |

### TC-LRS-007 Клиенты хранилища: xAPI-endpoint и Launch-ссылка
- Автотест: tests/ui/lrs/test_lrs_stores.py::TestLrsStores::test_store_clients_launch_link
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS, у `default store` есть клиент
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть «Клиенты хранилища» | Таблица: Логин, Пароль, Дата создания, Launch, Действия (Предпросмотр, Редактировать, Удалить); кнопка «Добавить Клиент» |
| 2 | Прочитать `href` ссылки «Launch» | Содержит `endpoint=https://lrs-<стенд>/xAPI` и `auth=Basic <base64 логин:пароль>` — base64 совпадает с логином/паролем из строки |
| 3 | `GET https://lrs-<стенд>/xAPI/about` с этим Basic | Ответ 200, JSON с `version` (xAPI 1.0.x) |

### TC-LRS-008 Вкладка Statements: таблица, предпросмотр, ссылка в карточку пользователя LMS
- Автотест: tests/ui/lrs/test_lrs_statements.py::TestLrsStatements::test_statements_table_preview_and_agent_link
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS; в `default store` есть хотя бы один statement
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть `/lrs-admin/store/1/statement` | Колонки Agent, Verb, Activity, Дата создания statement-а, Действия; записи отсортированы по дате убыванием; кнопки «Скачать архив», «Генерация отчета», «Сбросить»; пагинация и «записей на странице» |
| 2 | Нажать «Предпросмотр» у первой записи | Страница `/statement/{id}/show`: поля Agent, Verb, Activity, Дата, Registration, Voided, Payload и JSON statement'а: `actor.account.name` = Agent из таблицы, `actor.account.homePage` = `https://portal-<стенд>/accounts/userid`, `verb.id` = `http://adlnet.gov/expapi/verbs/<verb>`; кнопка «Вернуться к списку» |
| 3 | В таблице нажать на значение Agent | Открывается карточка пользователя LMS `https://portal-<стенд>/admin/users/{agent}`, id в URL = Agent |

### TC-LRS-009 Фильтры Statements: Agent ID, Verb, Date
- Автотест: tests/ui/lrs/test_lrs_statements.py::TestLrsStatements::test_statements_filters
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS; известен agent со statements (например из TC-LRS-013)
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Фильтр «Agent ID» → выбрать/ввести id агента | В таблице только строки этого Agent; URL получает `agent_id=…`; `POST …/statement/search` возвращает `recordsFiltered` ≤ `recordsTotal` |
| 2 | Фильтр «Verb» → `passed` | Только строки с verb `passed` |
| 3 | Фильтр «Date» → сегодняшняя дата / интервал | Только записи с датой в интервале |
| 4 | «Сбросить» | Фильтры сняты, URL без параметров, число строк как до фильтрации |

### TC-LRS-010 Вкладка Agents: ссылки Statements / State по агенту и переход в карточку LMS
- Автотест: tests/ui/lrs/test_lrs_statements.py::TestLrsStatements::test_agents_tab_links
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: admin в OpenLRS; есть агент со statements
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть `/lrs-admin/store/1/agent` | Колонка `account_name` (id пользователя LMS) и кнопки Statements, State у каждой строки |
| 2 | Нажать Statements у агента | Открывается `/statement?agent_id=<id>`, в таблице только его записи |
| 3 | Нажать `account_name` | Карточка пользователя LMS `/admin/users/<id>` |

### TC-LRS-011 Генерация отчёта из Statements → отчёт в LMS «Отчёты»
- Автотест: tests/ui/lrs/test_lrs_report.py::TestLrsReport::test_generate_report_appears_in_lms_exports
- Приоритет: high   Тип: e2e   Роли: admin
- Предусловия: admin в OpenLRS (SSO); отчёты, созданные тестом, удаляются в teardown через `DELETE /api/v1/exports/mass-delete`
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | На вкладке Statements (при необходимости — с фильтром Agent ID) нажать «Генерация отчета» | Запрос `…/store/1/statement/report_generation`; сообщение об успешной постановке; ошибок нет |
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
| 1 | Нажать «Скачать архив» | Запрос `…/store/1/archive/download`, браузер получает файл-архив (zip), размер > 0 |

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
| 1 | Открыть `/lrs-admin/store/1/state` | Колонки Agent, State key, Activity IRI, Registration, Действия (Предпросмотр, Удалить); фильтры по agent/stateKey/activityIri/registration |
| 2 | Нажать на Agent | Карточка пользователя LMS `/admin/users/<id>` |
| 3 | «Предпросмотр» | Страница `/state/{id}/show` с содержимым state (JSON) |

### TC-LRS-015 Форма входа OpenLRS не принимает учётку LMS (документированное поведение)
- Автотест: tests/ui/lrs/test_lrs_navigation.py::TestLrsNavigation::test_lrs_login_form_rejects_lms_credentials
- Приоритет: low   Тип: ui   Роли: admin
- Предусловия: чистый контекст
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | На `/lrs-admin/login` ввести email/пароль админа LMS, «Войти» | Остаёмся на форме входа (OpenLRS хранит своих пользователей отдельно, штатный вход — SSO). Если форма впускает — поведение изменилось, кейс пересмотреть |
