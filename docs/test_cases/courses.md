# Тест-кейсы: courses

| Параметр | Значение |
|---|---|
| Область | tests/ui/courses/tincan/individual, tests/ui/courses/tincan/knowledge_base, tests/ui/courses/tincan/stream, tests/ui/courses/scorm/individual, tests/ui/courses/scorm/stream |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-COURSES-001 Пользователь проходит курс Tincan через инд. трек
<!-- steps-hash: fe3b68be9f35 -->
- Автотест: tests/ui/courses/tincan/individual/test_user_tincan_individual_flow.py::TestUserTincanIndividualFlow::test_user_tincan_individual
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать пользователя | — |
| 2 | 2. Создать курс | — |
| 3 | 3. Назначить курс на инд. трек | — |
| 4 | 4. Логин | — |
| 5 | 5. Открыть курс через инд. обучение | — |
| 6 | 6. Пройти курс | — |
| 7 | 7. Очистка | — |

### TC-COURSES-002 E2E Develop: Создание курса → материал в БЗ → UI: логин → база знаний
<!-- steps-hash: 86e651ef834b -->
- Автотест: tests/ui/courses/tincan/knowledge_base/test_knowledge_base_flow.py::TestKnowledgeBaseFlow::test_create_course_and_view_in_ui
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать пользователя | — |
| 2 | 2. Загрузить обложку и архив, создать курс Tincan | — |
| 3 | 3. Создать материал в базе знаний | — |
| 4 | 4. Логин | — |
| 5 | 5-6. Открыть «Базу знаний» и найти созданный материал через поиск | — |
| 6 | 7. Найти и открыть созданный материал | — |
| 7 | 8. Проверить элементы на странице материала | — |
| 8 | 9. Нажать «Приступить к изучению» | — |
| 9 | 10. Очистка данных | — |

### TC-COURSES-003 Пользователь проходит курс Tincan
<!-- steps-hash: 2213981711ea -->
- Автотест: tests/ui/courses/tincan/stream/test_user_tincan_flow.py::TestUserTincanFlow::test_user_open_tincan
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: API: создать → UI: логин → пройти курс.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать программу | — |
| 2 | 2. Создать поток | — |
| 3 | 3. Создать модуль | — |
| 4 | 4. Создать пользователя | — |
| 5 | 5. Назначить пользователя на поток | — |
| 6 | 6. Создать курс | — |
| 7 | 7. Логин | — |
| 8 | 8. Открыть курс и проверить данные | — |
| 9 | 9. Пройти курс | — |
| 10 | 10. Очистка | — |

### TC-COURSES-004 Слушатель проходит курс SCORM 2004 через инд. обучение
- Автотест: tests/ui/courses/scorm/individual/test_user_scorm_individual_flow.py::TestUserScormIndividualFlow::test_user_scorm_individual
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: через API созданы слушатель (онбординг закрыт) и курс SCORM 2004 из `test_data/test_lms_scorm_2004.zip` (Storyline: слайд с текстом → вопрос «Сколько углов у треугольника?», ответы «3»/«шланг»), курс назначен слушателю (`/users/content/distant/assign-activities`). Любое окружение — OpenLRS не нужен
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Логин слушателя → «Индивидуальное обучение» → вкладка «Курсы и тесты» → карточка курса | В карточке название курса с суффиксом клиента (`…_внешка`), срок, кнопка «Начать» |
| 2 | Нажать «Начать» | Новая вкладка `<portal>/xapi/drivers/scorm?xAPILaunchKey=<jwt>`, пакет в `iframe#iframe` (`/static/content/<uuid>/…/index_lms.html`), заголовок `tst_lms`, кнопки PREV/NEXT; драйвер шлёт `POST /xAPI/statements` initialized + launched |
| 3 | NEXT → выбрать «3» → SUBMIT → Continue | Слайд Results «Your Score: 100%»; в `POST /xAPI/statements` ушли responded (`result.response` = «3»), затем passed + completed |
| 4 | Прочитать SCORM API драйвера (`window.API_1484_11`) | `cmi.completion_status` = completed, `cmi.success_status` = passed, `cmi.score.raw` = 100, `cmi.score.scaled` = 1 |
| 5 | Закрыть вкладку плеера, обновить карточку | Кнопка «Повторить» (у начатого, но не завершённого курса была бы «Продолжить») |
| 6 | Очистка | Курс удалён (`mass-delete`), слушатель — фикстурой |

### TC-COURSES-005 Слушатель проходит курс SCORM 2004 в модуле программы
- Автотест: tests/ui/courses/scorm/stream/test_user_scorm_stream_flow.py::TestUserScormStreamFlow::test_user_scorm_stream
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: через API созданы программа → поток → модуль, слушатель назначен в поток, курс SCORM 2004 (как в TC-COURSES-004) назначен в модуль (`assign_to_module`). Любое окружение
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Логин слушателя → «Моё обучение» → карточка программы → «Перейти к программе» | Страница модуля `/education/program/<uuid>/module/<id>/activities`: шапка программы, строка модуля раскрыта, вкладка «Курсы и тесты» активна, карточка курса выбрана, справа название `…_внешка`, срок и «Начать» (2420, 27.10.2026). Если вкладки неактивны до раскрытия модуля — это дефект навигации из TC-COURSES-003 |
| 2–5 | Как в TC-COURSES-004, шаги 2–5 | Те же результаты: 100 %, SCORM completed/passed/100, statements, «Повторить» |
| 6 | Очистка | Курс удалён; программа/поток/модуль/слушатель — фикстурами |
