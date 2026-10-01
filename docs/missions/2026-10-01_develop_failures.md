# Миссия: правки по упавшим тестам на develop

Записано 01.10.2026 по решению владельца. Цель — зелёный полный прогон на develop: каждый упавший или
сломанный тест либо починен, либо честно помечен как известный дефект продукта, либо выключен с причиной.

## База

Полный прогон test_hub #52 на develop (01.10.2026, метка `develop_full_2026-10-01`) — список упавших и
сломанных тестов в конце этого файла (раздел «Список»). Отчёт прогона: `http://127.0.0.1:8700/api/runs/52/report`
и `/api/runs/52/tests` (логин qa/qa, GET `/api/runs/52/tests/<nodeid>/log` даёт вывод конкретного теста).
Allure-вложения прогона — `workspace/runs/52/` в репозитории test_hub (только чтение). Для сравнения: прогоны
#39 (28.09, all) и #43 (29.09, api) падали на `test_sync_user` (CAS), онбординге, `test_constructor/test_10`,
статье базы знаний, `test_admin_check_cas_user`, `test_create_schedule_item_no_teacher`.

## Правила (обязательны)

- Стенд только `--env develop`, `HEADLESS=1`. Stage/prod/k8s не трогать.
- Учётки и токены только из `.env` через `config/environments.py`; значения не писать в код, логи, коммиты.
- Запускать **только свои тесты** (`pytest <nodeid> --env develop`), не полный прогон. Перед правкой
  воспроизвести падение, после правки прогнать тест 2 раза подряд.
- Чинить тест, а не подгонять assert под факт. Для каждого падения сначала классифицировать:
  1. **ошибка теста** (устаревший селектор, гонка, неверное ожидание, зависимость от данных) → починить;
  2. **дефект продукта** (поведение стенда противоречит требованию) → `pytest.mark.xfail(strict=False,
     reason="VSHGU2-NNNN или описание: …")` + запись в реестр test_hub через `docs/xfail_registry`-механику
     проекта (посмотреть, как оформлены существующие xfail в `tests/` и в реестре test_hub, 61 запись);
     в отчёте — кандидат в дефект с шагами и ожидаемым/фактическим;
  3. **данные стенда** (нет «Индивидуального обучения», выключен баннер, онбординг уже пройден у учётки)
     → тест должен сам готовить предусловие через API или делать `skip` с понятной причиной, а не падать.
- Флаки: если тест падает не каждый раз — найти причину (ожидание, порядок, общие данные), не добавлять
  `reruns` как единственное решение.
- Не менять page objects и помощники шире, чем нужно для починки; если правка затрагивает другие тесты —
  прогнать и их.
- Коммиты небольшие, по одному на область, на русском: «fix(<область>): <что и почему>».

## Что получить

1. Таблица в `docs/reports/2026-10-01_develop_failures.md`: тест → причина (1/2/3) → что сделано →
   статус после правки (2 прогона). Отдельно — список кандидатов в дефекты для владельца.
2. По завершении всех задач — один контрольный прогон только списка из «Списка» (не всего проекта):
   `pytest <nodeid1> <nodeid2> … --env develop` — все зелёные или xfail/skip с причиной.
3. README не трогать, кроме случая, когда добавлены новые env-переменные.

## Список (упавшие и сломанные тесты прогона #52)

Итог прогона #52 (завершён 01.10.2026 16:29): passed 233, failed 4, broken 5, skipped 200, xfailed 23. Упавшие/сломанные (уникальные nodeid; один тест с повторным запуском считается один раз):

- broken: `tests/ui/courses/tincan/knowledge_base/test_knowledge_base_flow.py::TestKnowledgeBaseFlow::test_create_course_and_view_in_ui`
- broken: `tests/ui/knowledge_base/user_achievements/test_user_gets_achievement_by_material.py::TestUserGetsAchievementByMaterial::test_user_gets_achievement_by_material[article]`
- broken: `tests/ui/test_constructor/test_10_admin_sees_progress_without_additional_questions_in_statistics.py::TestAdminSeesProgressWithoutAdditionalQuestionsInStatistics::test_admin_sees_progress_without_additional_questions_in_statistics`
- failed: `tests/api/cas/test_external_cas_sync_users_api.py::TestExternalCasSyncUsersAPI::test_sync_user`
- failed: `tests/ui/cas/admin/test_admin_cas_users.py::TestAdminCasUsers::test_admin_check_cas_user`
- failed: `tests/ui/knowledge_base/test_create_article_and_verify_in_user_ui.py::TestCreateArticleAndVerifyInUserUi::test_create_article_and_verify_in_user_ui`

