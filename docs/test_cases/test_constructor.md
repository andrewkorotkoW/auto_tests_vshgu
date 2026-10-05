# Тест-кейсы: test_constructor

| Параметр | Значение |
|---|---|
| Область | tests/ui/test_constructor |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-TEST_CONSTRUCTOR-001 UI: Администратор создаёт тест и видит его в таблице конструктора
<!-- steps-hash: 4c1918e09a03 -->
- Автотест: tests/ui/test_constructor/test_01_admin_creates_test_and_sees_it_in_constructor_table.py::TestAdminCreatesTestAndSeesItInConstructorTable::test_admin_creates_test_and_sees_it_in_constructor_table
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть форму создания и создать тест | — |
| 2 | 2. Открыть таблицу конструктора и убедиться, что тест виден | — |
| 3 | 3. Удалить тест через API | — |

### TC-TEST_CONSTRUCTOR-002 UI: Администратор создаёт тест с дополнительным вопросом по теме
<!-- steps-hash: 796fb4b298f0 -->
- Автотест: tests/ui/test_constructor/test_02_admin_creates_test_with_additional_questions.py::TestAdminCreatesTestWithAdditionalQuestions::test_admin_creates_test_with_additional_questions
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать тему вопроса и тест, включить доп. вопросы | — |
| 2 | 2. Добавить дополнительный вопрос по теме (без группы) | — |
| 3 | 3. Привязать тему к основному вопросу и включить счётчик доп. вопросов | — |
| 4 | 4. Открыть тест в конструкторе и проверить дополнительный вопрос | — |

### TC-TEST_CONSTRUCTOR-003 UI: Администратор создаёт опрос и видит его в таблице конструктора
<!-- steps-hash: 02241e40d89e -->
- Автотест: tests/ui/test_constructor/test_03_admin_creates_poll_and_sees_it_in_constructor_table.py::TestAdminCreatesPollAndSeesItInConstructorTable::test_admin_creates_poll_and_sees_it_in_constructor_table
- Приоритет: high   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть форму создания и создать опрос | — |
| 2 | 2. Открыть таблицу конструктора и убедиться, что опрос виден | — |
| 3 | 3. Удалить опрос через API | — |

### TC-TEST_CONSTRUCTOR-004 UI: Администратор создаёт тему вопроса в каталоге
<!-- steps-hash: f0c6bce6a288 -->
- Автотест: tests/ui/test_constructor/test_04_admin_creates_question_theme_in_catalog.py::TestAdminCreatesQuestionThemeInCatalog::test_admin_creates_question_theme_in_catalog
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть каталог тем вопросов и создать тему | — |
| 2 | 2. Найти тему в списке и проверить строку | — |
| 3 | 3. Удалить тему через API | — |

### TC-TEST_CONSTRUCTOR-005 UI: Администратор переименовывает тему вопроса в каталоге
<!-- steps-hash: cad279970660 -->
- Автотест: tests/ui/test_constructor/test_05_admin_edits_question_theme_in_catalog.py::TestAdminEditsQuestionThemeInCatalog::test_admin_edits_question_theme_in_catalog
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать тему вопроса через API | — |
| 2 | 2. Найти тему в каталоге и переименовать | — |
| 3 | 3. Найти тему по новому имени и проверить строку | — |

### TC-TEST_CONSTRUCTOR-006 UI: Администратор видит конкуренцию основных вопросов за дополнительный
<!-- steps-hash: 096749b8fe3f -->
- Автотест: tests/ui/test_constructor/test_06_admin_sees_additional_question_competition.py::TestAdminSeesAdditionalQuestionCompetition::test_admin_sees_additional_question_competition
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать тему вопроса и тест, включить доп. вопросы | — |
| 2 | 2. Подготовить конкуренцию: доп. вопрос + два основных в одной группе | — |
| 3 | 3. Открыть тест в конструкторе и проверить конкуренцию за допвопрос | — |

### TC-TEST_CONSTRUCTOR-007 UI: Администратор добавляет вопрос из банка вопросов в тест
<!-- steps-hash: a76e85b03b89 -->
- Автотест: tests/ui/test_constructor/test_07_admin_adds_question_from_bank_to_test.py::TestAdminAddsQuestionFromBankToTest::test_admin_adds_question_from_bank_to_test
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать донорский тест и вопрос, добавить его в банк | — |
| 2 | 2. Создать целевой тест | — |
| 3 | 3. Открыть целевой тест в конструкторе и добавить вопрос из банка | — |

### TC-TEST_CONSTRUCTOR-008 UI: Слушатель проходит опрос по последовательности вопросов (ветвление по ответу)
<!-- steps-hash: b14646708c65 -->
- Автотест: tests/ui/test_constructor/test_08_listener_passes_poll_sequence_by_answer.py::TestListenerPassesPollSequenceByAnswer::test_listener_passes_poll_sequence_by_answer
- Приоритет: medium   Тип: ui   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать опрос, включить последовательность вопросов по ответам | — |
| 2 | 2. Создать целевую и пропускаемую группы с вопросами | — |
| 3 | 3. Настроить ветвление стартовой группы по ответам | — |
| 4 | 4. Пройти опрос: ответ должен перевести сразу в целевую группу | — |

### TC-TEST_CONSTRUCTOR-009 UI: Слушатель получает дополнительные вопросы после неверного ответа на основной
<!-- steps-hash: 0e044727aef8 -->
- Автотест: tests/ui/test_constructor/test_09_listener_gets_additional_question_after_wrong_answer.py::TestListenerGetsAdditionalQuestionAfterWrongAnswer::test_listener_gets_additional_question_after_wrong_answer
- Приоритет: medium   Тип: ui   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать тему вопроса и тест, включить доп. вопросы | — |
| 2 | 2. Подготовить основной вопрос с двумя дополнительными по теме | — |
| 3 | 3. Пройти тест: неверный основной → два дополнительных вопроса подряд | — |

### TC-TEST_CONSTRUCTOR-010 UI: Администратор видит прогресс слушателя без учёта доп. вопросов в статистике
<!-- steps-hash: 836688d8cdae -->
- Автотест: tests/ui/test_constructor/test_10_admin_sees_progress_without_additional_questions_in_statistics.py::TestAdminSeesProgressWithoutAdditionalQuestionsInStatistics::test_admin_sees_progress_without_additional_questions_in_statistics
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать тему вопроса и тест, включить доп. вопросы | — |
| 2 | 2. Подготовить основной вопрос с двумя дополнительными по теме | — |
| 3 | 3. Назначить тест слушателю через инд. трек | — |
| 4 | 4. Пройти тест: основной неверно → доп.1 верно → доп.2 неверно → завершить | — |
| 5 | 5. Проверить в статистике прогресс 0% без учёта доп. вопросов | — |

### TC-TEST_CONSTRUCTOR-011 UI: Администратор добавляет вопрос из банка вопросов в опрос
<!-- steps-hash: 048552f971cd -->
- Автотест: tests/ui/test_constructor/test_11_admin_adds_poll_question_from_bank_to_poll.py::TestAdminAddsPollQuestionFromBankToPoll::test_admin_adds_poll_question_from_bank_to_poll
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать донорский опрос и вопрос, добавить его в банк | — |
| 2 | 2. Создать целевой опрос | — |
| 3 | 3. Открыть целевой опрос в конструкторе и добавить вопрос из банка | — |

### TC-TEST_CONSTRUCTOR-012 UI: Администратор видит настройки последовательности вопросов опроса в конструкторе
<!-- steps-hash: 76ec6062ab0e -->
- Автотест: tests/ui/test_constructor/test_12_admin_sees_poll_sequence_settings_in_constructor.py::TestAdminSeesPollSequenceSettingsInConstructor::test_admin_sees_poll_sequence_settings_in_constructor
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать опрос, включить последовательность вопросов по ответам | — |
| 2 | 2. Создать целевую и пропускаемую группы с вопросами | — |
| 3 | 3. Настроить ветвление стартовой группы по ответам | — |
| 4 | 4. Открыть опрос в конструкторе и проверить настройки перехода | — |

### TC-TEST_CONSTRUCTOR-013 UI: Слушатель не получает следующий доп. вопрос после неверного ответа на предыдущий доп. вопрос
<!-- steps-hash: 78ed0fa3665c -->
- Автотест: tests/ui/test_constructor/test_13_listener_does_not_get_next_additional_question_after_wrong_additional_answer.py::TestListenerDoesNotGetNextAdditionalQuestionAfterWrongAdditionalAnswer::test_listener_does_not_get_next_additional_question_after_wrong_additional_answer
- Приоритет: medium   Тип: ui   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать тему вопроса и тест, включить доп. вопросы | — |
| 2 | 2. Подготовить основной вопрос с двумя дополнительными по теме | — |
| 3 | 3. Пройти тест: неверный основной → неверный первый доп. → тест завершается без второго доп. | — |

### TC-TEST_CONSTRUCTOR-014 UI: Слушатель завершает опрос с последовательностью, минуя группу с обязательным вопросом
<!-- steps-hash: 95e78b52062b -->
- Автотест: tests/ui/test_constructor/test_14_listener_finishes_poll_sequence_with_required_skipped_group.py::TestListenerFinishesPollSequenceWithRequiredSkippedGroup::test_listener_finishes_poll_sequence_with_required_skipped_group
- Приоритет: medium   Тип: ui   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать опрос, включить последовательность вопросов по ответам | — |
| 2 | 2. Создать целевую группу и обязательную пропускаемую группу | — |
| 3 | 3. Настроить ветвление стартовой группы по ответам | — |
| 4 | 4. Пройти опрос: ветка минует обязательную группу, завершение проходит без ошибок | — |

### TC-TEST_CONSTRUCTOR-015 UI: Администратор создаёт анкету обратной связи потока с последовательностью вопросов
<!-- steps-hash: 84a4d6115ce1 -->
- Автотест: tests/ui/test_constructor/test_15_admin_creates_feedback_with_sequence.py::TestAdminCreatesFeedbackWithSequence::test_admin_creates_feedback_with_sequence
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать АОС потока по двум мероприятиям | — |
| 2 | 2. Найти автосозданные группы мероприятий/дня | — |
| 3 | 3. Включить последовательность вопросов и настроить ветвление первой группы | — |
| 4 | 4. Проверить настройки последовательности в открытом конструкторе | — |
| 5 | 5. Активировать анкету на потоке | — |

### TC-TEST_CONSTRUCTOR-016 UI: Авторизованный слушатель проходит АОС потока по публичной ссылке с последовательностью вопросов
<!-- steps-hash: 15ade15c27f1 -->
- Автотест: tests/ui/test_constructor/test_16_authorized_listener_passes_feedback_by_link_with_expert_sequence.py::TestAuthorizedListenerPassesFeedbackByLinkWithExpertSequence::test_authorized_listener_passes_feedback_by_link_with_expert_sequence
- Приоритет: medium   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать АОС потока по двум мероприятиям | — |
| 2 | 2. Найти автосозданные группы мероприятий/дня | — |
| 3 | 3. Включить последовательность вопросов и настроить маршрут группа1 → группа2 → день | — |
| 4 | 4. Активировать АОС на потоке и получить публичную ссылку | — |
| 5 | 5. Назначить слушателя на поток и авторизовать | — |
| 6 | 6. Пройти АОС по маршруту группа1 → группа2 → день → завершение | — |

### TC-TEST_CONSTRUCTOR-017 UI: Авторизованный слушатель проходит АОС потока, минуя вторую группу вопросов
<!-- steps-hash: cdb3911f0c6a -->
- Автотест: tests/ui/test_constructor/test_17_authorized_listener_passes_stream_feedback_skipping_second_group.py::TestAuthorizedListenerPassesStreamFeedbackSkippingSecondGroup::test_authorized_listener_passes_stream_feedback_skipping_second_group
- Приоритет: medium   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать АОС потока по двум мероприятиям | — |
| 2 | 2. Найти автосозданные группы мероприятий/дня | — |
| 3 | 3. Настроить ветвление: из первой группы — напрямую в день, минуя вторую группу | — |
| 4 | 4. Активировать АОС на потоке и получить публичную ссылку | — |
| 5 | 5. Назначить слушателя на поток и авторизовать | — |
| 6 | 6. Пройти АОС: ветка минует вторую группу, завершение проходит без ошибок | — |

### TC-TEST_CONSTRUCTOR-018 UI: Администратор не может активировать АОС потока с недостижимой группой в последовательности
<!-- steps-hash: 540c9f57d2de -->
- Автотест: tests/ui/test_constructor/test_18_admin_cannot_activate_feedback_with_unreachable_sequence_group.py::TestAdminCannotActivateFeedbackWithUnreachableSequenceGroup::test_admin_cannot_activate_feedback_with_unreachable_sequence_group
- Приоритет: medium   Тип: ui   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Создать АОС потока по двум мероприятиям | — |
| 2 | 2. Найти автосозданные группы мероприятий/дня | — |
| 3 | 3. Настроить ветвление так, чтобы вторая группа осталась недостижимой | — |
| 4 | 4. Проверить в конструкторе, что вторая группа помечена недостижимой | — |
| 5 | 5. Проверить, что активация анкеты на потоке блокируется | — |
