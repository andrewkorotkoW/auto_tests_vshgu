# Миссия: перенос 11 тестов Игоря по достижениям + тест-кейсы в Test IT со скриншотами

Записано 25.09.2026. Источник — ветка `origin/feature/dashboard-autotests` (уже в локальном репозитории,
`git fetch` не нужен). Согласно README «Не перенесено», в нашем слое отсутствуют:

- `tests/ui/knowledge_base/user_achievements/test_01..09_*.py` — слушатель получает достижение за статью,
  аудио, видео, книгу, файл, курс (6) и три составных условия (аудио+книга, файл+книга, две книги).
- `tests/ui/knowledge_base/admin_statistics/test_01_admin_sees_user_achievement_history.py`,
  `test_02_admin_sees_user_in_knowledge_base_rating.py` — история достижений пользователя и рейтинг БЗ.

## Правила

- Только `--env develop`, `HEADLESS=1`. Stage/prod/ЛПД не трогать. Учётки и токены из `.env` через
  `config/environments.py`, значения не логировать и не коммитить.
- Переносить в наш слой, а не копировать как есть: наши фикстуры (`admin_page`, `user_page`,
  `api_client`, `env`), наши page objects (`ui/pages/admin_knowledge_base_page.py`,
  `user_knowledge_base_page.py`, `user_sidebar_page.py`), наши API-клиенты (`api/endpoints/knowledge_base.py`),
  подготовка данных через API (как в уже перенесённых `tests/ui/knowledge_base/test_create_*.py`),
  `dismiss_popups`, allure feature/story/title на русском, скриншот при падении.
- Хелперы коллеги (`tests/api/helpers/achievement_prepare_api.py`, `knowledge_base_material_prepare_api.py`,
  `cleanup_manager.py`) — брать логику, но класть в `api/endpoints/knowledge_base.py` /
  `api/helpers/`, не создавать второй слой хелперов в `tests/`.
- Каждый тест независим: своё достижение и материал с префиксом `Автотест_`, удаление в teardown через
  API даже при падении. Никаких хардкодов id.
- Расхождение поведения стенда с ожиданием теста — `xfail(strict=False)` с причиной и в отчёт как
  кандидат в дефекты, assert под факт не подгонять.

## Структура (как в дереве проекта)

```
tests/ui/knowledge_base/user_achievements/
  conftest.py                              # material_for_type(type), achievement_for(material…), teardown
  test_user_gets_achievement_by_material.py  # параметризация: article|audio|video|book|file|course (6)
  test_user_gets_complex_achievement.py      # audio+book, file+book, two_books (3)
tests/ui/knowledge_base/admin_statistics/
  test_admin_sees_user_achievement_history.py
  test_admin_sees_user_in_knowledge_base_rating.py
```

Итого 11 тестов (6 + 3 + 2). Запускать только их:
`pytest tests/ui/knowledge_base/user_achievements tests/ui/knowledge_base/admin_statistics --env develop -q`,
прогон приложить (стабильно 2 раза подряд).

## Тест-кейсы в Test IT (владелец разрешил заливку для этой миссии)

- Проект «ВШГУ v.3» (`TESTIT_URL`, `TESTIT_TOKEN`, `TESTIT_PROJECT_ID` из `.env`), секция
  **ВШГУ v.3 / База знаний / Достижения** (id `590ce0ad-3c5d-43ec-84f5-0ae257f038a5`) — там уже есть кейсы
  9720–9724, они эталон стиля. Ничего в них не менять.
- Стиль «ВШГУ v.2»: название 2–5 слов, описание пустое, предусловия отдельными строками, шаги
  «действие → ожидаемый результат» по реальному UI (вкладки, поля, кнопки как на экране), приоритет Medium,
  длительность 10 мин, состояние NotReady, тегов нет, **к автотестам не привязывать**.
- Скриншоты: снимать Playwright'ом на develop под тестовыми учётками (1440×900, полная страница, где нужно
  — с подсветкой строки/карточки), загружать `POST /api/v2/attachments` и вставлять в ожидаемый результат
  шага как `<p class="tiptap-text"><img src="/api/v2/Attachments/{id}" width="440" class="tiptap-image"></p>`,
  id вложения добавить в `attachments` кейса. Баннер cookie перед съёмкой закрыть.
- API: заголовок `Authorization: PrivateToken`, `POST /api/v2/workItems` (entityTypeName TestCases,
  steps/preconditionSteps в HTML `<p class="tiptap-text">`), поиск `POST /api/v2/workItems/search`
  с `filter.projectIds/sectionIds/isDeleted=false`. **Ловушка:** сервер часто отвечает 500, но кейс создаёт —
  перед повтором искать по имени в секции, иначе дубли. Скрипт съёмки и заливки положить в
  `tools/test_cases/achievements_cases.py` (идемпотентный, `--dry-run` по умолчанию, `--apply` для заливки).
- Кейсы (по одному на сценарий, 11 штук): «Слушатель получает достижение за <тип материала>» ×6,
  «Составное достижение: <условия>» ×3, «История достижений пользователя», «Пользователь в рейтинге базы
  знаний». В каждом: предусловия (какие материал и достижение созданы), шаги слушателя/админа, ожидаемое
  (карточка достижения в «Полученные достижения», уведомление «У Вас новое достижение», строка на вкладке
  «Достижения», позиция в «Рейтинг»), скриншоты ключевых экранов.

## Сдача

- 11 тестов зелёные или xfail с причиной, прогон приложен; README: раздел «Не перенесено» удалить, описать
  новые папки.
- 11 кейсов в Test IT созданы, в отчёте задачи — их номера и ссылка на секцию.
