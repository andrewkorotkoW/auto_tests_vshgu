@echo off
REM Запуск автотестов с выбором окружения и allure-отчётом.
REM
REM Использование:
REM   scripts\run.bat --env develop
REM   scripts\run.bat --env stage -m "smoke and ui"
REM   scripts\run.bat --env prod -m smoke
REM
REM Результаты каждого запуска складываются в results\<env>\<timestamp>\ (это и есть
REM --alluredir), а history (для трендов между запусками) хранится отдельно на
REM каждое окружение в results\<env>\allure-history\ и переносится в/из него перед/после
REM генерации отчёта — так графики "было/стало" не путаются между develop/stage/prod.

setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0.."
pushd "%ROOT_DIR%"

set "ENV_NAME=develop"
set "MARK_EXPR="

:parse_args
if "%~1"=="" goto args_done
if "%~1"=="--env" (
    set "ENV_NAME=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="-m" (
    set "MARK_EXPR=%~2"
    shift
    shift
    goto parse_args
)
echo Неизвестный аргумент: %~1 1>&2
echo Использование: %~n0 --env ^<develop^|stage^|prod^> [-m "<expr>"] 1>&2
popd
exit /b 1

:args_done

for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TIMESTAMP=%%T"

set "RESULTS_ROOT=results\%ENV_NAME%"
set "ALLURE_RESULTS_DIR=%RESULTS_ROOT%\%TIMESTAMP%"
set "HISTORY_DIR=%RESULTS_ROOT%\allure-history"
set "REPORT_DIR=%RESULTS_ROOT%\allure-report"

if not exist "%ALLURE_RESULTS_DIR%" mkdir "%ALLURE_RESULTS_DIR%"

REM Подхватить историю прошлых запусков этого окружения, чтобы allure нарисовал тренд.
if exist "%HISTORY_DIR%\history" (
    mkdir "%ALLURE_RESULTS_DIR%\history" >nul 2>nul
    xcopy "%HISTORY_DIR%\history" "%ALLURE_RESULTS_DIR%\history" /e /i /y >nul
)

set "PYTEST_CMD=python -m pytest --env %ENV_NAME% --alluredir=%ALLURE_RESULTS_DIR%"
if not "%MARK_EXPR%"=="" set "PYTEST_CMD=%PYTEST_CMD% -m "%MARK_EXPR%""

echo Запуск: %PYTEST_CMD%
%PYTEST_CMD%
set "PYTEST_EXIT_CODE=%ERRORLEVEL%"

REM Найти allure CLI: либо в PATH, либо локально распакованный (см. .gitignore: allure-*\).
set "ALLURE_BIN="
where allure >nul 2>nul
if %ERRORLEVEL%==0 (
    set "ALLURE_BIN=allure"
) else (
    for /d %%D in (allure-*) do (
        if exist "%%D\bin\allure.bat" set "ALLURE_BIN=%%D\bin\allure.bat"
    )
)

if not "%ALLURE_BIN%"=="" (
    "%ALLURE_BIN%" generate --clean -o "%REPORT_DIR%" "%ALLURE_RESULTS_DIR%"
    REM Сохранить обновлённую историю обратно для следующего запуска этого окружения.
    if not exist "%HISTORY_DIR%" mkdir "%HISTORY_DIR%"
    if exist "%HISTORY_DIR%\history" rmdir /s /q "%HISTORY_DIR%\history"
    xcopy "%REPORT_DIR%\history" "%HISTORY_DIR%\history" /e /i /y >nul
    echo Отчёт: %REPORT_DIR%\index.html
) else (
    echo allure CLI не найден - отчёт не сгенерирован, результаты лежат в %ALLURE_RESULTS_DIR% 1>&2
)

popd
exit /b %PYTEST_EXIT_CODE%
