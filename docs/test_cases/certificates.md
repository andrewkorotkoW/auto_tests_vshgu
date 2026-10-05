# Тест-кейсы: certificates

| Параметр | Значение |
|---|---|
| Область | tests/api/certificates/assign/activity, tests/api/certificates/assign/program, tests/api/certificates/create/activity, tests/api/certificates/create/program |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-CERTIFICATES-001 E2E Develop: Сертификат → ДЗ → назначение на ДЗ → пользователь → инд. трек
<!-- steps-hash: 103d1db1ed18 -->
- Автотест: tests/api/certificates/assign/activity/test_assign_certificate_to_activity_and_user.py::TestAssignCertificateToActivity::test_assign_certificate_to_homework_and_user
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать шаблон сертификата (activity) | — |
| 2 | 2. Создать домашнее задание | — |
| 3 | 3. Назначить сертификат на домашнее задание | — |
| 4 | 4. Создать пользователя | — |
| 5 | 5. Назначить ДЗ пользователю через инд. трек | — |
| 6 | 6. Проверить, что ДЗ доступно пользователю | — |
| 7 | Очистка: удалить ДЗ | — |

### TC-CERTIFICATES-002 E2E Develop: Создать программу/поток/модуль → создать шаблон → назначить
<!-- steps-hash: 964ab8b5d2f4 -->
- Автотест: tests/api/certificates/assign/program/test_assign_template.py::TestAssignTemplate::test_assign_template_to_program
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу, поток, модуль | — |
| 2 | 2. Загрузить PDF и создать шаблон сертификата | — |
| 3 | 3. Назначить шаблон на программу | — |

### TC-CERTIFICATES-003 API Develop: Создать шаблон сертификата для активности
<!-- steps-hash: 2aface1702ac -->
- Автотест: tests/api/certificates/create/activity/test_create_template_activity.py::TestCreateActivityTemplate::test_create_activity_template
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Загрузить файл сертификата | — |
| 2 | 2. Создать шаблон активности | — |

### TC-CERTIFICATES-004 API Develop: Создать шаблон сертификата для программы
<!-- steps-hash: f8884cb19192 -->
- Автотест: tests/api/certificates/create/program/test_create_template_program.py::TestCreateProgramTemplate::test_create_program_template
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Загрузить файл сертификата | — |
| 2 | 2. Создать шаблон программы | — |
