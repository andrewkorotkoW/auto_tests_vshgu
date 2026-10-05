# Тест-кейсы: create_activity

| Параметр | Значение |
|---|---|
| Область | tests/api/create_activity/courses/scorm, tests/api/create_activity/courses/tincan, tests/api/create_activity/external_content, tests/api/create_activity/homeworks, tests/api/create_activity/lpd |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-CREATE_ACTIVITY-001 API Develop: Создать SCORM 2004 курс с обложкой и архивом
<!-- steps-hash: 180d8251c6ca -->
- Автотест: tests/api/create_activity/courses/scorm/test_create_scorm_2004.py::TestCreateScorm2004::test_create_scorm_2004
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Загрузить обложку | — |
| 2 | 2. Загрузить архив SCORM | — |
| 3 | 3. Создать SCORM-курс | — |
| 4 | 4. Очистка (удалить курс) | — |

### TC-CREATE_ACTIVITY-002 E2E: Программа → Поток → Модуль → Пользователь → Курс Tincan → Назначение
<!-- steps-hash: a34352199f89 -->
- Автотест: tests/api/create_activity/courses/tincan/test_e2e_create_tincan_api.py::TestE2ETincan::test_e2e_tincan_full_flow
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу | — |
| 2 | 2. Создать поток | — |
| 3 | 3. Создать модуль | — |
| 4 | 4. Создать пользователя | — |
| 5 | 5. Назначить пользователя на поток | — |
| 6 | 6. Загрузить файлы и создать курс | — |
| 7 | 7. Назначить курс в модуль | — |
| 8 | 8. Удалить курс | — |
| 9 | 9. Очистка | — |

### TC-CREATE_ACTIVITY-003 Создание курса Tincan
<!-- steps-hash: 0c7b2f0c81fa -->
- Автотест: tests/api/create_activity/courses/tincan/test_tincan_api.py::TestTincanAPI::test_create_tincan
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать курс Tincan | — |

### TC-CREATE_ACTIVITY-004 Создание Tincan без названия
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/create_activity/courses/tincan/test_tincan_api.py::TestTincanAPI::test_create_tincan_without_name
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-CREATE_ACTIVITY-005 Загрузка архива курса
<!-- steps-hash: 9f8a14b43781 -->
- Автотест: tests/api/create_activity/courses/tincan/test_tincan_api.py::TestTincanAPI::test_upload_archive
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Загрузить архив | — |

### TC-CREATE_ACTIVITY-006 Загрузка обложки
<!-- steps-hash: 39c9c1b95a8c -->
- Автотест: tests/api/create_activity/courses/tincan/test_tincan_api.py::TestTincanAPI::test_upload_cover
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Загрузить обложку | — |

### TC-CREATE_ACTIVITY-007 Загрузка доп файла
<!-- steps-hash: 2a64ed9d9e99 -->
- Автотест: tests/api/create_activity/courses/tincan/test_tincan_api.py::TestTincanAPI::test_upload_sub_file
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Загрузить доп файл | — |

### TC-CREATE_ACTIVITY-008 Массовое удаление Tincan
<!-- steps-hash: 2effc5cc6ed9 -->
- Автотест: tests/api/create_activity/courses/tincan/test_tincan_api.py::TestTincanAPI::test_mass_delete_tincan
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать курс | — |
| 2 | 2. Массово удалить | — |

### TC-CREATE_ACTIVITY-009 Создание, активация акивити игровой сессии
<!-- steps-hash: 52bb877533e5 -->
- Автотест: tests/api/create_activity/external_content/test_external_content_api.py::TestExternalContentAPI::test_external_content_full_flow
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Загрузить обложку | — |
| 2 | 2. Создать Активити | — |
| 3 | 3. Активировать активити | — |
| 4 | 4. Активировать игровую сессию | — |
| 5 | 4.5. Повторная активация — 208 | — |
| 6 | 5. Удалить внешний контент | — |

### TC-CREATE_ACTIVITY-010 API Develop: Создать практическое задание с обложкой и преподавателем
<!-- steps-hash: cc9e5fb9f7bd -->
- Автотест: tests/api/create_activity/homeworks/test_create_homework_five_point.py::TestCreateHomework::test_create_homework_full
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Загрузить обложку | — |
| 2 | 2. Найти или создать преподавателя с фамилией на 'ов' | — |
| 3 | 3. Создать практическое задание | — |

### TC-CREATE_ACTIVITY-011 API Develop: Создать практическое задание (зачёт/незачёт) с обложкой и преподавателем
<!-- steps-hash: 4fb571790305 -->
- Автотест: tests/api/create_activity/homeworks/test_create_homework_pass_fail.py::TestCreateHomeworkPassFail::test_create_homework_pass_fail
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Загрузить обложку | — |
| 2 | 2. Найти или создать преподавателя с фамилией на 'ов' | — |
| 3 | 3. Создать практическое задание (зачёт/незачёт) | — |

### TC-CREATE_ACTIVITY-012 API Develop: Создать практическое задание (10-балльное) с обложкой и преподавателем
<!-- steps-hash: ea74ac35c10c -->
- Автотест: tests/api/create_activity/homeworks/test_create_homework_ten_point.py::TestCreateHomeworkTenPoint::test_create_homework_ten_point
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Загрузить обложку | — |
| 2 | 2. Найти или создать преподавателя с фамилией на 'ов' | — |
| 3 | 3. Создать 10‑балльное практическое задание | — |

### TC-CREATE_ACTIVITY-013 Создание LPD с валидацией ID
<!-- steps-hash: 38969cb414d3 -->
- Автотест: tests/api/create_activity/lpd/test_create_lpd_api.py::TestLpdAPI::test_create_lpd_with_validation
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Валидация ID → создание LPD. Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Валидировать LPD ID | — |
| 2 | 2. Создать LPD | — |

### TC-CREATE_ACTIVITY-014 Валидация несуществующего LPD ID
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/create_activity/lpd/test_create_lpd_api.py::TestLpdAPI::test_validate_invalid_lpd_id
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Валидация несуществующего ID. Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-CREATE_ACTIVITY-015 Создание LPD без названия
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/create_activity/lpd/test_create_lpd_api.py::TestLpdAPI::test_create_lpd_without_name
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Попытка создать LPD без названия → 422. Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-CREATE_ACTIVITY-016 Массовое удаление активностей
<!-- steps-hash: f5a390b8b2d5 -->
- Автотест: tests/api/create_activity/lpd/test_create_lpd_api.py::TestLpdAPI::test_mass_delete_activities
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Создать и массово удалить. Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать LPD | — |
| 2 | 2. Массово удалить | — |

### TC-CREATE_ACTIVITY-017 E2E: Программа → Поток → Модуль → Пользователь → LPD → Назначение → Открепление
<!-- steps-hash: 2e674a1a76d5 -->
- Автотест: tests/api/create_activity/lpd/test_e2e_lpd_flow.py::TestE2ELpdFlow::test_e2e_lpd_flow
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Полный цикл LPD. Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу | — |
| 2 | 2. Создать поток | — |
| 3 | 3. Создать модуль | — |
| 4 | 4. Создать пользователя | — |
| 5 | 5. Назначить пользователя на поток | — |
| 6 | 6. Создать LPD | — |
| 7 | 7. Назначить LPD в модуль | — |
| 8 | 8. Назначить пользователя на LPD | — |
| 9 | 9. Открепить пользователя от LPD | — |
