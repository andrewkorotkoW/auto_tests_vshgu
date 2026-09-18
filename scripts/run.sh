#!/usr/bin/env bash
# Запуск автотестов с выбором окружения и allure-отчётом.
#
# Использование:
#   scripts/run.sh --env develop
#   scripts/run.sh --env stage -m "smoke and ui"
#   scripts/run.sh --env prod -m smoke
#
# Результаты каждого запуска складываются в results/<env>/<timestamp>/ (это и есть
# --alluredir), а history (для трендов между запусками) хранится отдельно на
# каждое окружение в results/<env>/allure-history/ и переносится в/из него перед/после
# генерации отчёта — так графики "было/стало" не путаются между develop/stage/prod.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

ENV_NAME="develop"
MARK_EXPR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)
            ENV_NAME="$2"
            shift 2
            ;;
        -m)
            MARK_EXPR="$2"
            shift 2
            ;;
        *)
            echo "Неизвестный аргумент: $1" >&2
            echo "Использование: $0 --env <develop|stage|prod> [-m '<expr>']" >&2
            exit 1
            ;;
    esac
done

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RESULTS_ROOT="results/${ENV_NAME}"
ALLURE_RESULTS_DIR="${RESULTS_ROOT}/${TIMESTAMP}"
HISTORY_DIR="${RESULTS_ROOT}/allure-history"
REPORT_DIR="${RESULTS_ROOT}/allure-report"

mkdir -p "$ALLURE_RESULTS_DIR"

# Подхватить историю прошлых запусков этого окружения, чтобы allure нарисовал тренд.
if [[ -d "${HISTORY_DIR}/history" ]]; then
    mkdir -p "${ALLURE_RESULTS_DIR}/history"
    cp -r "${HISTORY_DIR}/history/." "${ALLURE_RESULTS_DIR}/history/"
fi

PYTEST_ARGS=(--env "$ENV_NAME" --alluredir="$ALLURE_RESULTS_DIR")
if [[ -n "$MARK_EXPR" ]]; then
    PYTEST_ARGS+=(-m "$MARK_EXPR")
fi

echo "Запуск: pytest ${PYTEST_ARGS[*]}"
set +e
python3 -m pytest "${PYTEST_ARGS[@]}"
PYTEST_EXIT_CODE=$?
set -e

# Найти allure CLI: либо в PATH, либо локально распакованный (см. .gitignore: allure-*/).
ALLURE_BIN=""
if command -v allure >/dev/null 2>&1; then
    ALLURE_BIN="allure"
else
    LOCAL_ALLURE="$(find "$ROOT_DIR" -maxdepth 1 -type d -name 'allure-*' 2>/dev/null | head -n1)"
    if [[ -n "$LOCAL_ALLURE" && -x "${LOCAL_ALLURE}/bin/allure" ]]; then
        ALLURE_BIN="${LOCAL_ALLURE}/bin/allure"
    fi
fi

if [[ -n "$ALLURE_BIN" ]]; then
    "$ALLURE_BIN" generate --clean -o "$REPORT_DIR" "$ALLURE_RESULTS_DIR"
    # Сохранить обновлённую историю обратно для следующего запуска этого окружения.
    mkdir -p "$HISTORY_DIR"
    rm -rf "${HISTORY_DIR}/history"
    cp -r "${REPORT_DIR}/history" "${HISTORY_DIR}/history"
    echo "Отчёт: ${REPORT_DIR}/index.html"
else
    echo "allure CLI не найден — отчёт не сгенерирован, результаты лежат в ${ALLURE_RESULTS_DIR}" >&2
fi

exit "$PYTEST_EXIT_CODE"
