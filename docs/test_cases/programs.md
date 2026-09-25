# Тест-кейсы: programs

| Параметр | Значение |
|---|---|
| Область | tests/api/programs |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-PROGRAMS-001 Назначение активности пользователю
<!-- steps-hash: 201110c86ad5 -->
- Автотест: tests/api/programs/test_assign_activities_api.py::TestAssignActivitiesAPI::test_assign_activity_to_user
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Создать LPD и пользователя → назначить активность. Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать LPD | — |
| 2 | 2. Создать пользователя | — |
| 3 | 3. Назначить активность пользователю | — |

### TC-PROGRAMS-002 Открепление активности от пользователя
<!-- steps-hash: ba52409c07dd -->
- Автотест: tests/api/programs/test_assign_activities_api.py::TestAssignActivitiesAPI::test_detach_activity_from_user
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: Назначить и открепить активность. Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать LPD и пользователя | — |
| 2 | 2. Назначить активность | — |
| 3 | 3. Открепить активность | — |

### TC-PROGRAMS-003 Назначение пользователя в поток
<!-- steps-hash: 64c30bde7b01 -->
- Автотест: tests/api/programs/test_assignments_api.py::TestAssignmentsAPI::test_assign_user_to_stream
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Назначить пользователя в поток.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Назначить пользователя | — |
| 2 | 2. Проверить данные | — |

### TC-PROGRAMS-004 Повторное назначение того же пользователя
<!-- steps-hash: b925b8f13db3 -->
- Автотест: tests/api/programs/test_assignments_api.py::TestAssignmentsAPI::test_assign_user_twice
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: Назначить пользователя дважды — система должна обработать без ошибок.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать пользователя и поток | — |
| 2 | 2. Назначить первый раз | — |
| 3 | 3. Назначить повторно | — |

### TC-PROGRAMS-005 Создание модуля с валидными данными
<!-- steps-hash: 86f41fcd1819 -->
- Автотест: tests/api/programs/test_create_module.py::TestCreateModuleAPI::test_create_module_success
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Позитивный кейс: создание модуля с корректными данными.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать модуль через API | — |
| 2 | 2. Проверить ID модуля | — |
| 3 | 3. Проверить название | — |
| 4 | 4. Проверить привязку к программе и потоку | — |

### TC-PROGRAMS-006 Создание модуля с датами вне диапазона потока
<!-- steps-hash: edf664a65c2d -->
- Автотест: tests/api/programs/test_create_module.py::TestCreateModuleAPI::test_create_module_dates_outside_stream
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Модуль с датами, выходящими за даты потока → 422.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу | — |
| 2 | 2. Создать поток с датами 2026-06-01 → 2026-06-30 | — |
| 3 | 3. Попытаться создать модуль с датами РАНЬШЕ потока | — |
| 4 | 4. Попытаться создать модуль с датами ПОЗЖЕ потока | — |

### TC-PROGRAMS-007 Создание модуля без региона при must_use_module_region=True
<!-- steps-hash: f6903742ef6d -->
- Автотест: tests/api/programs/test_create_module.py::TestCreateModuleAPI::test_create_module_without_region
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Обновление модуля с must_use_module_region=True, но без region → 422.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу → поток → модуль | — |
| 2 | 2. Обновить модуль: must_use_module_region=True, но без region | — |

### TC-PROGRAMS-008 Создание модуля без названия
<!-- steps-hash: 09b174db4c17 -->
- Автотест: tests/api/programs/test_create_module.py::TestCreateModuleAPI::test_create_module_without_name
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Попытка создать модуль без названия → 422.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу → поток | — |
| 2 | 2. Попытаться создать модуль без названия | — |

### TC-PROGRAMS-009 Создание модуля без даты начала
<!-- steps-hash: 61c675e22d62 -->
- Автотест: tests/api/programs/test_create_module.py::TestCreateModuleAPI::test_create_module_without_date_from
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Попытка создать модуль без date_from → 422.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу → поток | — |
| 2 | 2. Попытаться создать модуль без date_from | — |

### TC-PROGRAMS-010 Создание программы с валидными данными
<!-- steps-hash: 2447dd7503ce -->
- Автотест: tests/api/programs/test_create_program_api.py::TestCreateProgramAPI::test_create_program_success
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Позитивный кейс: создание программы с корректными данными.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу через API | — |
| 2 | 2. Проверить ID программы | — |
| 3 | 3. Проверить название | — |
| 4 | 4. Проверить статус активности | — |

### TC-PROGRAMS-011 Создание программы с кастомным названием и цветом
<!-- steps-hash: a4faa0bea564 -->
- Автотест: tests/api/programs/test_create_program_api.py::TestCreateProgramAPI::test_create_program_custom
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Создание программы с заданными параметрами.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать программу с кастомными данными | — |
| 2 | Проверить название | — |
| 3 | Проверить цвета | — |

### TC-PROGRAMS-012 Создание неактивной программы
<!-- steps-hash: 6c6b82580fd1 -->
- Автотест: tests/api/programs/test_create_program_api.py::TestCreateProgramAPI::test_create_program_inactive
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Создание программы с is_active = False.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать неактивную программу | — |
| 2 | Проверить статус | — |

### TC-PROGRAMS-013 Массовое удаление программ
<!-- steps-hash: ddf44f0491aa -->
- Автотест: tests/api/programs/test_create_program_api.py::TestCreateProgramAPI::test_mass_delete_programs
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Создать 3 программы, удалить массово, проверить что удалены.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать 3 программы | — |
| 2 | 2. Массово удалить через /programs/mass-delete | — |
| 3 | 3. Проверить, что программы реально удалены | — |

### TC-PROGRAMS-014 Создание программы без названия
<!-- steps-hash: 15adb2665c49 -->
- Автотест: tests/api/programs/test_create_program_api.py::TestCreateProgramAPI::test_create_program_without_name
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Попытка создать программу с пустым названием (name = None).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Отправить запрос без name | — |

### TC-PROGRAMS-015 Создание программы с пустым payload
<!-- steps-hash: 109e01989fd3 -->
- Автотест: tests/api/programs/test_create_program_api.py::TestCreateProgramAPI::test_create_program_empty_payload
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Попытка создать программу вообще без атрибутов.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Отправить запрос с пустыми attributes | — |

### TC-PROGRAMS-016 Создание элемента расписания с валидными данными
<!-- steps-hash: 07aa29e80c6e -->
- Автотест: tests/api/programs/test_create_schedule_item_api.py::TestCreateScheduleItemAPI::test_create_schedule_item_success
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Позитивный кейс: создание элемента расписания.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать элемент расписания | — |
| 2 | 2. Проверить ID | — |
| 3 | 3. Проверить название | — |
| 4 | 4. Проверить регион | — |

### TC-PROGRAMS-017 Создание элемента расписания без учителей
<!-- steps-hash: f98381f2d568 -->
- Автотест: tests/api/programs/test_create_schedule_item_api.py::TestCreateScheduleItemAPI::test_create_schedule_item_no_teacher
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Создание элемента расписания с пустым teacher_ids.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать элемент без учителей | — |
| 2 | Проверить, что создан | — |

### TC-PROGRAMS-018 Создание элемента расписания с несколькими учителями
<!-- steps-hash: 875f00cf7c45 -->
- Автотест: tests/api/programs/test_create_schedule_item_api.py::TestCreateScheduleItemAPI::test_create_schedule_item_multiple_teachers
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Создание элемента расписания с teacher_ids=[4, 1].
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать элемент с двумя учителями | — |
| 2 | Проверить, что создан | — |

### TC-PROGRAMS-019 Создание элемента расписания без названия
<!-- steps-hash: 3b3a9fc4e017 -->
- Автотест: tests/api/programs/test_create_schedule_item_api.py::TestCreateScheduleItemAPI::test_create_schedule_item_without_name
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Попытка создать элемент расписания без названия → 422.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу → поток → модуль | — |
| 2 | 2. Попытаться создать элемент без названия | — |

### TC-PROGRAMS-020 Создание элемента расписания без региона
<!-- steps-hash: d31ecf3d2dce -->
- Автотест: tests/api/programs/test_create_schedule_item_api.py::TestCreateScheduleItemAPI::test_create_schedule_item_without_region
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Попытка создать элемент расписания без region → 422.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу → поток → модуль | — |
| 2 | 2. Попытаться создать элемент без region | — |

### TC-PROGRAMS-021 Создание элемента расписания с датами вне модуля
<!-- steps-hash: 3d97eae90186 -->
- Автотест: tests/api/programs/test_create_schedule_item_api.py::TestCreateScheduleItemAPI::test_create_schedule_item_dates_outside_module
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Элемент с датами, выходящими за даты модуля → 422.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу | — |
| 2 | 2. Создать поток с датами 2026-06-01 → 2026-06-30 | — |
| 3 | 3. Создать модуль с датами 2026-06-01 → 2026-06-30 | — |
| 4 | 4. Попытаться создать элемент с датами РАНЬШЕ модуля | — |
| 5 | 5. Попытаться создать элемент с датами ПОЗЖЕ модуля | — |

### TC-PROGRAMS-022 Создание потока с валидными данными
<!-- steps-hash: 7210c21e6486 -->
- Автотест: tests/api/programs/test_create_stream_api.py::TestCreateStreamAPI::test_create_stream_success
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Позитивный кейс: создание потока с корректными данными.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать поток через API | — |
| 2 | 2. Проверить ID потока | — |
| 3 | 3. Проверить название | — |
| 4 | 4. Проверить program_id | — |

### TC-PROGRAMS-023 Создание потока с кастомными параметрами
<!-- steps-hash: 075f2361de17 -->
- Автотест: tests/api/programs/test_create_stream_api.py::TestCreateStreamAPI::test_create_stream_custom
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Создание потока с заданным названием и локацией.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать поток с кастомными данными | — |
| 2 | Проверить название | — |
| 3 | Проверить атрибуты | — |

### TC-PROGRAMS-024 Создание потока без названия
<!-- steps-hash: fc4757c4c6f2 -->
- Автотест: tests/api/programs/test_create_stream_api.py::TestCreateStreamAPI::test_create_stream_without_name
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Попытка создать поток с пустым названием.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу | — |
| 2 | 2. Попытаться создать поток без названия | — |

### TC-PROGRAMS-025 Создание потока без даты начала
<!-- steps-hash: c2902d27aa6a -->
- Автотест: tests/api/programs/test_create_stream_api.py::TestCreateStreamAPI::test_create_stream_without_date_from
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Попытка создать поток без date_from.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу | — |
| 2 | 2. Попытаться создать поток без date_from | — |

### TC-PROGRAMS-026 Создание потока без academic_directors
<!-- steps-hash: d010d0d70c59 -->
- Автотест: tests/api/programs/test_create_stream_api.py::TestCreateStreamAPI::test_create_stream_without_academic_directors
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Попытка создать поток с пустым списком academic_directors.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу | — |
| 2 | 2. Попытаться создать поток без academic_directors | — |

### TC-PROGRAMS-027 Создание потока для несуществующей программы
<!-- steps-hash: 184c605a4f4d -->
- Автотест: tests/api/programs/test_create_stream_api.py::TestCreateStreamAPI::test_create_stream_invalid_program
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Попытка создать поток для несуществующей программы.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Попытаться создать поток с несуществующим program_id | — |

### TC-PROGRAMS-028 E2E: Полный цикл с назначением пользователя
<!-- steps-hash: 675b35cfc6fe -->
- Автотест: tests/api/programs/test_e2e_program_flow.py::TestE2EProgramFlow::test_full_e2e_flow
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Полный цикл: программа, поток, модуль, schedule item, АОС, пользователь, назначение, активация.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу | — |
| 2 | 2. Создать поток | — |
| 3 | 3. Создать модуль | — |
| 4 | 4. Создать элемент расписания | — |
| 5 | 5. Создать АОС | — |
| 6 | 6. Создать пользователя | — |
| 7 | 7. Назначить пользователя в поток | — |
| 8 | 8. Активировать АОС | — |
| 9 | 9. Проверить АОС | — |
| 10 | 10. Очистка | — |
