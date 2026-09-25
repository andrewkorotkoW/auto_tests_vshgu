# Тест-кейсы: learning_statistics

| Параметр | Значение |
|---|---|
| Область | tests/api/learning_statistics, tests/ui/learning_statistics |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-LEARNING_STATISTICS-001 API: фильтр по потоку сужает строку статистики курса до нужного stream_id
<!-- steps-hash: 3f000e938c36 -->
- Автотест: tests/api/learning_statistics/test_courses_dashboard_filters.py::TestCoursesDashboardApiFilters::test_get_course_row_filters_by_stream_id
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 11. Строка курса находится по своему потоку | — |
| 2 | Строка НЕ находится по чужому потоку той же программы | — |

### TC-LEARNING_STATISTICS-002 API: фильтр filters[type][]=programs находит курс, назначенный через поток программы
<!-- steps-hash: 6d95ea216d37 -->
- Автотест: tests/api/learning_statistics/test_courses_dashboard_filters.py::TestCoursesDashboardApiFilters::test_get_course_row_type_programs_filter
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 12. filters[type][]=programs находит курс | — |
| 2 | filters[type][]=individual: курс всё ещё в списке (найден по имени), но с нулевыми показателями — назначения через поток программы в подсчёт инд. трека не попадают. Открытие: filters[type][] не исключает строку курса из выдачи (курс, найденный по filters[name], остаётся в data[]) — он только переключает, ПО КАКОМУ ТИПУ НАЗНАЧЕНИЙ считаются агрегаты total/not_started/passed/... в этой строке (изначально предполагалось, что несовпадающий тип уберёт курс из выдачи целиком — разведкой на develop это не подтвердилось). | — |

### TC-LEARNING_STATISTICS-003 UI: кнопка «Выгрузить» инициирует скачивание валидного xlsx
<!-- steps-hash: a530344f722a -->
- Автотест: tests/ui/learning_statistics/test_courses_export.py::TestCoursesExport::test_export_downloads_valid_xlsx
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 22. Открыть карточку курса и скачать отчёт | — |
| 2 | 23. Скачанный файл — валидный xlsx (ZIP-сигнатура, непустой) | — |

### TC-LEARNING_STATISTICS-004 UI: данные в выгрузке совпадают с таблицей слушателей на странице
<!-- steps-hash: 2c631c6e1e5c -->
- Автотест: tests/ui/learning_statistics/test_courses_export.py::TestCoursesExport::test_export_content_matches_listener_table
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть карточку курса, дождаться таблицы слушателей | — |
| 2 | 24. Скачать отчёт и сравнить состав строк/ФИО с таблицей UI | — |

### TC-LEARNING_STATISTICS-005 UI: повторная выгрузка после фильтрации содержит только отфильтрованные данные
<!-- steps-hash: a453878968fb -->
- Автотест: tests/ui/learning_statistics/test_courses_export.py::TestCoursesExport::test_export_after_filter_reflects_filtered_data
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выгрузка без фильтра — 2 строки слушателей | — |
| 2 | 24. Отфильтровать таблицу слушателей по email одного — выгрузка содержит только его | — |

### TC-LEARNING_STATISTICS-006 UI: поиск по названию курса в списке показывает только совпадающий курс
<!-- steps-hash: 4c6b48a51bd7 -->
- Автотест: tests/ui/learning_statistics/test_courses_filters.py::TestCoursesFilters::test_search_course_by_name
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 10. Найти курс по точному имени | — |

### TC-LEARNING_STATISTICS-007 UI: поиск по несуществующему названию курса — пустой список без ошибки
<!-- steps-hash: 6effcc119109 -->
- Автотест: tests/ui/learning_statistics/test_courses_filters.py::TestCoursesFilters::test_search_course_no_results
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 17. Поиск заведомо несуществующего курса — «Данные отсутствуют», без краша | — |

### TC-LEARNING_STATISTICS-008 UI: фильтр карточки курса — disabled-поля, комбинация «Программа + Поток», сброс
<!-- steps-hash: e401214b702e -->
- Автотест: tests/ui/learning_statistics/test_courses_filters.py::TestCoursesFilters::test_map_filter_disabled_states_combo_and_reset
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть карточку курса и фильтр карты | — |
| 2 | 10/13/14 preconditions. «Программы»/«Поток» задизейблены, пока не выбран тип | — |
| 3 | Выбор типа «Программы» включает поле «Программы», но не «Поток» | — |
| 4 | 16. Выбор программы включает «Поток»; фильтр на СВОЙ поток не меняет данные | — |
| 5 | Фильтр на ЧУЖОЙ поток той же программы обнуляет данные (узкая выборка) | — |
| 6 | 15. Сброс фильтра возвращает полные данные курса | — |

### TC-LEARNING_STATISTICS-009 UI: курс без слушателей — карта и таблица показывают «данных нет»
<!-- steps-hash: cc4084f942d1 -->
- Автотест: tests/ui/learning_statistics/test_courses_map.py::TestCoursesMapOverview::test_course_without_listeners_shows_empty_state
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1-2. Открыть карточку статистики курса без слушателей | — |
| 2 | 3-4. Карта присутствует, диаграммы нулевые, ни один регион не выбран | — |

### TC-LEARNING_STATISTICS-010 UI: курс со слушателями — диаграммы карты совпадают со значениями API
<!-- steps-hash: 73aecb8db358 -->
- Автотест: tests/ui/learning_statistics/test_courses_map.py::TestCoursesMapOverview::test_course_with_listeners_map_matches_api
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть карточку курса из списка | — |
| 2 | 2-3. Карта отрисована, диаграммы «Всего» совпадают с числом назначенных | — |
| 3 | 5. Определить регион(ы) с данными через API и выбрать его на карте | — |
| 4 | 6. При выбранном регионе вкладка меняется на «Графики»/«Таблица», % считается от общего | — |
| 5 | Вкладка «Таблица» региона совпадает с данными API карты | — |
| 6 | Повторный клик снимает выбор — карта возвращается к вкладке «Всего» | — |

### TC-LEARNING_STATISTICS-011 UI: переключение между курсами обновляет карту (не остаются данные предыдущего)
<!-- steps-hash: 2c84892d7753 -->
- Автотест: tests/ui/learning_statistics/test_courses_map.py::TestCoursesMapOverview::test_switching_course_updates_map
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 9. Открыть карту курса A, затем курса B — значения должны обновиться | — |

### TC-LEARNING_STATISTICS-012 UI: состав и порядок столбцов итоговой таблицы курса с разделами
<!-- steps-hash: 480fba1ad28e -->
- Автотест: tests/ui/learning_statistics/test_courses_table_columns.py::TestCoursesTableColumns::test_listener_table_columns_for_course_with_sections
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 18. Открыть карточку курса и дождаться таблицы слушателей | — |
| 2 | Состав и порядок столбцов совпадают с фактическим develop | — |

### TC-LEARNING_STATISTICS-013 UI: свеженазначенный, не начавший курс слушатель — пустые значения прогресса
<!-- steps-hash: a04086fd5d25 -->
- Автотест: tests/ui/learning_statistics/test_courses_table_columns.py::TestCoursesTableColumns::test_listener_row_for_freshly_assigned_user
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Открыть карточку курса и дождаться строки слушателя | — |
| 2 | 18. «Назначено»: пустая дата начала, прогресс 0%, прочерк в «Текущий раздел» | — |

### TC-LEARNING_STATISTICS-014 API: перевод назначения в статус «в процессе» недоступен на develop
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/ui/learning_statistics/test_courses_table_progress.py::TestCoursesTableProgress::test_status_in_progress_via_api
- Приоритет: medium   Тип: ui   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-LEARNING_STATISTICS-015 API+UI: статус «пройдено» и прогресс 100% после смены статуса назначения
<!-- steps-hash: 5f3399135c9e -->
- Автотест: tests/ui/learning_statistics/test_courses_table_progress.py::TestCoursesTableProgress::test_status_passed_updates_after_change_state
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 20. Перевести назначение в «Пройдено» через API | — |
| 2 | Карточка курса: статус «Пройдено», прогресс 100% | — |

### TC-LEARNING_STATISTICS-016 UI: «Время прохождения, мин» не заполняется без реального прохождения курса
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/ui/learning_statistics/test_courses_table_progress.py::TestCoursesTableProgress::test_completion_time_reflects_real_duration
- Приоритет: low   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |
