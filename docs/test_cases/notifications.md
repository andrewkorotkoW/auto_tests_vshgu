# Тест-кейсы: notifications

| Параметр | Значение |
|---|---|
| Область | tests/api/notifications, tests/api/notifications/templates, tests/ui/notifications/admin, tests/ui/notifications/user |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-NOTIFICATIONS-001 Шаблон уведомления: создать → получить → изменить тему/текст → список содержит
<!-- steps-hash: f48dc3effe73 -->
- Автотест: tests/api/notifications/templates/test_notification_templates_api.py::TestNotificationTemplatesApi::test_template_full_cycle
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /notifications/templates/{id} | — |
| 2 | Список шаблонов содержит созданный | — |
| 3 | PUT — смена темы (caption) и текста | — |
| 4 | Изменения сохранились при повторном GET | — |

### TC-NOTIFICATIONS-002 POST /notifications/templates/delete → 200, шаблон пропадает из списка
<!-- steps-hash: 2896da699876 -->
- Автотест: tests/api/notifications/templates/test_notification_templates_api.py::TestNotificationTemplatesApi::test_delete_template_removes_it_from_list
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /notifications/templates/delete | — |
| 2 | Шаблон пропадает из GET /notifications/templates | — |

### TC-NOTIFICATIONS-003 GET /notifications/register-templates — список шаблонов саморегистрации
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/templates/test_register_review_templates_api.py::TestRegisterReviewTemplatesApi::test_register_templates_list_schema
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-004 GET /notifications/register-templates/{type} — известный тип возвращает схему
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/templates/test_register_review_templates_api.py::TestRegisterReviewTemplatesApi::test_register_template_by_known_type[register_application]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-005 GET /notifications/register-templates/{type} — известный тип возвращает схему
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/templates/test_register_review_templates_api.py::TestRegisterReviewTemplatesApi::test_register_template_by_known_type[user_verified_email]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-006 GET /notifications/register-templates/{type} — известный тип возвращает схему
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/templates/test_register_review_templates_api.py::TestRegisterReviewTemplatesApi::test_register_template_by_known_type[application_accepted]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-007 GET /notifications/register-templates/{type} — известный тип возвращает схему
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/templates/test_register_review_templates_api.py::TestRegisterReviewTemplatesApi::test_register_template_by_known_type[application_rejected]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-008 GET /notifications/register-templates/{type} — неизвестный тип: кандидат в дефект
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/templates/test_register_review_templates_api.py::TestRegisterReviewTemplatesApi::test_register_template_unknown_type_returns_404
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-009 PUT register-template — тема/текст меняются и возвращаются к исходным в teardown
<!-- steps-hash: e4c8c13b29c7 -->
- Автотест: tests/api/notifications/templates/test_register_review_templates_api.py::TestRegisterReviewTemplatesApi::test_register_template_round_trip_restores_original
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Round-trip подтверждён разведкой как безопасный (POST возвращает 200 с теми же значениями, что были переданы) — исходные title/body шаблона register_application обязательно возвращаются в finally, даже при падении assert.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Временно изменить тему и текст | — |
| 2 | Изменения видны при повторном GET | — |
| 3 | Вернуть исходные значения | — |

### TC-NOTIFICATIONS-010 GET /notifications/review-templates — 200 и список ожидаемой схемы
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/templates/test_register_review_templates_api.py::TestRegisterReviewTemplatesApi::test_review_templates_list_schema
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: На develop список пуст (см. отчёт разведки) — PUT/GET по id не проверяется: нет существующего шаблона, id которого можно было бы безопасно использовать без хардкода из БД.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-011 Админ создаёт уведомление — оно видно по GET /notifications/{id} и в списке с теми же полями
<!-- steps-hash: 26c2ba662f6c -->
- Автотест: tests/api/notifications/test_notifications_crud_api.py::TestNotificationsCrudApi::test_create_notification_visible_in_list_and_by_id
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /notifications/{id} возвращает те же name/caption/text | — |
| 2 | Уведомление есть в общем списке GET /notifications | — |

### TC-NOTIFICATIONS-012 Получатель видит созданное уведомление через GET /notifications (user_session)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/test_notifications_crud_api.py::TestNotificationsCrudApi::test_user_session_sees_notification
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: user_session на develop — тот же аккаунт, что и admin_session (см. фикстуру user_notifications_endpoint и README §13) — тест подтверждает, что GET /notifications под этой сессией доступен и находит только что созданное уведомление, но не проверяет изоляцию «слушатель видит только своё» — для этого на стенде нет отдельной учётки.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-013 POST /notifications/resend/{id} — повторная отправка → 200
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/test_notifications_crud_api.py::TestNotificationsCrudApi::test_resend_notification
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-014 POST /notifications/delete → 200, уведомление пропадает из GET /notifications/{id}
<!-- steps-hash: c7ac318db8ed -->
- Автотест: tests/api/notifications/test_notifications_crud_api.py::TestNotificationsCrudApi::test_delete_notification_removes_it
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /notifications/delete | — |
| 2 | Уведомление пропадает из GET /notifications/{id} | — |

### TC-NOTIFICATIONS-015 GET /notifications содержит созданное уведомление с полями id/тема/дата/получатели
<!-- steps-hash: 81b02ff88c34 -->
- Автотест: tests/api/notifications/test_notifications_lists_api.py::TestNotificationsListsApi::test_notifications_list_has_expected_fields
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Найти созданное уведомление в общем списке GET /notifications | — |
| 2 | Проверить обязательные поля: id, тема (caption), дата, получатели | — |

### TC-NOTIFICATIONS-016 GET /notifications/creators — непустой справочник авторов уведомлений
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/test_notifications_lists_api.py::TestNotificationsListsApi::test_creators_dictionary_not_empty
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-017 GET /notifications/receivers — непустой справочник получателей
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/test_notifications_lists_api.py::TestNotificationsListsApi::test_receivers_dictionary_not_empty
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-018 GET /notifications/text-variables — непустой справочник переменных подстановки
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/test_notifications_lists_api.py::TestNotificationsListsApi::test_text_variables_dictionary_not_empty
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-019 POST /notifications/create без получателей — кандидат в дефект (план ждёт 422, факт 201)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/test_notifications_negative_api.py::TestNotificationsNegativeApi::test_create_without_receivers_returns_422
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-020 POST /notifications/create без текста → 422 с сообщением
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/test_notifications_negative_api.py::TestNotificationsNegativeApi::test_create_without_text_returns_422
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-021 GET /notifications/{id} от неадресованного пользователя → 403/404
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/test_notifications_negative_api.py::TestNotificationsNegativeApi::test_get_notification_forbidden_for_unrelated_user
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Свежесозданный обычный пользователь (без админ/менеджерских ролей) не может открыть чужое уведомление по id — на develop это проявляется как 403 на весь раздел /notifications/* (обычная роль слушателя не имеет прав на этот раздел вообще, не только на конкретный чужой id — см. отчёт разведки).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-022 GET /notifications/{id} для несуществующего id → 404
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/notifications/test_notifications_negative_api.py::TestNotificationsNegativeApi::test_get_nonexistent_notification_returns_404
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Кандидат в дефект (не проверяется assert-ом, только фиксируется в отчёте задачи): тело 404-ответа содержит полный стек-трейс Laravel-исключения — утечка деталей реализации наружу (см. README §13).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-NOTIFICATIONS-023 Созданное и отправленное уведомление видно в таблице админки «Все уведомления»
<!-- steps-hash: 9471ca053edc -->
- Автотест: tests/ui/notifications/admin/test_admin_notifications_table.py::TestAdminNotificationsTable::test_admin_sees_created_notification_in_table
- Приоритет: medium   Тип: ui   Роли: admin, user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Отправить уведомление явно (create() отдаёт его с send_at=null) | — |
| 2 | Дождаться строки с названием уведомления в таблице | — |

### TC-NOTIFICATIONS-024 Пользователь видит в «Уведомлениях» тему и текст созданного уведомления
<!-- steps-hash: df5a6b1de971 -->
- Автотест: tests/ui/notifications/user/test_user_sees_notification.py::TestUserSeesNotification::test_user_sees_notification
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть «Уведомления» | — |
| 2 | Тема уведомления видна в списке | — |
| 3 | Текст уведомления совпадает с созданным | — |
| 4 | Открыть уведомление | — |
