"""Локаторы разделов, которые открываются в тестах онбординга: «База знаний»
(вкладки «Библиотека»/«Избранное»), «Техподдержка», «Индивидуальное обучение».

Перенесены как плоские константы из src/ui/locators/{library,support,
personal_education}_locators.py коллеги (репозиторий lms, feature/my-tests, см.
report.md разд. 2) — единственный потребитель этих селекторов сейчас tests/ui/onboarding/,
поэтому полноценные Page Object для этих разделов не заводились.
"""

KB_LINK = "span.nav-item__text:has-text('База знаний')"
LIBRARY_TAB = "span:has-text('Библиотека')"
FAVORITES_TAB = "span:has-text('Избранное')"

SUPPORT_LINK = "xpath=//span[contains(@class,'nav-item__text') and normalize-space()='Техподдержка']"
SUPPORT_PLUS_ICON = "path#vac-icon-add"

PERSONAL_LINK = "a.individual-education-banner__link"
PERSONAL_SCHEDULE_TAB = "xpath=//span[contains(@class,'py-2') and normalize-space()='Расписание']"

MY_LEARNING_HEADING = "Мое обучение"
