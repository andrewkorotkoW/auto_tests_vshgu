# Тест-кейсы: Шаблоны (Helpdesk)

| Параметр | Значение |
|---|---|
| Область | tests/api/helpdesk, tests/ui/helpdesk/admin |
| Стенд | develop, admin-панель `https://helpdesk-develop.d2.devspark.ru` (см. docs/helpdesk_recon.md) |
| Роли | admin — доступ к Helpdesk |

<!-- Кейсы перенесены вручную из Test IT v.2 (проект «ВШГУ v.2», раздел Helpdesk / Шаблоны,
     docs/plans/helpdesk_testit_v2_export.md) и сверены на стенде helpdesk-develop
     (docs/helpdesk_recon.md). tools/test_cases/generate.py их не создавал. Подраздел
     «Шаблоны / Шаблоны» из выгрузки v.2 (без кейсов) — внутренняя категория Test IT без
     отдельного UI-экрана, не переносится как раздел (docs/helpdesk_recon.md п.3). -->

### TC-HELPDESK_TEMPLATES-001 Переход на страницу «Шаблоны ответов»
- Автотест: tests/ui/helpdesk/admin/test_navigation.py::test_templates_section
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: -
- Требование: Test IT v.2 #9620, правка по docs/helpdesk_recon.md п.4 (#9620 ⚠): колонка факт. называется «Группы» (во множественном числе), в выгрузке v.2 — «Группа»
- Test IT: 908f42f1-c0e2-4eba-ac57-ae468015ac3e
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Клик по «Шаблоны» в боковом меню | Открывается «Шаблоны ответов», URL `/admin/mail-template`, кнопка «Добавить шаблон ответа», поле поиска, таблица с колонками ID/Наименование/Содержимое/Группы/Действия, пагинатор |

### TC-HELPDESK_TEMPLATES-002 Создание шаблона
- Автотест: tests/api/helpdesk/test_templates_api.py::TestTemplatesApi::test_create_template
- Приоритет: high   Тип: api   Роли: admin
- Предусловия: Шаблон тестовый (`Автотест_*`), удаляется в teardown
- Требование: Test IT v.2 #9621, подтверждено docs/helpdesk_recon.md п.4 (#9621 ✅)
- Test IT: c67ffcb5-f6e2-4f87-938f-b9e973f4c775
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | `POST /admin/mail-template` с полями Наименование, Содержимое, Ключевые слова (через запятую), Группа (select2, множественный выбор) | Ответ успешный, шаблон создан |
| 2 | `GET /admin/mail-template/search` и найти шаблон по наименованию | Шаблон найден, первым в списке (как при создании через форму) |

### TC-HELPDESK_TEMPLATES-003 Создание шаблона через форму
- Автотест: tests/ui/helpdesk/admin/test_templates.py::test_create_template
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: Шаблон тестовый (`Автотест_*`), удаляется в teardown
- Требование: Test IT v.2 #9621, подтверждено docs/helpdesk_recon.md п.4 (#9621 ✅)
- Test IT: 2113995a-9e4d-4585-82a7-f74c81153a54
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | На «Шаблоны ответов» нажать «Добавить шаблон ответа» | Открывается страница создания, URL `/admin/mail-template/create` |
| 2 | Заполнить поля «Наименование», «Содержимое», «Ключевые слова» (через запятую), выбрать одну или несколько групп в поле «Группа» | Введённые данные отображаются в полях |
| 3 | Нажать «Сохранить и выйти» | Открывается «Шаблоны ответов», созданный шаблон — первый в таблице |

### TC-HELPDESK_TEMPLATES-004 Просмотр шаблона
- Автотест: tests/api/helpdesk/test_templates_api.py::TestTemplatesApi::test_view_template
- Приоритет: medium   Тип: api   Роли: admin
- Предусловия: В системе создан шаблон (см. TC-HELPDESK_TEMPLATES-002)
- Требование: Test IT v.2 #9622, подтверждено docs/helpdesk_recon.md п.4 (#9622 ✅)
- Test IT: ccd86a6b-b37f-4790-a916-71162f4351de
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | `GET /admin/mail-template/{id}/show` | Ответ 200, в HTML — кнопка «Назад», Наименование, Содержимое, Ключевые слова, Группа созданного шаблона |

### TC-HELPDESK_TEMPLATES-005 Редактирование шаблона
- Автотест: tests/api/helpdesk/test_templates_api.py::TestTemplatesApi::test_update_template
- Приоритет: high   Тип: api   Роли: admin
- Предусловия: В системе создан шаблон (см. TC-HELPDESK_TEMPLATES-002)
- Требование: Test IT v.2 #9623, исправлено по docs/helpdesk_recon.md п.4 (#9623 ⚠): реальный маршрут редактирования — `GET /admin/mail-template/{id}/edit` (в выгрузке v.2 ошибочно указан `.../create»)
- Test IT: ca813a2e-a2fe-4a00-b119-f9d6d4b72664
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | `GET /admin/mail-template/{id}/edit` | Ответ 200, форма предзаполнена текущими данными шаблона (заголовок «Редактировать шаблон ответа») |
| 2 | `PUT /admin/mail-template/{id}` с изменёнными Наименование/Содержимое/Ключевые слова/Группа | Ответ успешный |
| 3 | Повторный `GET /admin/mail-template/{id}/show` | Данные шаблона обновлены |

### TC-HELPDESK_TEMPLATES-006 Удаление шаблона
- Автотест: tests/api/helpdesk/test_templates_api.py::TestTemplatesApi::test_delete_template
- Приоритет: high   Тип: api   Роли: admin
- Предусловия: В системе создан тестовый шаблон (см. TC-HELPDESK_TEMPLATES-002)
- Требование: Test IT v.2 #9624, правка по docs/helpdesk_recon.md п.4 (#9624 ⚠, §6): точный текст подтверждающей модалки не зафиксирован надёжно — автотест проверяет факт удаления по `DELETE /admin/mail-template/{id}`, а не текст модалки
- Test IT: 906a63e6-7264-4ed5-a5ee-d1a096b61d11
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | `DELETE /admin/mail-template/{id}` (`data-route` из иконки-корзины) с CSRF-токеном | Ответ успешный |
| 2 | `GET /admin/mail-template/search` и поискать шаблон по наименованию | Шаблон не находится в списке |

### TC-HELPDESK_TEMPLATES-007 Создание шаблона без обязательных полей — 422
- Автотест: tests/api/helpdesk/test_templates_negative_api.py::TestTemplatesNegativeApi::test_create_template_missing_required_fields
- Приоритет: medium   Тип: api   Роли: admin
- Предусловия: -
- Test IT: d57aba10-e699-4232-9790-d609927a7f1c
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | `POST /admin/mail-template` без обязательных полей (Наименование, Содержимое) | Сервер отвечает ошибкой валидации (422), шаблон не создаётся |

### TC-HELPDESK_TEMPLATES-008 Редактирование несуществующего шаблона — 404
- Автотест: tests/api/helpdesk/test_templates_negative_api.py::TestTemplatesNegativeApi::test_edit_template_not_found
- Приоритет: medium   Тип: api   Роли: admin
- Предусловия: -
- Test IT: be0179e8-6464-4f80-91e1-76c9c9412b24
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | `GET /admin/mail-template/{заведомо несуществующий id}/edit` | Сервер отвечает 404 |
