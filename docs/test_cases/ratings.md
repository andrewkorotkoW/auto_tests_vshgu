# Тест-кейсы: ratings

| Параметр | Значение |
|---|---|
| Область | tests/api/ratings |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-RATINGS-001 Admin меняет статус отзыва на допустимые целые 0/1/2
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_change_status_export.py::TestRatingsChangeStatusExport::test_change_status_admin_accepts_int_values[1]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Допустимые значения status эмпирически подобраны при подготовке задачи: это целые числа 0/1/2 (совпадают со значениями status в GET /ratings) — строковые "approved"/"rejected"/"pending" отвергаются валидатором (см. TC-RATINGS-005).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать tincan-курс (обёрнутый материалом БЗ) и отзыв на него | Отзыв создан |
| 2 | POST /ratings/change-status с review_ids=[id отзыва], status=1 | 200, {"data": {"status": "success"}} |
| 3 | GET /ratings/{id отзыва} | status отзыва равен 1 |

### TC-RATINGS-002 Admin меняет статус отзыва на допустимые целые 0/1/2
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_change_status_export.py::TestRatingsChangeStatusExport::test_change_status_admin_accepts_int_values[2]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Допустимые значения status эмпирически подобраны при подготовке задачи: это целые числа 0/1/2 (совпадают со значениями status в GET /ratings) — строковые "approved"/"rejected"/"pending" отвергаются валидатором (см. TC-RATINGS-005).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать tincan-курс (обёрнутый материалом БЗ) и отзыв на него | Отзыв создан |
| 2 | POST /ratings/change-status с review_ids=[id отзыва], status=2 | 200, {"data": {"status": "success"}} |
| 3 | GET /ratings/{id отзыва} | status отзыва равен 2 |

### TC-RATINGS-003 Admin меняет статус отзыва на допустимые целые 0/1/2
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_change_status_export.py::TestRatingsChangeStatusExport::test_change_status_admin_accepts_int_values[0]
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Допустимые значения status эмпирически подобраны при подготовке задачи: это целые числа 0/1/2 (совпадают со значениями status в GET /ratings) — строковые "approved"/"rejected"/"pending" отвергаются валидатором (см. TC-RATINGS-005).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать tincan-курс (обёрнутый материалом БЗ) и отзыв на него | Отзыв создан |
| 2 | POST /ratings/change-status с review_ids=[id отзыва], status=0 | 200, {"data": {"status": "success"}} |
| 3 | GET /ratings/{id отзыва} | status отзыва равен 0 |

### TC-RATINGS-004 Admin: пустое тело change-status → 422 с обязательными review_ids/status
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_change_status_export.py::TestRatingsChangeStatusExport::test_change_status_missing_fields_422
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /ratings/change-status с пустым телом {} | 422, errors содержит data.attributes.review_ids и data.attributes.status |

### TC-RATINGS-005 Строковый статус отвергается — требуется целое число
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_change_status_export.py::TestRatingsChangeStatusExport::test_change_status_rejects_non_integer_status
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать tincan-курс (обёрнутый материалом БЗ) и отзыв на него | Отзыв создан |
| 2 | POST /ratings/change-status с review_ids=[id отзыва], status="approved" (строка) | 422, errors содержит data.attributes.status |

### TC-RATINGS-006 Обычный слушатель не может менять статус отзыва → 403
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_change_status_export.py::TestRatingsChangeStatusExport::test_change_status_forbidden_for_regular_user
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать второго пользователя (не admin), создать его отзыв на материал БЗ | Отзыв создан |
| 2 | От имени этого пользователя POST /ratings/change-status на его же отзыв | 403 |

### TC-RATINGS-007 POST /ratings/export → 200 result=ok для admin и для обычного пользователя
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_change_status_export.py::TestRatingsChangeStatusExport::test_export_returns_ok_regardless_of_role
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: Контракт ответа подтверждён разведкой (docs/qr_code_ratings_recon.md): синхронный 200 без обязательных полей. Реальный побочный эффект (письмо/файл/ссылка) этим тестом НЕ проверяется — разведка явно предупреждает не фиксировать его как «одинаковый для всех ролей» без проверки факта; здесь проверяется только контракт ответа API.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /ratings/export от имени admin | 200, {"result": "ok"} |
| 2 | Создать второго пользователя, POST /ratings/export от его имени | 200, {"result": "ok"} |

### TC-RATINGS-008 Анонимный запрос export → 401
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_change_status_export.py::TestRatingsChangeStatusExport::test_export_anon_401
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Анонимный POST /ratings/export с {} | 401 |

### TC-RATINGS-009 Создать отзыв на tincan-курс (через материал БЗ) -> получить -> my-review -> удалить
<!-- steps-hash: 3d89b1829105 -->
- Автотест: tests/api/ratings/test_ratings_crud_api.py::TestRatingsCrud::test_full_review_cycle_on_tincan_course
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Рабочий путь для отзыва на tincan-курс — обернуть его материалом базы знаний (created_course) и ставить отзыв на entity_type="knowledge_base_material" с id материала, не на сам tincan (см. TC-RATINGS-011).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Обернуть tincan-курс материалом БЗ (created_course) | Материал создан, есть id |
| 2 | POST /ratings: rating=5, entity_type=knowledge_base_material, entity_id=id материала, body="Отличный курс" | 201, отзыв создан с rating=5, body и entity_type/entity_id совпадают с запросом |
| 3 | GET /ratings/{id отзыва} | Возвращён тот же отзыв (тот же id, body) |
| 4 | GET /ratings/my-review?entity_type=knowledge_base_material&entity_id=id материала | Возвращён тот же отзыв (id совпадает) |
| 5 | GET /ratings (общий список) | Созданный отзыв присутствует в списке |
| 6 | DELETE /ratings/my-review?entity_type=knowledge_base_material&entity_id=id материала | Отзыв удалён |
| 7 | Повторный GET /ratings/my-review на тот же материал | 200, data пусто |

### TC-RATINGS-010 Обычный слушатель может создать отзыв на материал БЗ, не будучи назначенным на курс
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_crud_api.py::TestRatingsCrud::test_listener_can_review_without_assignment
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Обернуть tincan-курс материалом БЗ (created_course) | Материал создан |
| 2 | Создать второго пользователя (слушателя), не назначенного на курс | Пользователь создан |
| 3 | От его имени POST /ratings: rating=4, entity_type=knowledge_base_material, entity_id=id материала | 201, отзыв создан с rating=4 и тем же entity_id — назначение на курс не требуется |

### TC-RATINGS-011 Сырой tincan (entity_type=activity) — известное ограничение: всегда 'Not reviewable entity'
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_crud_api.py::TestRatingsCrud::test_raw_tincan_activity_is_not_reviewable
- Приоритет: medium   Тип: api   Роли: admin, user
- Предусловия: Эмпирически подтверждённое ограничение API (не дефект, тест проходит, без xfail): даже когда tincan-активность реально назначена слушателю, POST /ratings с entity_type="activity" и id самой активности всегда отвечает 422 "Not reviewable entity" — и для админа, и для назначенного слушателя. Рабочий путь — обернуть tincan материалом БЗ и ставить отзыв на entity_type="knowledge_base_material" (см. TC-RATINGS-009), а не на сырую активность.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать tincan-активность (created_tincan, без обёртки материалом БЗ) | Активность создана |
| 2 | Назначить активность слушателю (assigned_user + assign_activities) | Активность назначена слушателю |
| 3 | POST /ratings: rating=5, entity_type="activity", entity_id=id активности | 422, текст ошибки содержит "Not reviewable entity" |

### TC-RATINGS-012 GET /ratings анонимно → 401
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_list_ratings_anon_401
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Анонимный GET /ratings | 401 |

### TC-RATINGS-013 GET/DELETE /ratings/my-review без entity_type/entity_id → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_missing_params_422[-get]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /ratings/my-review без параметров запроса | 422, errors непусто |

### TC-RATINGS-014 GET/DELETE /ratings/my-review без entity_type/entity_id → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_missing_params_422[-delete]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | DELETE /ratings/my-review без параметров запроса | 422, errors непусто |

### TC-RATINGS-015 GET/DELETE /ratings/my-review без entity_type/entity_id → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_missing_params_422[?entity_type=knowledge_base_material-get]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /ratings/my-review?entity_type=knowledge_base_material (без entity_id) | 422, errors непусто |

### TC-RATINGS-016 GET/DELETE /ratings/my-review без entity_type/entity_id → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_missing_params_422[?entity_type=knowledge_base_material-delete]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | DELETE /ratings/my-review?entity_type=knowledge_base_material (без entity_id) | 422, errors непусто |

### TC-RATINGS-017 GET/DELETE /ratings/my-review без entity_type/entity_id → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_missing_params_422[?entity_id=1-get]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /ratings/my-review?entity_id=1 (без entity_type) | 422, errors непусто |

### TC-RATINGS-018 GET/DELETE /ratings/my-review без entity_type/entity_id → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_missing_params_422[?entity_id=1-delete]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | DELETE /ratings/my-review?entity_id=1 (без entity_type) | 422, errors непусто |

### TC-RATINGS-019 GET/DELETE /ratings/my-review анонимно → 401
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_anon_401[get]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Анонимный GET /ratings/my-review?entity_type=knowledge_base_material&entity_id=1 | 401 |

### TC-RATINGS-020 GET/DELETE /ratings/my-review анонимно → 401
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_anon_401[delete]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Анонимный DELETE /ratings/my-review?entity_type=knowledge_base_material&entity_id=1 | 401 |

### TC-RATINGS-021 GET /ratings/my-review для несуществующей сущности → 404
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_for_nonexistent_entity_404
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /ratings/my-review?entity_type=knowledge_base_material&entity_id=999999999 | 404 |

### TC-RATINGS-022 GET /ratings/my-review для реальной сущности без моего отзыва → 200 с пустыми данными
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_my_review_for_real_entity_without_my_review_returns_empty
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать материал БЗ (tincan-курс), не оставляя отзыва | Материал создан |
| 2 | GET /ratings/my-review на этот материал | 200, data пусто |

### TC-RATINGS-023 DELETE /ratings/my-review без активного отзыва — известный дефект (500 вместо 404)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_delete_my_review_without_active_review_is_not_500
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Известный дефект: DELETE /ratings/my-review для реально существующей сущности, у которой нет моего отзыва (ещё не создавался или уже удалён), отвечает 500 ("Call to a member function delete() on null", RatingController.php:81) вместо ожидаемых 404/200 — контроллер не проверяет, что отзыв найден, перед вызовом delete() на нём. Тест помечен ожидаемо неуспешным (xfail, strict=False), пока дефект не исправлен.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать материал БЗ (tincan-курс), не оставляя отзыва | Материал создан |
| 2 | DELETE /ratings/my-review на этот материал | Ожидался 200/404; фактически — 500 (дефект) |

### TC-RATINGS-024 POST /ratings без обязательных полей конверта → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_create_rating_missing_fields_422[payload0]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /ratings с пустым телом {} | 422, errors содержит data.attributes.rating, data.attributes.entity_type, data.attributes.entity_id |

### TC-RATINGS-025 POST /ratings без обязательных полей конверта → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_create_rating_missing_fields_422[payload1]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /ratings с {"data": {}} (нет attributes) | 422, errors содержит data.attributes.rating, data.attributes.entity_type, data.attributes.entity_id |

### TC-RATINGS-026 POST /ratings без обязательных полей конверта → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_create_rating_missing_fields_422[payload2]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /ratings с {"data": {"attributes": {}}} (нет полей внутри attributes) | 422, errors содержит data.attributes.rating, data.attributes.entity_type, data.attributes.entity_id |

### TC-RATINGS-027 POST /ratings без обязательных полей конверта → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_create_rating_missing_fields_422[payload3]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /ratings с {"rating": 5, "entity_type": "knowledge_base_material", "entity_id": 1} — поля вне конверта data.attributes | 422, errors содержит data.attributes.rating, data.attributes.entity_type, data.attributes.entity_id |

### TC-RATINGS-028 POST /ratings с неизвестным entity_type → 404 'Неверный alias сущности'
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_create_rating_unknown_entity_type_404
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /ratings: rating=5, entity_type="not-a-real-type", entity_id=1 | 404, data.error содержит "alias" |

### TC-RATINGS-029 POST /ratings на несуществующий материал известного типа → 404
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_create_rating_nonexistent_entity_id_404
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /ratings: rating=5, entity_type="knowledge_base_material", entity_id=999999999 (не существует) | 404 |

### TC-RATINGS-030 GET /ratings/<несуществующий id> → 404
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/ratings/test_ratings_negative_api.py::TestRatingsNegative::test_get_rating_nonexistent_404
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /ratings/999999999 | 404 |
