# Тест-кейсы: tickets

| Параметр | Значение |
|---|---|
| Область | tests/api/tickets, tests/ui/tickets/user |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-TICKETS-001 POST /tickets от пользователя — обращение создаётся (200/201) и находится в my-tickets
<!-- steps-hash: 99b23aadbef8 -->
- Автотест: tests/api/tickets/test_tickets_crud_api.py::TestTicketsCrudApi::test_create_ticket
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать обращение POST /tickets — ответ 200/201 | — |
| 2 | Обращение найдено по теме в my-tickets — есть id (create не возвращает id) | — |

### TC-TICKETS-002 GET /tickets/my-tickets — созданное обращение имеет статус «открыто»
<!-- steps-hash: 4843f1709fd2 -->
- Автотест: tests/api/tickets/test_tickets_crud_api.py::TestTicketsCrudApi::test_new_ticket_is_open_in_my_tickets
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Обращение в my-tickets имеет статус open | — |

### TC-TICKETS-003 PUT /tickets/{id}/close — обращение закрывается, статус в my-tickets меняется на «закрыто»
<!-- steps-hash: e81596d4edcc -->
- Автотест: tests/api/tickets/test_tickets_crud_api.py::TestTicketsCrudApi::test_close_ticket
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Закрыть обращение PUT /tickets/{id}/close | — |
| 2 | В my-tickets статус обращения — closed | — |

### TC-TICKETS-004 Повторное PUT /tickets/{id}/close уже закрытого обращения — фиксируем фактический код
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/tickets/test_tickets_crud_api.py::TestTicketsCrudApi::test_repeat_close_is_rejected
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TICKETS-005 POST /tickets/{id}/messages в уже закрытое обращение — фиксируем фактический код
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/tickets/test_tickets_crud_api.py::TestTicketsCrudApi::test_message_to_closed_ticket_is_rejected
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TICKETS-006 POST /tickets/{id}/messages — сообщение добавляется (200); GET messages возвращает первое и добавленное сообщение в правильном порядке
<!-- steps-hash: 22bdfb95da2c -->
- Автотест: tests/api/tickets/test_tickets_messages_api.py::TestTicketsMessagesApi::test_add_message_and_order
- Приоритет: high   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | До добавления — в переписке одно (первое) сообщение с текстом обращения | — |
| 2 | Добавить сообщение POST /tickets/{id}/messages — ответ 200 | — |
| 3 | GET messages содержит оба сообщения, добавленное — вторым (после первого) | — |

### TC-TICKETS-007 POST /tickets с пустой темой — 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/tickets/test_tickets_negative_api.py::TestTicketsNegativeApi::test_create_empty_title
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TICKETS-008 POST /tickets с пустым текстом — 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/tickets/test_tickets_negative_api.py::TestTicketsNegativeApi::test_create_empty_text
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TICKETS-009 POST /tickets с пустым телом запроса — 422 с ошибками по всем обязательным полям
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/tickets/test_tickets_negative_api.py::TestTicketsNegativeApi::test_create_empty_payload
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TICKETS-010 GET /tickets/{id}/messages чужого обращения — ожидается 403/404, фиксируем фактический код
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/tickets/test_tickets_negative_api.py::TestTicketsNegativeApi::test_foreign_ticket_messages_forbidden
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TICKETS-011 PUT /tickets/{id}/close чужого обращения — ожидается 403/404, фиксируем фактический код
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/tickets/test_tickets_negative_api.py::TestTicketsNegativeApi::test_foreign_ticket_close_forbidden
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TICKETS-012 Пользователь создаёт обращение через форму, видит его в списке и своё сообщение в переписке
<!-- steps-hash: b3947e54017f -->
- Автотест: tests/ui/tickets/user/test_user_creates_ticket.py::TestUserCreatesTicket::test_user_creates_ticket_and_sees_it
- Приоритет: high   Тип: ui   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | 1. Открыть «Техподдержка» | — |
| 2 | 2. Создать обращение через форму | — |
| 3 | 3. Найти обращение через API (для надёжного teardown и id) | — |
| 4 | 4. Обращение появляется в списке (докручиваем до появления строки) | — |
| 5 | 5. Открыть переписку — своё сообщение видно | — |
