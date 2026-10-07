# Миссия (черновик, ждёт разговора владельца с девопсом): образ и CI под пайплайн платформы

Записано 07.10.2026. Контекст: девопс (Гриценко М.) сделал из устаревшего снимка `feature/ak_auto_tests`
ветку `main` в `qa/lms`, поправил Dockerfile/CI (без volume) и добавил наши джобы в `vshgu/lms/ci-cd`
(`.autotest.vshgu.yml`, закомментировано). Требования девопса: никаких volume при запуске; универсальный
набор переменных для iac-конфигов (сейчас файл `CI_AUTOTEST_ENV_FILE` содержит `DEVELOP_*`/`STAGE_*` для
одного ЦОДа). Актуальная ветка — `auto_tests_vshgu` (в `main` нет ~70 файлов тестов за октябрь); ветка
Игоря `feature/unify-autotest-architecture` влита в `auto_tests_vshgu` 07.10 (`5cf53e2`).

## Факты по пайплайну (ci-cd, ветка develop, 07.10)
- Стадии: prepare → deploy → stage → ui-tests → auto-test → cleanup. Наш файл `.autotest.vshgu.yml`
  подключается через `include: local` (закомментировано), джобы `tests:develop:api|ui`, `tests:stage`,
  `tests:prod-smoke`, все `when: manual`, `allow_failure: true`, раннер `devspark-builder` (shell), образ
  `git.devspark.ru:5005/edu-platform-instances/vshgu/qa/lms:main`, `GIT_STRATEGY: none`, `cd /tests`,
  `export $(grep -v '^#' $CI_AUTOTEST_ENV_FILE | xargs)`, `scripts/run.sh --env ${STAND} ${PYTEST_ARGS}`,
  артефакты `results/` + junit.
- Dockerfile на `main`: `VOLUME` закомментирован, `CMD ["/bin/bash"]`; `.gitlab-ci.yml` на `main`: docker
  executor (`image: $IMAGE`, тег `devspark-docker`), `run.sh` напрямую, артефакты `results/`.

## Что сделать
1. Перенести правки девопса (`origin/main`: коммиты 4ae4b46, efc1e27, 120dc7d, 426467b — Dockerfile и
   `.gitlab-ci.yml`) в `auto_tests_vshgu` (cherry-pick/ручной перенос, истории не связаны). Убрать
   `VOLUME` и `-v` везде, включая `docker-compose.yml` (оставить compose только для локального запуска с
   пометкой) и `docs/DEVOPS.md`. `.cache/` сессий — внутри контейнера (эфемерно), `results/` — артефакт.
2. Универсальный набор переменных для пайплайна (режим `--env stand`, расширение текущего `k8s`):
   обязательные `STAND_URL`, `STAND_COOKIE_NAME`, `ADMIN_LOGIN`, `ADMIN_PASSWORD`, `USER_LOGIN`,
   `USER_PASSWORD`; необязательные `STAND_API_URL`, `STAND_GLOBAL_URL`, `HELPDESK_URL`, `CAS_TOKEN`,
   `EXTERNAL_TOKEN`, `LPD_JWT`, `BUK_TOKEN`. Адреса API/global/helpdesk выводятся из `STAND_URL`
   (`portal-` → `global-`/`helpdesk-`), как в `config/environments.py` для `k8s`. Старые `DEVELOP_*`/`STAGE_*`
   остаются для локальной работы. Интеграционные тесты при пустом токене — skip с причиной, не fail.
3. `scripts/run.sh`: `--env stand` + переменные из окружения, без чтения `.env` в CI; код выхода pytest
   пробрасывать; `results/<env>/<ts>/` как сейчас.
4. `docs/DEVOPS.md`: раздел для девопса — список переменных с примером `CI_AUTOTEST_ENV_FILE`, как
   собрать образ, как запустить джобу, как читать артефакты; текст для `.autotest.vshgu.yml` (STAND=stand,
   STAND_URL из переменной деплоя). Указать, что `main` должен быть равен `auto_tests_vshgu`.
5. Проверка: `docker build` локально, `docker run` без volume с `--env stand` и `STAND_URL` develop,
   smoke-набор зелёный, артефакты внутри контейнера на месте; tests/tools зелёные.
6. После слияния — владелец просит девопса заменить `main` веткой `auto_tests_vshgu`.

## Правила
Только develop/k8s-стенды, прод не трогать. Учётки из `.env`, в код/доки/коммиты не писать. Отчёт —
`docs/reports/2026-10-07_ci_pipeline.md`.
