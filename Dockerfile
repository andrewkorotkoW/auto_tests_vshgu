# Автотесты портала (API + UI) в контейнере.
# Базовый образ Playwright уже содержит Chromium и все системные зависимости;
# версия образа должна совпадать с playwright в requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HEADLESS=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /tests

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Результаты allure и кэш сессий выносятся наружу через volume (см. docker-compose.yml).
# VOLUME ["/tests/results", "/tests/.cache"]

# Без ENTRYPOINT: GitLab CI должен запускать в контейнере shell, а команда прогона задаётся явно.
# Локально: docker run … auto_tests_vshgu scripts/run.sh --env develop
# CMD ["scripts/run.sh", "--env", "develop"]
CMD ["/bin/bash"]