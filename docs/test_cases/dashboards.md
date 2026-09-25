# Тест-кейсы: dashboards

| Параметр | Значение |
|---|---|
| Область | tests/ui/dashboards |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-DASHBOARDS-001 UI: Администратор проверяет строки дашбордов программ и курсов
<!-- steps-hash: ecfadac480be -->
- Автотест: tests/ui/dashboards/test_admin_checks_program_and_course_dashboards.py::TestAdminChecksProgramAndCourseDashboards::test_admin_checks_program_and_course_dashboards
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть дашборд статистики программ и проверить строку программы | — |
| 2 | 2. Открыть дашборд статистики курсов и проверить строку курса | — |
