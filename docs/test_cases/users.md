# Тест-кейсы: users

| Параметр | Значение |
|---|---|
| Область | tests/api/users, tests/api/users/teacher, tests/ui/users |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-USERS-001 API Develop: Назначить роль преподавателя пользователю
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/users/teacher/test_assign_roles_api.py::TestAssignRoles::test_assign_teacher_role
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-USERS-002 API Develop: Полный цикл проверки ДЗ — студент → преподаватель
<!-- steps-hash: ca400a5f0722 -->
- Автотест: tests/api/users/teacher/test_examine_by_teacher.py::TestExamineByTeacher::test_examine_homework_flow
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать студента | — |
| 2 | 2. Создать преподавателя | — |
| 3 | 3. Загрузить обложку и создать ДЗ | — |
| 4 | 4. Назначить ДЗ студенту | — |
| 5 | 5. Получить answer_id через GET /homework/answers | — |
| 6 | 6. Преподаватель проверяет ответ | — |

### TC-USERS-003 Создание пользователя с валидными данными
<!-- steps-hash: bd979c2df7b8 -->
- Автотест: tests/api/users/test_create_user_api.py::TestCreateUserAPI::test_create_user_success
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Позитивный кейс: создание пользователя с корректными данными.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать пользователя через API | — |
| 2 | 2. Проверить ID пользователя | — |
| 3 | 3. Проверить Email | — |
| 4 | 4. Проверить ФИО | — |
| 5 | 5. Время выполнения | — |

### TC-USERS-004 Создание пользователя с регионом и муниципалитетом
<!-- steps-hash: fe6bf5b29b2d -->
- Автотест: tests/api/users/test_create_user_api.py::TestCreateUserAPI::test_create_user_with_specific_region
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: Создание с регионом Москва (33) и муниципалитетом Южный округ (2310).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать пользователя с регионом 33 и муниципалитетом 2310 | — |
| 2 | 2. Проверить регион | — |
| 3 | 3. Проверить муниципалитет | — |

### TC-USERS-005 Создание пользователя с кастомной датой рождения
<!-- steps-hash: 966c7cf14a9e -->
- Автотест: tests/api/users/test_create_user_api.py::TestCreateUserAPI::test_create_user_custom_birthdate
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: Создание пользователя с конкретной датой рождения.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'Создать пользователя с ДР {custom_dob}' | — |
| 2 | Проверить дату рождения | — |

### TC-USERS-006 Создание пользователя с уже существующим Email
<!-- steps-hash: f8a9d819e4c4 -->
- Автотест: tests/api/users/test_create_user_api.py::TestCreateUserAPI::test_create_user_duplicate_email
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Попытка создать пользователя с Email, который уже существует.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать первого пользователя | — |
| 2 | 2. Попытаться создать второго с тем же Email | — |

### TC-USERS-007 Создание пользователя без даты рождения
<!-- steps-hash: 61ee913fb390 -->
- Автотест: tests/api/users/test_create_user_api.py::TestCreateUserAPI::test_create_user_without_birthdate
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Попытка создать пользователя без даты рождения.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Отправить запрос без date_of_birth | — |

### TC-USERS-008 Создание пользователя без пароля
<!-- steps-hash: 64590be3cffc -->
- Автотест: tests/api/users/test_create_user_api.py::TestCreateUserAPI::test_create_user_without_password
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Попытка создать пользователя с пустым паролем.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Отправить запрос без пароля | — |

### TC-USERS-009 Создание пользователя с паролем только из строчных букв
<!-- steps-hash: 57edb7d4c7f7 -->
- Автотест: tests/api/users/test_create_user_api.py::TestCreateUserAPI::test_create_user_password_lowercase_only
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Попытка создать пользователя с паролем без заглавных букв и цифр.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Отправить запрос с паролем 'abcdefgh' | — |

### TC-USERS-010 Создание пользователя с паролем 'password'
<!-- steps-hash: 44abd8c76828 -->
- Автотест: tests/api/users/test_create_user_api.py::TestCreateUserAPI::test_create_user_password_obvious
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Попытка создать пользователя с очевидным паролем 'password'.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Отправить запрос с паролем 'password' | — |

### TC-USERS-011 Создание пользователя с паролем из одних цифр
<!-- steps-hash: 524e8f9466cb -->
- Автотест: tests/api/users/test_create_user_api.py::TestCreateUserAPI::test_create_user_password_numbers_only
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Попытка создать пользователя с паролем '12345678'.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Отправить запрос с паролем '12345678' | — |

### TC-USERS-012 Обычный пользователь не может создать другого пользователя через API
<!-- steps-hash: 5e28ad03d847 -->
- Автотест: tests/api/users/test_users_permissions_api.py::TestUsersPermissionsAPI::test_create_user_forbidden_for_regular_user
- Приоритет: high   Тип: api   Роли: user
- Предусловия: Создаём обычного пользователя (без админских ролей), логинимся под ним по email/паролю, которые вернула фикстура created_user, и пытаемся выполнить от его имени админское действие POST /users — ожидаем отказ в доступе (403).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать обычного пользователя от имени администратора | — |
| 2 | 2. Залогиниться под этим пользователем | — |
| 3 | 3. Попытаться создать пользователя от его имени | — |

### TC-USERS-013 Пользователь: логин → анкета и онбординг → cookie-баннер → ссылка «Политикой» → «Принимаю» → баннер не повторяется
<!-- steps-hash: da6e8552eb56 -->
- Автотест: tests/ui/users/test_user_cookie_banner.py::TestUserCookieBanner::test_user_cookie_banner
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: Ожидаемое поведение (владелец, 23.09.2026): баннер показывается после входа в систему, на странице входа его нет. После «Принимаю» повторно не показывается.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать пользователя | — |
| 2 | 2. Логин, анкета «данные о себе», тур онбординга | — |
| 3 | 3. Cookie-баннер виден | — |
| 4 | 4. Ссылка «Политикой…» открывается в новой вкладке | — |
| 5 | 5. Нажать «Принимаю» — баннер скрывается | — |
| 6 | 6. После перезагрузки страницы баннер не показывается повторно | — |

### TC-USERS-014 Вход по email и паролю пользователя: сессия открыта, в шапке его ФИО
<!-- steps-hash: 8c485a42e685 -->
- Автотест: tests/ui/users/test_user_login_navigation.py::TestUserLoginNavigation::test_login_with_user_credentials
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | После входа мы не на странице авторизации | — |
| 2 | В шапке отображается ФИО пользователя | — |
| 3 | Раздел «Мое обучение» открывается | — |

### TC-USERS-015 В боковом меню отображаются кнопки пользователя с правильными ссылками
<!-- steps-hash: 3c9d993f1f32 -->
- Автотест: tests/ui/users/test_user_login_navigation.py::TestUserLoginNavigation::test_sidebar_buttons_displayed
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'Кнопка «{label}» → {href}' | — |
| 2 | f'Необязательная внешняя кнопка «{label}»' | — |

### TC-USERS-016 Переход по кнопкам меню: {label} → {href}
<!-- steps-hash: 4b675ef4098f -->
- Автотест: tests/ui/users/test_user_login_navigation.py::TestUserLoginNavigation::test_navigate_by_sidebar_button[education]
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'Нажать «{label}»' | — |
| 2 | Открылся нужный раздел, без 404, пользователь тот же | — |

### TC-USERS-017 Переход по кнопкам меню: {label} → {href}
<!-- steps-hash: 4b675ef4098f -->
- Автотест: tests/ui/users/test_user_login_navigation.py::TestUserLoginNavigation::test_navigate_by_sidebar_button[library]
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'Нажать «{label}»' | — |
| 2 | Открылся нужный раздел, без 404, пользователь тот же | — |

### TC-USERS-018 Переход по кнопкам меню: {label} → {href}
<!-- steps-hash: 4b675ef4098f -->
- Автотест: tests/ui/users/test_user_login_navigation.py::TestUserLoginNavigation::test_navigate_by_sidebar_button[portal-notifications]
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'Нажать «{label}»' | — |
| 2 | Открылся нужный раздел, без 404, пользователь тот же | — |

### TC-USERS-019 Переход по кнопкам меню: {label} → {href}
<!-- steps-hash: 4b675ef4098f -->
- Автотест: tests/ui/users/test_user_login_navigation.py::TestUserLoginNavigation::test_navigate_by_sidebar_button[support]
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'Нажать «{label}»' | — |
| 2 | Открылся нужный раздел, без 404, пользователь тот же | — |

### TC-USERS-020 Администратор проверяет роль 'Преподаватель' у пользователя
<!-- steps-hash: 38b2e44be6b5 -->
- Автотест: tests/ui/users/test_verify_role_ui.py::TestAdminVerifyRoleUI::test_admin_sees_teacher_role
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать пользователя и назначить роль teacher | — |
| 2 | 2. Логин под администратором | — |
| 3 | 3. Перейти в список пользователей | — |
| 4 | 4. Найти пользователя и открыть карточку | — |
| 5 | 5. Проверить роль | — |
