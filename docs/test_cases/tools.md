# Тест-кейсы: tools

| Параметр | Значение |
|---|---|
| Область | tests/tools |
| Стенд | develop (см. README §13) |
| Роли | см. кейсы ниже |

<!-- Черновик сгенерирован tools/test_cases/generate.py. Ручные правки полей (Приоритет/Роли/Предусловия и т.п.) не перезаписываются повторным запуском. -->

### TC-TOOLS-001 Id parses known keys
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_id_parses_known_keys[body0-keys0-42]
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-002 Id parses known keys
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_id_parses_known_keys[body1-keys1-42]
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-003 Id parses known keys
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_id_parses_known_keys[body2-keys2-7]
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-004 Id parses known keys
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_id_parses_known_keys[body3-keys3-9]
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-005 Id prefers plain id over requested key
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_id_prefers_plain_id_over_requested_key
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: Ключ "id" в приоритете всегда, даже если явно запрошен другой ключ и он тоже есть — так и задумано в lib._id (порядок обхода: ("id",) + keys).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-006 Id falls back to top level when data is not a dict
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_id_falls_back_to_top_level_when_data_is_not_a_dict
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: Внешний CAS API иногда дублирует id на верхнем уровне, а "data" при этом список.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-007 Id raises when no id present
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_id_raises_when_no_id_present
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-008 Is conflict true for already exists 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_is_conflict_true_for_already_exists_422
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-009 Is conflict false for other 422
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_is_conflict_false_for_other_422
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-010 Is conflict false when status not in conflict statuses
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_is_conflict_false_when_status_not_in_conflict_statuses
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-011 Request tolerant conflict treated as success
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_request_tolerant_conflict_treated_as_success
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-012 Request tolerant raises on real error
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_request_tolerant_raises_on_real_error
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-013 Request tolerant ok status passthrough
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_request_tolerant_ok_status_passthrough
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-014 Resilient client retries until success
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_resilient_client_retries_until_success
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-015 Resilient client exhausts retries and returns last 5xx
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_resilient_client_exhausts_retries_and_returns_last_5xx
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: ResilientClient сам не бросает исключение — отдаёт последний ответ после исчерпания попыток (retries=2 -> 1 первая попытка + 2 повтора = 3 вызова).
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-016 Request tolerant raises after retries exhausted
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_request_tolerant_raises_after_retries_exhausted
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: Комбинация ResilientClient + request_tolerant: если все попытки вернули 5xx, итоговая ошибка всё-таки пробрасывается — уже на уровне request_tolerant.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-017 Manifest save load round trip
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_manifest_save_load_round_trip
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-018 Manifest load defaults when fields missing
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_manifest_load_defaults_when_fields_missing
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-019 Manifest path matches generate py convention
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_manifest_path_matches_generate_py_convention
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: test_data_generation/generate.py формирует путь как MANIFESTS_DIR / f"{env.name}_{scenario}_{int(time.time())}.json" — проверяем через сам generate.py (а не дублируем формат строкой), просто подменив MANIFESTS_DIR.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-020 Build clients dry run never opens a session
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_build_clients_dry_run_never_opens_a_session
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-021 Dry run scenario produces plan without network calls
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_lib.py::test_dry_run_scenario_produces_plan_without_network_calls
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: Прогон реального сценария (scenarios/users.py) в dry-run: подменяем requests.Session.request так, чтобы любой настоящий HTTP-вызов ронял тест, и убеждаемся, что сценарий всё равно строит план (манифест) через DryRunClient.
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-022 Compute area merges api and ui zones and handles edge cases
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_test_cases_generate.py::test_compute_area_merges_api_and_ui_zones_and_handles_edge_cases
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-023 Generates file per area with expected case ids and fields
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_test_cases_generate.py::test_generates_file_per_area_with_expected_case_ids_and_fields
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-024 Idempotent rerun without source changes
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_test_cases_generate.py::test_idempotent_rerun_without_source_changes
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-025 Manual edits to text fields survive rerun
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_test_cases_generate.py::test_manual_edits_to_text_fields_survive_rerun
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-026 Changed steps flag update without rewriting manual fields
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_test_cases_generate.py::test_changed_steps_flag_update_without_rewriting_manual_fields
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-027 New autotest appends next number without reordering
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_test_cases_generate.py::test_new_autotest_appends_next_number_without_reordering
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |

### TC-TOOLS-028 Adopts hand authored case without steps hash without flagging update
<!-- steps-hash: e3b0c44298fc -->
- Автотест: tests/tools/test_test_cases_generate.py::test_adopts_hand_authored_case_without_steps_hash_without_flagging_update
- Приоритет: medium   Тип: tools   Роли: -
- Предусловия: -
| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить сценарий автотеста | — |
