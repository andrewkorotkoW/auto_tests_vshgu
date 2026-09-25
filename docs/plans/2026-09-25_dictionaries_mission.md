# Разведка: справочники (develop)

Записано 25.09.2026. В админке нет отдельного пункта меню «Справочники» —
проверено обходом всего левого сайдбара `AdminPage.go_to_admin()` (Настройки
админа → Пользователи/роли, Статистика обучения, База Программ, База Активити,
База Пользователей, База Материалов, Практические задания, Уведомления,
Саморегистрация, Оценки и отзывы, Логи, Тестирование, Организации, Сертификаты,
Отчеты — нигде явного «Справочники»/«Категории»/«Направления» нет). Справочники
управляются точечно, изнутри форм, которые их используют: значения подгружаются
лениво по клику на конкретный select (см. комментарий в
`ui/pages/admin_programs_page.py:169` про «Стоимостная группа/Вид программы») —
поэтому на самой странице формы без клика по селекту сетевых запросов к
справочникам не видно вовсе.

## Как нашли реальные маршруты

Перехват сети Playwright (по аналогии с README §13 про `POST /notifications/create`):
поднял программу через `ProgramsEndpoint.create`, открыл
`/admin/programs/{id}/streams/create` под `admin_session`/storage_state, и по очереди
кликнул через `AdminProgramsPage._select_by_label` селекты «Проект», «Стоимостная
группа», «Подразделение реализации», «Вид программы», «Форма реализации» — каждый клик
на открытие лениво дёргает свой `GET /dictionaries/by-type/<type>`. Дальше методом проб
(`GET /dictionaries/by-type/<type>` для десятка кандидатов) нашёл ещё `region`/
`municipality` (поля формы пользователя) и подтвердил уже известный `tag` (темы вопросов
конструктора, `api/endpoints/question_bank.py`, единственное место в репозитории, где
`/dictionaries` уже использовался).

## Единый REST-ресурс `/dictionaries` (не набор разных сущностей)

Один Laravel-ресурс на бэкенде (`Dictionaries\Enums\DictionaryType` backing-enum),
общий для всех «типов» справочника — не отдельные CRUD на каждую сущность:

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/dictionaries/by-type/{type}?sort[0][name]=dictionary.name&sort[0][direction]=asc` | Полный отсортированный список по типу, без пагинации — им подгружаются опции select в формах |
| GET | `/dictionaries?filters[type]=<type>&filters[name]=<name>&per-page=&page=` | Постраничный список, фильтр по типу/имени |
| POST | `/dictionaries` `{"name": ..., "type": ...}` | Создание элемента |
| PATCH | `/dictionaries/{id}` `{"name": ...}` | Обновление (не PUT!) |
| DELETE | `/dictionaries/{id}` | Удаление, ответ `{"message": "Элемент справочника успешно удален"}` |

`GET /dictionaries/{id}` и `PUT /dictionaries/{id}` отвечают **405** («Supported
methods: PATCH, DELETE») — get-by-id для одного элемента не предусмотрен, что и
объясняет, зачем `list_by_type`/`find_by_name` ищут по типу+имени, а не по id.

## Найденные типы справочника и их связь с программами/пользователями

| `type` | Где используется в форме | Обязательность | Кол-во на develop |
|---|---|---|---|
| `project` | Поток программы, поле «Проект» | обязательное | 3 |
| `program_level` | Поток программы, поле «Стоимостная группа» | обязательное | 3 |
| `program_department` | Поток программы, поле «Подразделение реализации» | обязательное | 3 |
| `program_type` | Поток программы, поле «Вид программы» | обязательное | 3 |
| `learning_format` | Поток программы, поле «Форма реализации» | обязательное | 12 |
| `tag` | Тема вопроса конструктора тестов/опросов (уже покрыт `QuestionBankEndpoint`) | — | 3+ |
| `region` | Поле `region_id` формы пользователя (`generate_user_payload`) | обязательное | 89, read-only на develop |
| `municipality` | Поле `municipality_id` формы пользователя, `meta.region_id` привязывает к региону | обязательное | 173, read-only на develop |

`program_level`/`project` дополнительно несут `meta.experts_entity_id` (используется
как `experts_entity_name` в `generate_stream_payload`), `program_department` несёт
`tenant` (мультиарендность), `municipality` несёт `meta.region_id`/`meta.name` —
структура элемента зависит от типа, но реализована одним и тем же ресурсом.

`region`/`municipality` на develop не создавались тестами (это готовые справочники ФИАС
для формы пользователя) — CRUD-раунд-трип для отчёта задачи проверен на `program_type`
(см. ниже), но по коду ресурс общий для всех типов, отдельного эндпоинта на каждый не
требуется.

## Кандидат в дефекты

`POST /dictionaries` без поля `type` отвечает **500** (`"0" is not a valid backing
value for enum Dictionaries\Enums\DictionaryType`) вместо ожидаемой валидационной 422 —
сервер падает на приведении отсутствующего значения к enum до валидации. `POST` без
`name` корректно отвечает 422. Как и с другими найденными дефектами стенда — не
подгонять код клиента под это поведение, тесты (если решат покрыть этот кейс) должны
идти через `xfail(strict=False)`.

## Реализация

- `api/endpoints/dictionaries.py` — `DictionariesEndpoint`: `list_by_type`, `list`,
  `create`, `update`, `delete`, `find_by_name`.
- `api/helpers/data_generator.py` — `generate_dictionary_payload(dictionary_type=...,
  name=None)`: один общий генератор на все типы (ресурс один и тот же), имя с суффиксом
  `unique_suffix()` для безопасного параллельного запуска под pytest-xdist.

## Проверено

Одноразовый ad-hoc скрипт (не в репозитории) прогнал полный CRUD round-trip через
реальный `DictionariesEndpoint` на develop под `admin_session` для `type=program_type`:
`create` → `find_by_name` → `update` (PATCH) → `find_by_name` после обновления →
`list(filters[name])` → `delete` → `find_by_name` подтверждает отсутствие. Все шаги
прошли успешно, тестовый элемент за собой удалён.

Тесты (`tests/api/dictionaries/...`) в этой задаче не писались — по ТЗ их делает
dwight отдельно.

## Уточнение (задача UI Page Object, 25.09.2026)

Раздел «Справочники» в боковом меню админки **есть** — вывод выше о его отсутствии
неверен. Причина, почему обход сайдбара его не нашёл: у пункта «Справочники» нет
своего `href` — это `<div class="v-list-item__title">`, разворачивающий вложенный
список ссылок по клику (Vuetify `v-list-group`), а не `<a class="menu__item">`, как у
остальных пунктов верхнего уровня. Проверено вручную на develop: клик по заголовку
раскрывает 6 ссылок с полноценным CRUD (таблица + модалки создание/редактирование/
удаление, round-trip проверен через Page Object):

    /admin/catalogs/programs        «Вид программы»            program_type
    /admin/catalogs/forms           «Форма реализации»         learning_format
    /admin/catalogs/departments     «Подразделение реализации» program_department
    /admin/catalogs/regions         «Регионы»                  region
    /admin/catalogs/municipalities  «Муниципалитеты»           municipality
    /admin/catalogs/test-themes     «Темы вопросов»            tag

Типов `project` и `program_level` среди этих 6 ссылок нет — они по-прежнему только
через API, отдельной страницы в админке для них нет (это единственная часть исходного
вывода, которая подтвердилась). См. `ui/pages/admin_dictionaries_page.py`.
