# Тест-кейсы: knowledge_base

| Параметр | Значение |
|---|---|
| Область | tests/api/knowledge_base, tests/ui/knowledge_base |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-KNOWLEDGE_BASE-001 API Develop: Загрузить Tincan-курс → создать материал в БЗ → переключить видимость
<!-- steps-hash: a971ea28dccf -->
- Автотест: tests/api/knowledge_base/test_create_course_baza_znanii.py::TestCourseMaterial::test_create_course_material_full_cycle
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Загрузить обложку и архив | — |
| 2 | 2. Создать курс Tincan | — |
| 3 | 3. Создать материал в базе знаний, привязанный к курсу | — |
| 4 | 4. Переключить видимость материала | — |
| 5 | Очистка данных | — |

### TC-KNOWLEDGE_BASE-002 UI: Администратор создаёт достижение «Количество материалов = 1 статья» с иконкой
<!-- steps-hash: bec044b8a946 -->
- Автотест: tests/ui/knowledge_base/test_create_achievement.py::TestCreateAchievement::test_create_achievement
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Проверить, что файл иконки подготовлен | — |
| 2 | 2. Открыть форму создания достижения | — |
| 3 | 3. Заполнить название, описание, загрузить иконку | — |
| 4 | 4. Добавить условие «Количество материалов»: тип «Статья», количество 1 | — |
| 5 | 5. Сохранить достижение | — |
| 6 | 6. Проверить, что достижение появилось в списке созданных | — |
| 7 | 7. Удалить достижение через API | — |

### TC-KNOWLEDGE_BASE-003 Create achievement material count for type
<!-- steps-hash: 6351d21a55d8 -->
- Автотест: tests/ui/knowledge_base/test_create_achievement.py::TestCreateAchievement::test_create_achievement_material_count_for_type[video]
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'1-6. Создать достижение с условием «Количество материалов»: тип «{MATERIAL_TYPE_TITLES[material_type]}», количество 1' | — |
| 2 | 7. Удалить достижение через API | — |

### TC-KNOWLEDGE_BASE-004 Create achievement material count for type
<!-- steps-hash: 6351d21a55d8 -->
- Автотест: tests/ui/knowledge_base/test_create_achievement.py::TestCreateAchievement::test_create_achievement_material_count_for_type[audio]
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'1-6. Создать достижение с условием «Количество материалов»: тип «{MATERIAL_TYPE_TITLES[material_type]}», количество 1' | — |
| 2 | 7. Удалить достижение через API | — |

### TC-KNOWLEDGE_BASE-005 Create achievement material count for type
<!-- steps-hash: 6351d21a55d8 -->
- Автотест: tests/ui/knowledge_base/test_create_achievement.py::TestCreateAchievement::test_create_achievement_material_count_for_type[book]
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'1-6. Создать достижение с условием «Количество материалов»: тип «{MATERIAL_TYPE_TITLES[material_type]}», количество 1' | — |
| 2 | 7. Удалить достижение через API | — |

### TC-KNOWLEDGE_BASE-006 Create achievement material count for type
<!-- steps-hash: 6351d21a55d8 -->
- Автотест: tests/ui/knowledge_base/test_create_achievement.py::TestCreateAchievement::test_create_achievement_material_count_for_type[file]
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'1-6. Создать достижение с условием «Количество материалов»: тип «{MATERIAL_TYPE_TITLES[material_type]}», количество 1' | — |
| 2 | 7. Удалить достижение через API | — |

### TC-KNOWLEDGE_BASE-007 Create achievement material count for type
<!-- steps-hash: 6351d21a55d8 -->
- Автотест: tests/ui/knowledge_base/test_create_achievement.py::TestCreateAchievement::test_create_achievement_material_count_for_type[course]
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | f'1-6. Создать достижение с условием «Количество материалов»: тип «{MATERIAL_TYPE_TITLES[material_type]}», количество 1' | — |
| 2 | 7. Удалить достижение через API | — |

### TC-KNOWLEDGE_BASE-008 UI: Администратор создаёт статью в базе знаний, слушатель видит её в «Базе знаний»
<!-- steps-hash: 22f135fd5e03 -->
- Автотест: tests/ui/knowledge_base/test_create_article_and_verify_in_user_ui.py::TestCreateArticleAndVerifyInUserUi::test_create_article_and_verify_in_user_ui
- Приоритет: medium   Тип: ui   Роли: admin, user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть форму создания материала в админке | — |
| 2 | 2. Выбрать тип материала «Статья» | — |
| 3 | 3. Заполнить название, короткое описание и текст статьи | — |
| 4 | 4. Сохранить статью | — |
| 5 | 5. Опубликовать статью (по умолчанию создаётся скрытой — is_visible=false) | — |
| 6 | 6. Проверить, что статья появилась в списке материалов админки | — |
| 7 | 7. Открыть «Базу знаний» под пользователем | — |
| 8 | 8. Найти созданную статью через поиск и открыть её | — |
| 9 | 9. Проверить заголовок статьи на странице материала | — |
| 10 | 10. Удалить статью через API | — |

### TC-KNOWLEDGE_BASE-009 UI: Администратор создаёт материал БЗ типа «Аудио»
<!-- steps-hash: e06b8d1cdaa4 -->
- Автотест: tests/ui/knowledge_base/test_create_material_audio.py::TestCreateMaterialAudio::test_create_material_audio
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть форму создания материала и выбрать тип «Аудио» | — |
| 2 | 2. Заполнить название, короткое описание и описание | — |
| 3 | 3. Указать длительность | — |
| 4 | 4. Загрузить аудиофайл | — |
| 5 | 5. Сохранить материал | — |
| 6 | 6. Проверить, что материал появился в списке материалов админки | — |
| 7 | 7. Удалить материал через API | — |

### TC-KNOWLEDGE_BASE-010 UI: Администратор создаёт материал БЗ типа «Книга»
<!-- steps-hash: 1a59d7d88515 -->
- Автотест: tests/ui/knowledge_base/test_create_material_book.py::TestCreateMaterialBook::test_create_material_book
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть форму создания материала и выбрать тип «Книга» | — |
| 2 | 2. Заполнить название, короткое описание и описание | — |
| 3 | 3. Загрузить файл книги | — |
| 4 | 4. Сохранить материал | — |
| 5 | 5. Проверить, что материал появился в списке материалов админки | — |
| 6 | 6. Удалить материал через API | — |

### TC-KNOWLEDGE_BASE-011 UI: Администратор создаёт материал БЗ типа «Курс» поверх курса Tincan
<!-- steps-hash: b82330743f81 -->
- Автотест: tests/ui/knowledge_base/test_create_material_course.py::TestCreateMaterialCourse::test_create_material_course
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Подготовить курс Tincan через API | — |
| 2 | 2. Открыть форму создания материала и выбрать тип «Курс» | — |
| 3 | 3. Выбрать подготовленный курс | — |
| 4 | 4. Сохранить материал | — |
| 5 | 5. Проверить, что материал появился в списке материалов админки | — |
| 6 | 6. Удалить материал через API | — |

### TC-KNOWLEDGE_BASE-012 UI: Администратор создаёт материал БЗ типа «Файл»
<!-- steps-hash: d389f688075e -->
- Автотест: tests/ui/knowledge_base/test_create_material_file.py::TestCreateMaterialFile::test_create_material_file
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть форму создания материала и выбрать тип «Файл» | — |
| 2 | 2. Заполнить название, короткое описание и описание | — |
| 3 | 3. Загрузить файл | — |
| 4 | 4. Сохранить материал | — |
| 5 | 5. Проверить, что материал появился в списке материалов админки | — |
| 6 | 6. Удалить материал через API | — |

### TC-KNOWLEDGE_BASE-013 UI: Администратор создаёт материал БЗ типа «Видео»
<!-- steps-hash: 83044947c527 -->
- Автотест: tests/ui/knowledge_base/test_create_material_video.py::TestCreateMaterialVideo::test_create_material_video
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть форму создания материала и выбрать тип «Видео» | — |
| 2 | 2. Заполнить название, короткое описание и описание | — |
| 3 | 3. Указать длительность | — |
| 4 | 4. Загрузить видеофайл | — |
| 5 | 5. Сохранить материал | — |
| 6 | 6. Проверить, что материал появился в списке материалов админки | — |
| 7 | 7. Удалить материал через API | — |
