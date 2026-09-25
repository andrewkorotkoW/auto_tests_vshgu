# Тест-кейсы: dictionaries

| Параметр | Значение |
|---|---|
| Область | tests/api/dictionaries |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-DICTIONARIES-001 Поток программы, созданный со ссылкой на новый элемент справочника program_type, хранит эту связь
<!-- steps-hash: c0992fade09f -->
- Автотест: tests/api/dictionaries/test_dictionaries_association_api.py::TestDictionariesAssociationApi::test_stream_created_with_new_dictionary_item_persists_reference
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Связь сохраняется и после повторного GET потока | — |

### TC-DICTIONARIES-002 Пользователь, созданный со ссылкой на существующие region/municipality, хранит эту связь
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_association_api.py::TestDictionariesAssociationApi::test_user_created_with_dictionary_region_persists_reference
- Приоритет: high   Тип: api   Роли: user
- Предусловия: region/municipality — read-only справочники ФИАС на develop (мишн-док), поэтому связь проверяется на уже существующих элементах (region_id=1/municipality_id=158 — значения по умолчанию generate_user_payload), а не на созданных тестом записях.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-003 POST /dictionaries создаёт элемент, он находится через find_by_name
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_create_and_find_by_name[program_type]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-004 POST /dictionaries создаёт элемент, он находится через find_by_name
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_create_and_find_by_name[program_department]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-005 POST /dictionaries создаёт элемент, он находится через find_by_name
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_create_and_find_by_name[learning_format]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-006 POST /dictionaries создаёт элемент, он находится через find_by_name
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_create_and_find_by_name[tag]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-007 GET /dictionaries/by-type/{type} — созданный элемент есть в полном списке типа
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_list_by_type_contains_created[program_type]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-008 GET /dictionaries/by-type/{type} — созданный элемент есть в полном списке типа
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_list_by_type_contains_created[program_department]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-009 GET /dictionaries/by-type/{type} — созданный элемент есть в полном списке типа
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_list_by_type_contains_created[learning_format]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-010 GET /dictionaries/by-type/{type} — созданный элемент есть в полном списке типа
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_list_by_type_contains_created[tag]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-011 GET /dictionaries?filters[type]&filters[name] — постраничный список фильтруется по типу и имени
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_list_paginated_filtered[program_type]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-012 GET /dictionaries?filters[type]&filters[name] — постраничный список фильтруется по типу и имени
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_list_paginated_filtered[program_department]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-013 GET /dictionaries?filters[type]&filters[name] — постраничный список фильтруется по типу и имени
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_list_paginated_filtered[learning_format]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-014 GET /dictionaries?filters[type]&filters[name] — постраничный список фильтруется по типу и имени
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_list_paginated_filtered[tag]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-015 PATCH /dictionaries/{id} — обновляет имя, старое имя больше не находится
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_update_changes_name[program_type]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-016 PATCH /dictionaries/{id} — обновляет имя, старое имя больше не находится
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_update_changes_name[learning_format]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-017 PATCH /dictionaries/{id} — обновляет имя, старое имя больше не находится
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_update_changes_name[tag]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-018 PATCH /dictionaries/{id} для type=program_department — кандидат в дефект (план ждёт 200, факт 500)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_update_program_department_name
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-019 DELETE /dictionaries/{id} — элемент перестаёт находиться по имени
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_delete_removes_item[program_type]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-020 DELETE /dictionaries/{id} — элемент перестаёт находиться по имени
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_delete_removes_item[program_department]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-021 DELETE /dictionaries/{id} — элемент перестаёт находиться по имени
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_delete_removes_item[learning_format]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-022 DELETE /dictionaries/{id} — элемент перестаёт находиться по имени
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_delete_removes_item[tag]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-023 GET /dictionaries/{id} и PUT /dictionaries/{id} не поддерживаются — 405 (get/update по id не предусмотрены)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_crud_api.py::TestDictionariesCrudApi::test_get_and_put_by_id_not_allowed
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-024 POST /dictionaries с пустым name — 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_negative_api.py::TestDictionariesNegativeApi::test_create_empty_name_returns_422
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-025 POST /dictionaries без поля type — кандидат в дефект (план ждёт 422, факт 500)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_negative_api.py::TestDictionariesNegativeApi::test_create_without_type_returns_422
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-026 POST /dictionaries от обычного пользователя — 403 (раздел админский)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_negative_api.py::TestDictionariesNegativeApi::test_create_forbidden_for_regular_user
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-027 GET /dictionaries/by-type/{type} от обычного пользователя — доступно (раздел на чтение открыт всем)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_negative_api.py::TestDictionariesNegativeApi::test_list_by_type_allowed_for_regular_user
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: Не дефект, а документирование фактической модели прав: в отличие от /notifications/* (403 целиком для не-админов, README §13), справочники читаются любым авторизованным пользователем — POST/PATCH/DELETE админские, GET нет.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-028 POST /dictionaries type=project/program_level без meta.experts_entity_id ломает GET по всему типу — подтверждённый дефект
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_negative_api.py::TestDictionariesNegativeApi::test_create_experts_type_without_meta_breaks_type_reads[project]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-DICTIONARIES-029 POST /dictionaries type=project/program_level без meta.experts_entity_id ломает GET по всему типу — подтверждённый дефект
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/dictionaries/test_dictionaries_negative_api.py::TestDictionariesNegativeApi::test_create_experts_type_without_meta_breaks_type_reads[program_level]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |
