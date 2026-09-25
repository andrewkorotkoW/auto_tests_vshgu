# Тест-кейсы: buk

| Параметр | Значение |
|---|---|
| Область | tests/api/buk, tests/ui/buk |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-BUK-001 POST: приём пользователя → recorded, затем автосопоставление по email → synced
<!-- steps-hash: f0626e1280a5 -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_post_auto_match_by_email
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать пользователя АСУО через админ-API | — |
| 2 | 2. POST в /external/buk/users с email и ФИО как в АСУО | — |
| 3 | 3. Дождаться асинхронного сопоставления | — |

### TC-BUK-002 POST повторно с тем же buk_user_id → already_exists
<!-- steps-hash: 2b0382c42238 -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_post_duplicate_already_exists
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Повторный POST тем же buk_user_id | — |

### TC-BUK-003 PUT по неизвестному buk_user_id → not_found
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_put_unknown_user_not_found
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-BUK-004 POST с email, которого нет в АСУО → pending; PUT с верным email → synced
<!-- steps-hash: 5667bf6b3bf1 -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_pending_then_put_corrects_email
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. POST с несуществующим email | — |
| 2 | 2. PUT с уточнённым email → повторное сопоставление | — |

### TC-BUK-005 Ручное сопоставление по user_id при несовпавшем email → synced_manual
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_manual_match_by_user_id
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-BUK-006 Ручное сопоставление с user_id администратора → rejected
<!-- steps-hash: 5758bbe20dbf -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_manual_match_admin_rejected
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Узнать id текущего администратора | — |

### TC-BUK-007 Второй buk_user_id на уже связанного пользователя → conflict; связь 1:1 сохраняется
<!-- steps-hash: dd59371e9913 -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_second_buk_id_same_user_conflict
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST другого buk_user_id с тем же email | — |
| 2 | Первая связь не изменилась | — |

### TC-BUK-008 PUT с другим user_id для synced-пользователя → conflict, профиль и связь не меняются
<!-- steps-hash: f4bd7e811490 -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_put_other_user_id_on_synced_conflict
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | PUT с чужим user_id и другим именем | — |
| 2 | Итог обработки: conflict, связь осталась с первым пользователем | — |

### TC-BUK-009 PUT для synced не перезаписывает мастер-профиль АСУО
<!-- steps-hash: a83d9177d4a3 -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_put_synced_does_not_overwrite_profile
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | PUT с другим ФИО | — |
| 2 | Профиль в АСУО остался прежним | — |

### TC-BUK-010 DELETE: разрыв связи → unsynced/deleted_in_buk, аккаунт АСУО остаётся; повтор идемпотентен
<!-- steps-hash: d95347b5c89e -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_delete_unsync_idempotent
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. DELETE | — |
| 2 | 2. Аккаунт в АСУО сохранился | — |
| 3 | 3. Повторный DELETE — успех с тем же состоянием | — |

### TC-BUK-011 После DELETE перепривязка к другому пользователю через PUT с user_id
<!-- steps-hash: ea4bba500ead -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_relink_after_delete
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | DELETE, затем PUT с новым user_id | — |

### TC-BUK-012 DELETE неизвестного buk_user_id → not_found
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_delete_unknown_not_found
- Приоритет: low   Тип: api   Роли: -
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-BUK-013 POST без обязательного email → поэлементная ошибка валидации
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_post_without_email_validation_error
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-BUK-014 Без токена → 403 Unauthorized
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_without_token_forbidden
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-BUK-015 Пакет из двух пользователей: поэлементные результаты в порядке запроса
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/buk/test_external_buk_users_api.py::TestExternalBukUsersAPI::test_batch_two_users
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-BUK-016 Админ: в базе пользователей у синхронизированного с БУК стоит чип «БУК», подсказка «Синхронизирован»
<!-- steps-hash: 76b8e1883411 -->
- Автотест: tests/ui/buk/test_buk_admin_users_ui.py::TestBukAdminUsersUI::test_admin_sees_buk_chip_with_tooltip
- Приоритет: high   Тип: ui   Роли: admin, user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Найти пользователя в базе пользователей | — |
| 2 | В колонке «Синхронизация» есть чип «БУК» с зелёной иконкой | — |
| 3 | Навести курсор на «БУК»: подсказка «Синхронизирован» | — |

### TC-BUK-017 Админ: у пользователя без синхронизации чипа «БУК» нет, «КАС» показывает ожидание
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/ui/buk/test_buk_admin_users_ui.py::TestBukAdminUsersUI::test_admin_no_buk_chip_for_unsynced
- Приоритет: medium   Тип: ui   Роли: admin, user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-BUK-018 Админ: после разрыва связи (DELETE от БУК) чип «БУК» больше не «Синхронизирован»
<!-- steps-hash: e1b36b6ea4e3 -->
- Автотест: tests/ui/buk/test_buk_admin_users_ui.py::TestBukAdminUsersUI::test_admin_buk_chip_after_unsync
- Приоритет: medium   Тип: ui   Роли: admin, user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | До разрыва: «Синхронизирован» | — |
| 2 | DELETE от БУК | — |
| 3 | После обновления таблицы чип либо исчез, либо подсказка уже не «Синхронизирован» | — |

### TC-BUK-019 Синхронизированный с БУК пользователь: вход → в меню профиля есть «АИС «БУК «Перспектива»»» → переход
<!-- steps-hash: 581a13cf3b4f -->
- Автотест: tests/ui/buk/test_buk_user_menu_ui.py::TestBukUserMenuUI::test_buk_button_for_synced_user
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Войти под пользователем | — |
| 2 | 2. Открыть меню под ФИО: пункт БУК отображается | — |
| 3 | 3. Переход по кнопке: открывается новая вкладка с переходом в БУК | — |

### TC-BUK-020 Согласие с правилами в БУК → вход в кабинет БУК (сквозной SSO)
<!-- steps-hash: 013506d2a39b -->
- Автотест: tests/ui/buk/test_buk_user_menu_ui.py::TestBukUserMenuUI::test_buk_consent_leads_into_buk
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Страница согласия БУК | — |
| 2 | 2. Галка «Даю согласие» → «Подтвердить» | — |
| 3 | 3. Мы внутри БУК, без ошибки авторизации | — |

### TC-BUK-021 Пользователь без синхронизации с БУК: пункта БУК в меню нет
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/ui/buk/test_buk_user_menu_ui.py::TestBukUserMenuUI::test_no_buk_button_for_unsynced_user
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-BUK-022 После разрыва связи (DELETE от БУК) пункт БУК исчезает из меню
<!-- steps-hash: fbc0980761b3 -->
- Автотест: tests/ui/buk/test_buk_user_menu_ui.py::TestBukUserMenuUI::test_buk_button_disappears_after_unsync
- Приоритет: medium   Тип: ui   Роли: user
- Предусловия: Требует env=stage
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | До разрыва пункт есть | — |
| 2 | DELETE от БУК → unsynced | — |
| 3 | После перезагрузки страницы пункта нет | — |
