# Миссия: e2e-набор слушателя — маркер `e2e`, структура папок, кейсы (14.10.2026)

Цель владельца: иметь в репозитории один набор сквозных сценариев слушателя, который
запускается одной командой (`pytest -m e2e`, в test_hub — прогон по маркеру `e2e`) на
develop и k8s, и перечень того, чего в этом наборе ещё нет.

Правила как в `docs/plans/2026-10-14_lrs_mission.md`: **агентам прогоны на стендах
запрещены** — только `pytest --collect-only` и юнит-проверки; логику существующих тестов
не менять (только маркеры, перенос файлов, документация); пуш не делать.

## Контекст

- `tests/e2e/` сегодня — это бывший `tests/stage`: сквозные сценарии ЛПД (`api/`, `ui/`,
  `conftest.py` с фикстурами `individual_lpd`/`program_lpd`), привязанные к stage
  (`@pytest.mark.env("stage")`). Stage сейчас живёт на ветке ЛПД/БУК, поэтому эти
  сценарии **не входят** в e2e-набор develop/k8s — они стендовые. Настоящие e2e в
  `tests/e2e/` сейчас только `tests/e2e/lrs/`.
- Маркер `e2e` уже объявлен в `pytest.ini` («Сквозные сценарии (несколько систем)»),
  стоит на 2 тестах LRS (`tests/ui/lrs/test_lrs_report.py`, `tests/e2e/lrs/…`).
- CI: `.gitlab-ci.yml` job `tests:develop:ui` гоняет `tests/ui tests/e2e`
  (`docs/DEVOPS.md:132`), README описывает `tests/e2e` в строках ~80, ~116, ~133.
- Список сценариев слушателя — от владельца (14.10.2026), ниже разложен на «уже есть» и
  «надо написать».

## Часть 1. Структура: ЛПД-сценарии отдельно от e2e

1. `git mv tests/e2e/api tests/stage_lpd/api`, `git mv tests/e2e/ui tests/stage_lpd/ui`,
   `git mv tests/e2e/conftest.py tests/stage_lpd/conftest.py`, добавить `tests/stage_lpd/__init__.py`.
   `tests/e2e/` остаётся для сквозных сценариев (сейчас `lrs/`), `tests/e2e/__init__.py` сохранить.
2. Обновить все упоминания: `.gitlab-ci.yml` (`PYTEST_ARGS: "tests/ui tests/e2e"` →
   `"tests/ui tests/e2e tests/stage_lpd"`, чтобы набор CI не изменился), `docs/DEVOPS.md`,
   README (структура `tests/`, абзац про «переименованный бывший tests/stage», примеры
   `@pytest.mark.env("stage")`), `pytest.ini` (описание маркера `lrs`, если упоминает пути).
3. Проверка: `pytest --collect-only -q tests/stage_lpd` и `pytest --collect-only -q tests/e2e`
   собираются, число тестов в `tests/stage_lpd` = числу, что было в `tests/e2e/{api,ui}`.

## Часть 2. Маркер `e2e` на существующие сквозные сценарии слушателя

Поставить `@pytest.mark.e2e` (рядом с существующими маркерами, логику не трогать) на:

| № | Сценарий из списка владельца | Тест |
|---|---|---|
| 1 | Вход → онбординг (модалка согласия, тур, cookie) | `tests/ui/users/test_user_cookie_banner.py` |
| 2 | Программа → поток → модуль (админ) | `tests/ui/practical_tasks/test_add_practical_task_to_schedule.py` |
| 3 | Курс (поток) | `tests/ui/courses/tincan/stream/test_user_tincan_flow.py` |
| 4 | Тест (поток) | `tests/ui/tests/stream/test_user_test_stream_flow.py` |
| 5 | ПЗ: слушатель сдаёт | `tests/ui/practical_tasks/test_complete_practical_task.py` |
| 6 | ПЗ: проверяющий оценивает | `tests/ui/practical_tasks/test_review_practical_task.py` |
| 7 | Групповые ПЗ | `tests/ui/practical_tasks/groups/test_group_practical_task_flow.py` |
| 8 | АОС (авторизованный) | `tests/ui/aos/user/test_user_aos_flow.py` |
| 9 | АОС по публичной ссылке без авторизации | `tests/ui/aos/user/test_aos_public_link.py` |
| 10 | Игровая сессия | `tests/ui/game_session/user/test_activity_launch_flow.py` |
| 11 | Уведомления | `tests/ui/notifications/user/test_user_sees_notification.py` |
| 12 | Инд. трек: курс | `tests/ui/courses/tincan/individual/test_user_tincan_individual_flow.py` (оба теста файла) |
| 13 | Инд. трек: опрос | `tests/ui/polls/individual/test_poll_flow.py` |
| 14 | Инд. трек: ПЗ | `tests/ui/practical_tasks/personal_assignment/test_complete_and_review_personal_assignment.py` |
| 15 | Курс из БЗ, назначенный на инд. трек | `tests/ui/courses/tincan/knowledge_base/test_knowledge_base_flow.py` |
| 16 | Практическое задание в инд. треке через раздел `homework` (в продукте это тоже ПЗ, «ДЗ» — только имя в коде) | `tests/ui/homework/individual/test_ui_homework_flow.py` |
| 17 | Техподдержка: слушатель создаёт обращение и видит его в списке | `tests/ui/tickets/user/test_user_creates_ticket.py` |
| 18 | Замыкание статистикой: после прохождения курса статус «пройдено» и 100 % видны админу в статистике обучения | `tests/ui/learning_statistics/test_courses_table_progress.py::TestCoursesTableProgress::test_status_passed_updates_after_change_state` — **только этот тест файла** |

Дополнение владельца (14.10 вечер): пункты 17–18 добавлены по его подтверждению; «ДЗ» в
пункте 16 — это практическое задание, в кейсах так и называть.

Уже помечены: `tests/ui/lrs/test_lrs_report.py::…::test_generate_report_appears_in_lms_exports`,
`tests/e2e/lrs/test_statement_after_test_pass.py`. Проверка: `pytest --collect-only -q -m e2e`
→ 21 тест (18 строк выше = 19 тестов + 2 LRS).

Маркер `smoke`/`develop`/`xfail` у этих тестов не снимать и не добавлять.

## Часть 3. Кейсы `docs/test_cases/e2e.md`

По шаблону `docs/test_cases/TEMPLATE.md` и образцу `docs/test_cases/lrs.md`.

**Важно: `docs/test_cases/e2e.md` уже существует** (18 кейсов TC-E2E-001…018, сгенерированы
`tools/test_cases/generate.py`): часть на `tests/api/e2e/` (API-цепочки «программа → поток →
модуль → контент → назначение», они остаются e2e-областью), часть на `tests/e2e/api|ui`
(ЛПД на stage). Сделать так:
- кейсы с `- Автотест: tests/e2e/api/…` и `tests/e2e/ui/…` перенести в новый файл
  `docs/test_cases/stage_lpd.md` (шапка «Область: tests/stage_lpd», стенд stage), в строках
  «Автотест:» заменить путь на `tests/stage_lpd/…`; их номера TC-E2E-NNN сохранить, чтобы не
  ломать импорт в test_hub;
- в `e2e.md` оставить кейсы на `tests/api/e2e/`, нумерацию не менять, новые кейсы продолжать
  с **TC-E2E-019**.
- **Новые кейсы по существующим тестам** — по одному на тест из таблицы части 2 (№ 12 даёт два
  кейса) плюс два LRS-теста с маркером (всего 21): шаги и ожидаемые результаты переписать из
  `allure.step` самого теста (не выдумывать), строка `- Автотест: <nodeid>`, роли, тип `e2e`,
  стенд `develop|k8s` (LRS — только k8s).
- **Черновики без автотеста** (следующие номера после них), с пометкой «ждёт автотеста»:
  1. Очное мероприятие в потоке — **разведка сделана**, шаги брать из
     `docs/e2e/offline_events_recon.md` (раздел «Что положить в кейсы», TC-E2E-020 там = этот кейс):
     мероприятие `webinar` через `schedule-items`, модуль с регионом, назначение слушателя,
     отметка `is_registered=true`, зелёная галочка на карточке во вкладке «Расписание».
  2. Очное мероприятие в инд. треке — **разведка сделана**, там же: `POST /users/content/offline`,
     «Индивидуальное обучение» → «Расписание», teardown detach + `DELETE /tests`.
  3. Опрос в потоке + неавторизованная попытка: опрос назначен на модуль потока, слушатель
     проходит; ссылка на плеер без сессии → редирект на `/auth`, прогресса нет (ждёт разведки).
  4. Сертификат слушателя: шаблон сертификата программы (`tests/api/certificates/`),
     слушатель завершает программу, в кабинете появляется сертификат, файл скачивается (ждёт разведки).
  5. Достижение слушателя: достижение «Количество материалов = 1» (`tests/ui/knowledge_base/
     test_create_achievement.py`), слушатель открывает материал БЗ, в его профиле появляется
     достижение (сейчас есть только проверка глазами админа —
     `admin_statistics/test_admin_sees_user_achievement_history.py`) (ждёт разведки).
  6. Повторный вход без онбординга: слушатель, уже прошедший модалку согласия, тур и
     cookie-баннер, выходит и входит снова — ничего из этого не повторяется, сразу кабинет
     (ловит регрессии `dismiss_popups`; дешёвый, писать первым в следующей миссии).

Импорт кейсов в test_hub делает владелец вручную (`POST /api/projects/VSHGU/testcases/import`).

## Часть 4. Документация и отчёт

- README: раздел «e2e-набор слушателя» — что входит, как запускать (`pytest -m e2e --env k8s -n 0`,
  в test_hub — маркер `e2e`), чем отличается от `tests/stage_lpd`, список того, чего нет (18–22).
- `docs/reports/2026-10-14_e2e_markers.md`: что перенесено, что помечено, вывод
  `pytest --collect-only -q -m e2e` и `… tests/stage_lpd`.

## Не делать

- Не запускать тесты на стендах (develop лежит, k8s — только владелец через test_hub).
- Не менять логику тестов, фикстур и page objects; не трогать `tests/ui/lrs` (правятся отдельно).
- Не писать автотесты для 18–22 — сначала разведка на k8s владельцем, потом отдельная миссия.
