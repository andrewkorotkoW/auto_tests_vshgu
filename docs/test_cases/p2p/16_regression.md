# Тест-кейсы: p2p / регресс обычного ПЗ

| Параметр | Значение |
|---|---|
| Область | tests/api/p2p, tests/ui/p2p (регресс существующего сценария ПЗ при выключенной взаимопроверке) |
| Стенд | develop (см. README §13) |
| Роли | admin, reviewer, user |

Опора на существующие тесты ПЗ (не менялись): `tests/ui/practical_tasks/test_complete_practical_task.py`,
`tests/ui/practical_tasks/test_review_practical_task.py`,
`tests/ui/practical_tasks/groups/test_group_practical_task_flow.py`,
`tests/ui/practical_tasks/personal_assignment/test_complete_and_review_personal_assignment.py`.

### TC-P2P-108 ПЗ с выключенной взаимопроверкой сдаётся и проверяется по прежнему сценарию
- Требование: 04 §1
- Автотест: tests/ui/p2p/test_regression.py::TestRegression::test_homework_without_p2p_keeps_standard_flow
- Приоритет: high   Тип: ui   Роли: user, reviewer
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать обычное ПЗ без включения «Включить взаимопроверку», назначить в поток | ПЗ назначено |
| 2 | Слушатель сдаёт работу, штатный проверяющий проверяет её без участия peer-проверок | Сценарий проходит как до появления взаимопроверки (как в test_complete_practical_task.py / test_review_practical_task.py) |

### TC-P2P-109 Групповое ПЗ проходит стандартный сценарий проверки без взаимопроверки
- Требование: 02 п.4
- Автотест: tests/ui/p2p/test_regression.py::TestRegression::test_group_homework_keeps_standard_flow_without_p2p
- Приоритет: medium   Тип: ui   Роли: user, reviewer
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать групповое ПЗ, назначить в поток и группу | ПЗ назначено |
| 2 | Пройти стандартный сценарий группового ПЗ (как в test_group_practical_task_flow.py) | Сценарий не затронут появлением P2P-функциональности |

### TC-P2P-110 Индивидуальное назначение ПЗ проходит стандартный сценарий без взаимопроверки
- Требование: 04 §1
- Автотест: tests/api/p2p/test_regression.py::TestRegression::test_personal_assignment_keeps_standard_flow_without_p2p
- Приоритет: medium   Тип: api   Роли: user, reviewer
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Назначить ПЗ пользователю напрямую (без потока), без включения взаимопроверки | Назначение создано |
| 2 | Пройти сдачу и проверку (как в test_complete_and_review_personal_assignment.py) | Сценарий не затронут |

### TC-P2P-111 Ограничение «одно и то же ПЗ нельзя назначить в поток/программу дважды» не меняется
- Требование: 03 §6
- Автотест: tests/api/p2p/test_regression.py::TestRegression::test_single_homework_per_program_restriction_unchanged
- Приоритет: medium   Тип: api   Роли: admin
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Назначить P2P-ПЗ в поток программы | Назначение создано |
| 2 | Попытаться повторно назначить то же ПЗ в другой поток той же программы | Ограничение действует так же, как для обычного ПЗ — без изменений |
