# Тест-кейсы: qr_code

| Параметр | Значение |
|---|---|
| Область | tests/api/qr_code |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-QR_CODE-001 GET /qr-code/generate → PNG персонального QR
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_generate_download.py::TestQrCodeGenerateDownload::test_generate_returns_png
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /qr-code/generate под авторизованным пользователем | 200, Content-Type image/png, Content-Disposition содержит my-qr-code.png, тело — валидный PNG (сигнатура \x89PNG) |

### TC-QR_CODE-002 GET /qr-code/download → PDF персонального QR
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_generate_download.py::TestQrCodeGenerateDownload::test_download_returns_pdf
- Приоритет: medium   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /qr-code/download под авторизованным пользователем | 200, Content-Type application/pdf, Content-Disposition содержит my-qr-code.pdf, тело — валидный PDF (сигнатура %PDF-) |

### TC-QR_CODE-003 Два разных пользователя получают два разных QR (разные токены)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_generate_download.py::TestQrCodeGenerateDownload::test_generate_is_personal_per_user
- Приоритет: medium   Тип: api   Роли: admin, user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | GET /qr-code/generate от admin, декодировать PNG (opencv QRCodeDetector) | Получен токен admin |
| 2 | Создать второго пользователя, залогиниться под ним, GET /qr-code/generate, декодировать PNG | Получен токен второго пользователя |
| 3 | Сравнить два токена | Токены разные — QR персональный для каждого пользователя |

### TC-QR_CODE-004 Анонимный запрос generate/download → 401
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_generate_download.py::TestQrCodeGenerateDownload::test_anon_gets_401[/qr-code/generate]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Анонимный (без сессии) GET /qr-code/generate | 401, message="Unauthenticated." |

### TC-QR_CODE-005 Анонимный запрос generate/download → 401
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_generate_download.py::TestQrCodeGenerateDownload::test_anon_gets_401[/qr-code/download]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Анонимный (без сессии) GET /qr-code/download | 401, message="Unauthenticated." |

### TC-QR_CODE-006 Полный цикл: generate -> decode QR -> parse-token возвращает свой user_id
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_parse_token.py::TestQrCodeParseToken::test_parse_token_full_round_trip_returns_own_user_id
- Приоритет: high   Тип: api   Роли: user
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Создать пользователя, залогиниться под ним | Сессия пользователя создана |
| 2 | GET /qr-code/generate, декодировать PNG (opencv QRCodeDetector) | Получен JWT-токен из QR |
| 3 | POST /qr-code/parse-token с этим токеном | 200, {"data": {"user_id": <id созданного пользователя>}} |

### TC-QR_CODE-007 Без token в конверте data.attributes → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_parse_token.py::TestQrCodeParseToken::test_parse_token_missing_field_422[payload0]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /qr-code/parse-token с пустым телом {} | 422, errors упоминает token / data.attributes.token |

### TC-QR_CODE-008 Без token в конверте data.attributes → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_parse_token.py::TestQrCodeParseToken::test_parse_token_missing_field_422[payload1]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /qr-code/parse-token с {"data": {}} (нет attributes) | 422, errors упоминает token / data.attributes.token |

### TC-QR_CODE-009 Без token в конверте data.attributes → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_parse_token.py::TestQrCodeParseToken::test_parse_token_missing_field_422[payload2]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /qr-code/parse-token с {"data": {"attributes": {}}} (нет token внутри attributes) | 422, errors упоминает token / data.attributes.token |

### TC-QR_CODE-010 Без token в конверте data.attributes → 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_parse_token.py::TestQrCodeParseToken::test_parse_token_missing_field_422[payload3]
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /qr-code/parse-token с {"token": "x"} — token вне конверта data.attributes | 422, errors упоминает token / data.attributes.token |

### TC-QR_CODE-011 Анонимный запрос parse-token → 401
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_parse_token.py::TestQrCodeParseToken::test_parse_token_anon_401
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Анонимный POST /qr-code/parse-token с {"data": {"attributes": {"token": "garbage"}}} | 401 |

### TC-QR_CODE-012 Невалидная структура токена — известный дефект (500 вместо 4xx)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_parse_token.py::TestQrCodeParseToken::test_parse_token_malformed_structure_is_validation_error
- Приоритет: medium   Тип: api   Роли: -
- Предусловия: Известный дефект: строка без двух точек (не JWT, например "garbage") в токене роняет ручку в HTTP 500 (необработанное исключение Lcobucci\JWT\Token\InvalidTokenStructure: "The JWT string must have two dots") вместо чистой ошибки валидации 400/422. Тест помечен ожидаемо неуспешным (xfail, strict=False), пока дефект не исправлен.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | POST /qr-code/parse-token с {"data": {"attributes": {"token": "garbage"}}} | Ожидалось 400/422; фактически — 500 с трейсом исключения (дефект) |

### TC-QR_CODE-013 Токен с произвольной подписью — известный дефект (подпись JWT не проверяется)
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/api/qr_code/test_qr_code_parse_token.py::TestQrCodeParseToken::test_parse_token_rejects_forged_signature
- Приоритет: high   Тип: api   Роли: -
- Предусловия: Подтверждённый дефект безопасности: POST /qr-code/parse-token не проверяет криптографическую подпись JWT. Самодельный токен вида header.payload.случайная-подпись с произвольным user_id в payload успешно парсится (200) и возвращает этот user_id, как будто подпись верна — подтверждено живым прогоном (в т.ч. реальный токен с добавленным мусорным байтом в конце подписи также проходит как валидный). Позволяет подделать QR-токен на произвольного пользователя. Тест помечен ожидаемо неуспешным (xfail, strict=False), пока дефект не исправлен.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Собрать токен header.payload.подпись с user_id=999999999 в payload и заведомо случайной (не-HMAC) подписью | Токен имеет корректную по форме структуру JWT (3 части через точку) |
| 2 | POST /qr-code/parse-token с этим поддельным токеном | Ожидался отказ 401/422 из-за неверной подписи; фактически — 200 с user_id=999999999 из payload (дефект) |
