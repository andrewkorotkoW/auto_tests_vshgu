"""Предполагаемый клиент API взаимопроверки ПЗ (p2p) — ветки/контракта ещё нет
(миссия `docs/missions/2026-09-30_tz2026_p2p.md`). Методы построены по аналогии с уже
существующими эндпоинтами практических заданий: api/endpoints/homework.py (создание,
mass_delete, examine, get_status), api/endpoints/homework_pass_fail.py и
homework_ten_point.py (create с фиксированным grade_type — здесь так же фиксируем
p2p-атрибуты в payload вместо отдельного эндпоинта на каждый вариант),
api/endpoints/assignments.py (assign/list_for_stream/change_state — назначения в поток и
статусы), api/endpoints/streams.py (create/get путь /programs/{id}/streams/{id}).

Каждый метод — предположение по приоритетной версии требований (04, см. README в
docs/requirements/tz2026/) и явно помечен docstring «контракт не подтверждён, раздел N»
(N — номер раздела документа 04). Ни один URL здесь не проверялся на реальном стенде —
функциональности ещё нет ни на одной ветке. Когда появится реализация, метод нужно
свести с реальным контрактом (эндпоинт/payload/статусы), сигнатуру можно менять.
"""
from typing import Dict, List, Optional

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger


class P2PEndpoint:
    """Методы для работы с взаимопроверкой практических заданий (p2p)."""

    def __init__(self, client: ApiClient):
        self.client = client

    # ── §4: карточка ПЗ — тумблер, штатные проверяющие ──────────────────────

    def enable_peer_review(self, content_id: int, enabled: bool = True) -> Dict:
        """ОПРОВЕРГНУТО живьём 12-13.11.2026 — НЕ ИСПОЛЬЗОВАТЬ. `PATCH /content/{id}/
        peer-review` не существует, и сама идея точечного включения после создания неверна:
        `peer_review_enabled` задаётся ТОЛЬКО в payload `POST /content` (см.
        generate_homework_payload(peer_review_enabled=True) в api/helpers/data_generator.py)
        и неизменяем после — подтверждено 13.11.2026 явной серверной ошибкой на `PUT
        /content/{id}`: «Нельзя изменить признак включения взаимопроверки после создания
        карточки.» (не просто задизейбленное поле в UI, серверная валидация). Метод оставлен
        для обратной совместимости вызовов в tests/api/p2p/*.py (conftest.py и 7+ тестовых
        файлов ещё используют его в предположении, что контракт когда-нибудь появится) — все
        они требуют переписи на передачу `peer_review_enabled=True` в `created_homework(...)`,
        как уже сделано в tests/ui/p2p/conftest.py::p2p_practical_task.
        """
        resp = self.client.patch(f"/content/{content_id}/peer-review", json={
            "data": {"attributes": {"enabled": enabled}}
        })
        expect_status(resp, (200, 201))
        logger.info(f"Homework {content_id}: peer-review enabled={enabled}")
        return resp.json()

    def update_peer_pass_threshold(self, content_id: int, peer_pass_threshold: int) -> Dict:
        """Обновить порог «зачёт/незачёт» карточки ПЗ (актуально только при
        grade_type=pass_fail — на других типах оценивания поле всегда null).

        Подтверждено живьём 13.11.2026: `PUT /content/{id}` с полным набором атрибутов
        (вернуть текущие attributes из GET, подменить peer_pass_threshold — поштучная
        частичная замена не проверялась) — поле РЕДАКТИРУЕМО после создания (в отличие от
        peer_review_enabled). При обновлении через PUT сервер отклоняет (422 «должно
        отсутствовать») read-only поля external_review_config_locked/peer_criteria_frozen
        в теле запроса — их нужно исключать перед отправкой, если формируете payload из
        ответа GET (как делает этот метод)."""
        current = self.client.get(f"/content/{content_id}").json()["data"]["attributes"]
        attributes = {k: v for k, v in current.items() if k not in (
            "created_at", "updated_at", "deleted_at", "files", "teachers", "inspectors", "iri",
            "external_review_config_locked", "peer_criteria_frozen",
        )}
        attributes["peer_pass_threshold"] = peer_pass_threshold
        resp = self.client.put(f"/content/{content_id}", json={"data": {"attributes": attributes}})
        expect_status(resp, 200)
        logger.info(f"Content {content_id}: peer_pass_threshold updated to {peer_pass_threshold}")
        return resp.json()

    def list_eligible_reviewers(self, content_id: int) -> List[Dict]:
        """Кандидаты в штатные проверяющие p2p-ПЗ (04 §4.2 — тот же пул, что и для
        обычного проверяющего ПЗ).

        Контракт не подтверждён, раздел 4.
        """
        resp = self.client.get(f"/content/{content_id}/peer-review/reviewers/eligible")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def assign_card_reviewers(self, content_id: int, user_ids: List[int]) -> Dict:
        """Назначить штатных проверяющих в карточке ПЗ (04 §4.2). По 04 §3.1 назначение
        должно автоматически выдавать роль «Преподаватель», если её ещё нет — это
        поведение сервера, клиент только отправляет назначение.

        Контракт не подтверждён, раздел 4.
        """
        resp = self.client.post(f"/content/{content_id}/peer-review/reviewers", json={
            "data": {"attributes": {"user_ids": user_ids}}
        })
        expect_status(resp, (200, 201))
        logger.info(f"Homework {content_id}: card reviewers assigned {user_ids}")
        return resp.json()

    # ── §5: конструктор критериев ────────────────────────────────────────────
    # 12.11.2026, живая разведка p2p-prototype (часть 01, через реальную форму
    # «Критерии оценки» на вкладке «Взаимопроверка» карточки ПЗ, /admin/activities/{id}):
    # опровергнута сама предпосылка путей ниже (content/{id}/peer-review/criteria НЕ
    # существует) — реальный корень неожиданно /homework/{content_id}/..., а не
    # /content/{content_id}/... Опровергнут и набор типов из плана (Шкала/Одиночный
    # выбор/Множественный выбор/Текстовое поле) — реальные 4 типа: quantitative
    # (0–100, как системная «Общая оценка», но доступен и для НОВЫХ критериев),
    # qualitative (текст/комментарий, аналог «Текстового поля»), single_choice,
    # multiple_choice. «Шкалы» с произвольным диапазоном как отдельного типа нет.

    def get_criteria(self, content_id: int) -> List[Dict]:
        """Подтверждено живьём 12.11.2026: GET /homework/{content_id}/peer-criteria ->
        {"data": [{id, type, title, sort_order, score_min, score_max, weight, options,
        is_system}]}. type ∈ {quantitative, qualitative, single_choice, multiple_choice}.
        Системная «Общая оценка»: type=quantitative, score_min=0, score_max=100,
        weight=None, is_system=True (её тип менять нельзя — подтверждено в UI). Остальные
        критерии: weight — доля от 0 до 1, сумма весов всех НЕ системных критериев = 1
        (автоматически распределяется поровну между критериями choice/quantitative, у
        которых есть вес — кнопка «Распределить поровну» в UI). options (только для
        single_choice/multiple_choice) — список {id: "opt-...", text, score}; score
        скрыт от проверяющего в форме оценки, виден только в этом admin-контракте.
        """
        resp = self.client.get(f"/homework/{content_id}/peer-criteria")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def set_criteria(self, content_id: int, criteria: List[Dict]) -> Dict:
        """Сохранить форму критериев целиком (полная замена). После первой полученной
        peer-проверки добавление/удаление критериев должно быть запрещено (04 §5.2, сам
        переход не проверен).

        Подтверждено живьём 13.11.2026 (прямой вызов, не через UI): `POST /homework/
        {content_id}/peer-criteria`, тело — `{"data": {"attributes": {"items": [...]}}}`
        (JSON:API-обёртка с ключом `items`, НЕ плоский список `{"data": [...]}`, как
        предполагалось раньше — именно так и выяснилось: 422 «Поле data.attributes.items
        должно присутствовать» на плоском теле). Элемент списка — как в ответе GET
        (type/title/score_min/score_max/is_system для quantitative; options для choice-
        типов), `id`/`sort_order` критерия можно не передавать — сервер присваивает сам.

        17.11.2026, уточнено живьём: у вариантов choice-критериев `options[].id` ОБЯЗАТЕЛЕН и
        задаётся клиентом (строка вида `opt-<slug>-N`; без него 422 «Поле ...options.0.id
        обязательно для заполнения, когда ...options указано»), а у взвешиваемых критериев
        (single_choice/multiple_choice с баллами) обязателен `weight` (422 «У взвешиваемого
        критерия нужен weight.») — сумма весов не системных критериев = 1."""
        resp = self.client.post(f"/homework/{content_id}/peer-criteria", json={"data": {"attributes": {"items": criteria}}})
        expect_status(resp, (200, 201))
        logger.info(f"Homework {content_id}: criteria saved ({len(criteria)} items)")
        return resp.json()

    # ── §2/§6: настройки p2p-ПЗ в потоке (участники, лимиты, дедлайн) ────────
    # 12.11.2026, живая разведка (p2p-prototype) через модалку «Взаимопроверка в
    # потоке» (иконка «люди» в колонке «Действия» на вкладке «Расписание» потока,
    # рядом с шестерёнкой редактирования — появляется только у content с
    # peer_review_enabled=true). РЕАЛЬНЫЙ корень пути — не "content/{content_id}",
    # а "modules/{module_id}/contents/{stream_content_id}" (это ДРУГОЙ id: привязка
    # контента К ПОТОКУ, не сам content_id карточки — см. get_stream_content).
    # Подтверждено только чтение (GET); payload сохранения («Сохранить настройки»,
    # «Распределить», «+ Добавить назначение») ещё не перехвачен — методы записи
    # ниже помечены отдельно.
    #
    # Также опровергнута сама идея «режима» распределения (set_distribution_mode
    # удалён): ручное и автоматическое распределение — не альтернативы, а два
    # ОДНОВРЕМЕННО доступных, дополняющих друг друга механизма (текст в модалке:
    # «Ручные назначения дополняют автоматическое распределение»). «Участников»
    # нельзя выбрать отдельным списком (set_stream_participants удалён) — во
    # взаимопроверке участвуют ВСЕ слушатели потока целиком («Во взаимопроверке
    # участвуют слушатели выбранного потока»), подмножество не выбирается.

    def get_stream_content(self, program_id: int, stream_id: int, module_id: int, stream_content_id: int) -> Dict:
        """Подтверждено живьём 12.11.2026: GET .../modules/{module_id}/contents/
        {stream_content_id} -> data.attributes.peer_settings — единый объект со всеми
        настройками взаимопроверки в потоке:
        {min_reviews_per_work, reviews_per_reviewer, peer_review_deadline_at,
        external_cert_reviews_threshold, external_cert_reviews_threshold_max, frozen,
        author_visibility: {author_see_comments, author_see_peer_breakdown,
        author_see_reviewer_names}, external_see_author_names, auto_final_grade_enabled}.
        stream_content_id — НЕ content_id карточки (см. docstring класса выше)."""
        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/contents/{stream_content_id}"
        )
        expect_status(resp, 200)
        return resp.json()["data"]

    def list_peer_assignments(self, program_id: int, stream_id: int, module_id: int, stream_content_id: int) -> List[Dict]:
        """Подтверждено живьём 12.11.2026: GET .../contents/{stream_content_id}/
        peer-assignments -> {"data": [...]} (пусто, пока распределения не было —
        форма записи элемента списка ещё не разведана)."""
        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}"
            f"/contents/{stream_content_id}/peer-assignments"
        )
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def save_peer_settings(
        self, program_id: int, stream_id: int, module_id: int, stream_content_id: int,
        min_reviews_per_work: int, reviews_per_reviewer: int, peer_review_deadline_at: str,
        author_see_comments: bool = True, author_see_reviewer_names: bool = False,
        author_see_peer_breakdown: bool = False, external_see_author_names: bool = False,
        **extra_fields,
    ) -> Dict:
        """Сохранить настройки взаимопроверки (кнопка «Сохранить настройки»).

        Подтверждено живьём 12.11.2026: тело запроса БЕЗ JSON:API-обёртки data/attributes —
        плоский `{"peer_settings": {...}}`, и сервер требует ВСЕ поля разом (PUT как полная
        замена, не точечный PATCH): min_reviews_per_work, reviews_per_reviewer,
        peer_review_deadline_at, author_visibility.{author_see_comments,
        author_see_reviewer_names, author_see_peer_breakdown}, external_see_author_names —
        без них 422. external_cert_reviews_threshold/_max/auto_final_grade_enabled/frozen
        необязательны (не было в списке обязательных) — extra_fields добавляет их при
        необходимости.

        13.11.2026, подтверждено живьём дополнительно:
        - `peer_review_deadline_at` обязан лежать СТРОГО в границах дат модуля
          (`date_from`..`date_to`) — проверено В ОБЕ СТОРОНЫ: и дата позже `date_to`, и дата
          раньше `date_from` одинаково дают 422 «Срок взаимопроверки должен лежать в границах
          дат модуля.».
        - `min_reviews_per_work`/`reviews_per_reviewer` (M/N) при СОЗДАНИИ stream_content
          всегда `1`/`1` (до первого вызова этого метода) — подтверждено ещё раз.
        - M/N свободно меняются ДО `peer_settings.frozen` (становится `true` после первого
          завершённого — `finalize_peer_review` — отзыва на эту работу в потоке, см.
          finalize_peer_review). ПОСЛЕ freeze попытка изменить M/N на ДРУГОЕ значение даёт 422
          «Нельзя изменить минимальное число проверок на работу или число проверок на
          проверяющего: настройки заморожены.» — остальные поля (проверено на
          author_visibility.*) остаются редактируемыми и после freeze, если M/N в теле
          совпадают с текущими (отправлять их нужно — поля обязательны, но без изменения
          значения).
        - 17.11.2026: `auto_final_grade_enabled` через этот PUT на ПЗ с `grade_type=five_point`
          НЕ принимается — 422 «Поле peer settings.auto final grade enabled должно
          отсутствовать» (в ответе GET поле есть, всегда false); где включается автоитог —
          не найдено (06_final_result.md)."""
        peer_settings = {
            "min_reviews_per_work": min_reviews_per_work,
            "reviews_per_reviewer": reviews_per_reviewer,
            "peer_review_deadline_at": peer_review_deadline_at,
            "author_visibility": {
                "author_see_comments": author_see_comments,
                "author_see_reviewer_names": author_see_reviewer_names,
                "author_see_peer_breakdown": author_see_peer_breakdown,
            },
            "external_see_author_names": external_see_author_names,
            **extra_fields,
        }
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}"
            f"/contents/{stream_content_id}/peer-settings",
            json={"peer_settings": peer_settings},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Stream content {stream_content_id}: peer_settings saved {peer_settings}")
        return resp.json()

    def assign_work_manually(self, program_id: int, stream_id: int, module_id: int, stream_content_id: int, author_user_id: int, reviewer_user_id: int) -> Dict:
        """Ручное назначение («+ Добавить назначение» в модалке) — дополняет
        автораспределение, не альтернатива ему.

        Подтверждено живьём 12.11.2026: назначение адресуется по автору работы
        (`author_user_id`), а не по id самой работы (`work_id` — неверная догадка, сервер
        ответил 422 «author_user_id/reviewer_user_id обязательны»). Тело — без JSON:API-
        обёртки, плоское `{"author_user_id": ..., "reviewer_user_id": ...}`."""
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}"
            f"/contents/{stream_content_id}/peer-assignments",
            json={"author_user_id": author_user_id, "reviewer_user_id": reviewer_user_id},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Author {author_user_id}'s work assigned to reviewer {reviewer_user_id} (manual)")
        return resp.json()

    def run_automatic_distribution(self, program_id: int, stream_id: int, module_id: int, stream_content_id: int) -> Dict:
        """Запуск автоматического распределения («Распределить» в модалке).

        17.11.2026: реальный путь найден в таблице именованных маршрутов стенда (`GET /routes`,
        `programs.streams.modules.contents.peer-assignments.redistribute`) — это
        `POST .../contents/{stream_content_id}/peer-assignments/redistribute`. Прежняя догадка
        `PUT .../peer-assignments/distribute` была неверной: сервер трактовал «distribute» как
        `{peer_assignment}` route-binding (под `/peer-assignments/{id}` живут PUT/PATCH/DELETE
        отдельного назначения). Тело запроса и ответ ЖИВЬЁМ НЕ ПРОВЕРЕНЫ (вызов на демо-данных
        переразложил бы назначения; «Первая проверка уже завершена — перераспределение
        недоступно» — после первой финализации кнопка в UI задизейблена, ожидаем 422).
        Параметры распределения берутся из peer_settings (reviews_per_reviewer), в теле ничего
        не предполагаем."""
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}"
            f"/contents/{stream_content_id}/peer-assignments/redistribute",
            json={},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Stream content {stream_content_id}: automatic (re)distribution started")
        return resp.json()

    # ── §3/§8: peer-проверка слушателем-проверяющим ─────────────────────────
    # 12.11.2026, живая разведка p2p-prototype (часть 04, с записью — assign_work_manually/
    # save_peer_settings подтверждены, run_automatic_distribution — нет, см. выше). Список
    # «чужих» работ и форма проверки живут НЕ под /programs/{program_id} (админский числовой
    # id), а под /my-programs/{program_uuid} (тот же UUID, что в адресной строке слушателя,
    # /education/program/{uuid}/...) — РАЗНЫЕ id-схемы для одной и той же программы: админ
    # использует числовой id, слушатель — uuid. module_id/stream_content_id — те же числовые
    # id, что и в админской части (02_stream_settings.md).

    def list_peer_submissions(self, program_uuid: str, module_id: int, stream_content_id: int) -> List[Dict]:
        """Подтверждено живьём 12.11.2026 (перехвачен реальный XHR страницы ПЗ слушателя):
        GET /my-programs/{program_uuid}/modules/{module_id}/contents/{stream_content_id}/
        peer-submissions?page=1&per_page=50 -> {"data": [{homework_answer_id, title,
        author_name, submitted_at, my_review_status, revision_status,
        peer_review_allowed}], "meta": {...}} — это и есть список «Назначенные
        взаимопроверки» (UI колонки «Работа»(=author_name)/«Сдана»/«Статус»)."""
        resp = self.client.get(
            f"/my-programs/{program_uuid}/modules/{module_id}/contents/{stream_content_id}/peer-submissions",
            params={"page": 1, "per_page": 50},
        )
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def get_peer_submission(self, program_uuid: str, module_id: int, stream_content_id: int, homework_answer_id: int) -> Dict:
        """Подтверждено живьём 12.11.2026: GET .../peer-submissions/{homework_answer_id} ->
        data: {homework_answer_id, title, author_name, submitted_at,
        homework_answers_history_id, text, student_file, criteria, review, revision_status,
        peer_review_allowed}. `criteria` — список критериев с их настройками для формы
        проверки (на ПЗ без явно заданных критериев — пустой список, тогда форма «Оценка»
        показывает только кнопки без полей — подтверждено живьём, не баг, просто нечего
        заполнять)."""
        resp = self.client.get(
            f"/my-programs/{program_uuid}/modules/{module_id}/contents/{stream_content_id}"
            f"/peer-submissions/{homework_answer_id}"
        )
        expect_status(resp, 200)
        return resp.json()["data"]

    @staticmethod
    def _peer_review_values_payload(values_by_criterion_id: Dict) -> List[Dict]:
        """Форма ОДНОГО элемента `values` подтверждена по ответу сервера (структура
        {peer_criterion_id, value}, список, не map). value по типу критерия: quantitative ->
        число (0..100), qualitative -> строка, single_choice -> id варианта (строка,
        напр. "opt-mwdx5unx-1"), multiple_choice -> список id вариантов."""
        return [{"peer_criterion_id": cid, "value": value} for cid, value in values_by_criterion_id.items()]

    def save_peer_review_draft(self, program_uuid: str, module_id: int, stream_content_id: int, homework_answer_id: int, values_by_criterion_id: Dict) -> Dict:
        """Кнопка «Сохранить черновик» — сохраняет без финального подтверждения,
        значения можно менять повторно (04 §8.1).

        Подтверждено живьём: POST /my-programs/{program_uuid}/modules/{module_id}/
        contents/{stream_content_id}/homework/answers/{homework_answer_id}/peer-reviews
        (БЕЗ /finalize — отдельный путь от finalize_peer_review ниже). Ответ: {"data": {id,
        status: "draft", homework_answer_id, homework_answers_history_id, assignment_id,
        finalized_at: null, values: [...]}}.

        13.11.2026 — ИСПРАВЛЕНО: тело запроса ВСЁ ЖЕ в JSON:API-обёртке
        `{"data": {"attributes": {"values": [...]}}}` (гипотеза о плоском `{"values": [...]}`
        из прошлого захода была ошибочной — выведена из формы ОТВЕТА, а не перехваченного
        реального запроса, и прямая проверка 13.11.2026 дала 422 «Поле data.attributes.values
        обязательно для заполнения» на плоском теле; с обёрткой сработало)."""
        resp = self.client.post(
            f"/my-programs/{program_uuid}/modules/{module_id}/contents/{stream_content_id}"
            f"/homework/answers/{homework_answer_id}/peer-reviews",
            json={"data": {"attributes": {"values": self._peer_review_values_payload(values_by_criterion_id)}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Peer review draft for homework_answer_id={homework_answer_id} saved")
        return resp.json()

    def finalize_peer_review(self, program_uuid: str, module_id: int, stream_content_id: int, homework_answer_id: int, values_by_criterion_id: Dict) -> Dict:
        """Кнопка «Завершить оценку» — диалог-предупреждение подтверждён дословно:
        «Оценка завершена. Изменить её можно будет после новой сдачи работы автором.» —
        блокировка УСЛОВНАЯ (до пересдачи автором), не навсегда, как предполагал
        TC-P2P-031. После завершения все поля формы показываются disabled с сохранёнными
        значениями и этим баннером вместо кнопок.

        Подтверждено живьём: POST .../homework/answers/{homework_answer_id}/peer-reviews/
        finalize. Ответ та же форма, что у save_peer_review_draft, но status="finalized" и
        finalized_at проставлен.

        13.11.2026 — ИСПРАВЛЕНО: тело запроса — JSON:API-обёртка `{"data": {"attributes":
        {"values": [...]}}}`, см. docstring save_peer_review_draft (та же история ошибки)."""
        resp = self.client.post(
            f"/my-programs/{program_uuid}/modules/{module_id}/contents/{stream_content_id}"
            f"/homework/answers/{homework_answer_id}/peer-reviews/finalize",
            json={"data": {"attributes": {"values": self._peer_review_values_payload(values_by_criterion_id)}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Peer review for homework_answer_id={homework_answer_id} finalized")
        return resp.json()

    def return_for_revision(self, content_id: int, homework_answer_id: int, deadline: str,
                            comment: str = "Вернуть на доработку") -> Dict:
        """Возврат работы на доработку штатным проверяющим (04 §8.2 п.2).

        Подтверждено живьём 17.11.2026: отдельного peer-эндпоинта нет (прежний стаб
        `/homework/{work}/return-for-revision` — догадка) — это штатный examination ПЗ:
        `POST /homework/{content_id}/answers/{homework_answer_id}/examination` с
        `status: "sent_back"` и ОБЯЗАТЕЛЬНЫМ `deadline` (YYYY-MM-DD). После: answer_status=sent_back
        (status=7), sent_back_count+1, у слушателей-проверяющих peer_review_allowed=false /
        revision_status="sent_back" до пересдачи автором (08_return_for_revision.md).
        Слушатель-проверяющий такого маршрута в /my-programs не имеет."""
        resp = self.client.post(
            f"/homework/{content_id}/answers/{homework_answer_id}/examination",
            json={"data": {"attributes": {"grade": "", "status": "sent_back", "deadline": deadline,
                                          "teacher_comment": comment}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Answer {homework_answer_id} (homework {content_id}): sent back for revision")
        return resp.json()

    def delete_peer_assignment(self, program_id: int, stream_id: int, module_id: int, stream_content_id: int, peer_assignment_id: int) -> None:
        """Снять назначение слушателя-проверяющего (TC-P2P-069). Подтверждено живьём 17.11.2026:
        `DELETE .../contents/{stream_content_id}/peer-assignments/{homework_peer_assignment_id}` →
        200 {"status":"success"}; у проверяющего работа пропадает из peer-submissions, черновик
        исчезает из агрегатов, finalize → 403 «Нет peer-назначения на проверку». Отдельного статуса
        «Отменена» нет — запись удаляется."""
        resp = self.client.delete(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}"
            f"/contents/{stream_content_id}/peer-assignments/{peer_assignment_id}"
        )
        expect_status(resp, 200)
        logger.info(f"Peer assignment {peer_assignment_id} deleted")

    # ── §9: итоговый результат и агрегаты ────────────────────────────────────
    # 17.11.2026, живая разведка p2p-prototype (06_final_result.md, 07_aggregation.md):
    # отдельных эндпоинтов «итог»/«агрегаты» НЕТ — агрегаты отдаёт `answers.peer-results`,
    # итог выставляется штатной проверкой ПЗ (`homework.answers.examination`,
    # api/endpoints/homework.py::examine). Прежние стабы get_peer_reviews_for_work /
    # get_aggregates / set_final_result (пути /homework/{work}/peer-reviews[/aggregates],
    # /homework/{work}/final-result) были неверной догадкой и удалены.

    def get_peer_results(self, content_id: int, homework_answer_id: int) -> Dict:
        """Подтверждено живьём 17.11.2026: `GET /homework/{content_id}/answers/{homework_answer_id}/
        peer-results` -> `data.attributes`: `viewer` ("staff" | "author" | "peer_reviewer" — зависит
        от того, кто спрашивает, и от author_visibility в peer_settings), `reviews` [{peer_review_id,
        reviewer_name, review_score, values[{peer_criterion_id, title, value}]}], `reviews_count`,
        `review_score_avg`, `criteria_stats` [{peer_criterion_id, title, type, is_system, avg,
        entries[{peer_review_id, reviewer_type, reviewer_id, value|text, score}], option_counts,
        options}]. Учитываются только финализированные проверки (черновики не входят).
        Все средние и `review_score` округлены до ЦЕЛОГО (70,5 -> 71; 3,5 -> 4), не до 0,1.
        `review_score` = сумма weight × score по взвешенным НЕ системным критериям; системная
        «Общая оценка» и качественные критерии в него не входят."""
        resp = self.client.get(f"/homework/{content_id}/answers/{homework_answer_id}/peer-results")
        expect_status(resp, 200)
        return resp.json().get("data", {}).get("attributes", {})

    def set_final_result(self, content_id: int, homework_answer_id: int, grade: str,
                         teacher_comment: str = "Итоговый результат по взаимопроверке") -> Dict:
        """Итоговый результат по работе = ШТАТНАЯ проверка ПЗ (подтверждено живьём 17.11.2026):
        `POST /homework/{content_id}/answers/{homework_answer_id}/examination`,
        `{"data":{"attributes":{"grade","status":"accepted","deadline":"","teacher_comment"}}}`.
        После него answer_status=accepted (status=2), отдельного статуса «Итоговый результат
        выставлен» нет; повторный вызов с другой оценкой меняет итог; peer-проверки по работе
        после этого финализировать уже нельзя (422 «Работа на доработке или уже принята»).
        Право на вызов — штатные права проверки ПЗ, а не «назначение проверяющим ПЗ» (админ вне
        списка teachers работы проходит) — расхождение с 04 §3/§9, см. 06_final_result.md."""
        resp = self.client.post(
            f"/homework/{content_id}/answers/{homework_answer_id}/examination",
            json={"data": {"attributes": {"grade": str(grade), "status": "accepted", "deadline": "",
                                          "teacher_comment": teacher_comment}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Answer {homework_answer_id} (homework {content_id}): final grade {grade} set")
        return resp.json()

    # ── §7: внешний проверяющий по ссылке ────────────────────────────────────

    def add_external_reviewer(self, program_id: int, stream_id: int, content_id: int, full_name: str, email: Optional[str] = None) -> Dict:
        """Добавить внешнего проверяющего к p2p-ПЗ в потоке (ФИО обязательно, email
        опционален, 04 §7 п.1–2). Несколько внешних с одинаковым ФИО — разные сущности,
        различаются по внутреннему идентификатору (04 §7 п.6–7), не по ФИО.

        Контракт не подтверждён, раздел 7.
        """
        payload = {"data": {"attributes": {"full_name": full_name}}}
        if email:
            payload["data"]["attributes"]["email"] = email
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/content/{content_id}/peer-review/external-reviewers",
            json=payload,
        )
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"External reviewer added: {full_name} (id={data.get('id')})")
        return data

    def get_external_reviewer_link(self, external_reviewer_id: int) -> str:
        """Персональная ссылка внешнего проверяющего (04 §7 п.3) — многоразовая по
        приоритетной версии 04 (расхождение с 03/05, см. README и 05_external_reviewer.md).

        Контракт не подтверждён, раздел 7.
        """
        resp = self.client.get(f"/peer-review/external-reviewers/{external_reviewer_id}")
        expect_status(resp, 200)
        return resp.json()["data"]["attributes"]["link"]

    def list_works_for_external_link(self, link_token: str) -> List[Dict]:
        """Список всех сданных работ ПЗ в потоке по персональной ссылке — без
        авторизации (04 §7 п.4). Используется отдельным HTTP-клиентом без сессионной
        куки (см. ui/pages/external_review_page.py — там это делается через отдельный
        browser context, здесь для API-проверок нужен клиент без Cookie/токена).

        Контракт не подтверждён, раздел 7.
        """
        resp = self.client.get(f"/peer-review/external/{link_token}/works")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    # ── §10: статусы работы и назначенной проверки ───────────────────────────

    def get_work_status(self, content_id: int, homework_answer_id: int) -> str:
        """Статус работы = answer_status обычного ПЗ (подтверждено 17.11.2026, 09_statuses.md):
        "on_review" (5) после сдачи/пересдачи, "sent_back" (7) после возврата, "accepted" (2) после
        итога. Peer-специфичных статусов работы («На взаимопроверке», «ожидает итога») нет;
        назначение проверяющих и набор min_reviews_per_work статус не меняют."""
        resp = self.client.get(f"/homework/{content_id}/answers/{homework_answer_id}")
        expect_status(resp, 200)
        return resp.json()["data"]["attributes"]["answer_status"]

    def get_review_status(self, program_uuid: str, module_id: int, stream_content_id: int, homework_answer_id: int) -> Optional[str]:
        """Статус назначенной проверки глазами слушателя-проверяющего (TC-P2P-067, подтверждено
        17.11.2026): поле my_review_status в peer-submissions — None (назначена, не начата) →
        "draft" (черновик) → "finalized" (завершена). Статусов «Приостановлена»/«Отменена» нет:
        на время возврата работы peer_review_allowed=false, снятое назначение просто исчезает."""
        for item in self.list_peer_submissions(program_uuid, module_id, stream_content_id):
            attrs = item.get("attributes") or item
            if attrs.get("homework_answer_id") == homework_answer_id:
                return attrs.get("my_review_status")
        return None
