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
        типов), `id`/`sort_order`/`weight` можно не передавать — сервер присваивает сам."""
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
          значения)."""
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

    def run_automatic_distribution(self, program_id: int, stream_id: int, module_id: int, stream_content_id: int, reviews_per_reviewer: int = 1) -> Dict:
        """Запуск автоматического распределения («Распределить» в модалке) —
        reviews_per_reviewer — подтверждённое имя поля (было: works_per_listener).
        «Первая проверка уже завершена — перераспределение недоступно» — повторный
        вызов после первой проверки должен отклоняться (не проверено).

        Подтверждено живьём 12.11.2026: метод — PUT, не POST (POST вернул 405, Laravel
        сообщил «Supported methods: PUT, PATCH, DELETE»). Тело запроса (плоское, по
        аналогии с save_peer_settings/assign_work_manually) ещё не подтверждено до конца —
        422/200 после смены метода не перепроверялся в этом заходе."""
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}"
            f"/contents/{stream_content_id}/peer-assignments/distribute",
            json={"reviews_per_reviewer": reviews_per_reviewer},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Stream content {stream_content_id}: automatic distribution started")
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

    def return_for_revision(self, work_id: int, reviewer_user_id: int, comment: str = "") -> Dict:
        """Возврат работы на доработку штатным проверяющим (04 §8.2 п.2). Слушатель-
        проверяющий не должен иметь доступа к этому действию — проверяется на уровне
        API-ответа (403/аналог), а не сокрытием кнопки.

        Контракт не подтверждён, раздел 8.
        """
        resp = self.client.post(
            f"/homework/{work_id}/return-for-revision",
            json={"data": {"attributes": {"reviewer_user_id": reviewer_user_id, "comment": comment}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Work {work_id}: returned for revision by {reviewer_user_id}")
        return resp.json()

    # ── §9: итоговый результат и агрегаты ────────────────────────────────────

    def get_peer_reviews_for_work(self, work_id: int) -> List[Dict]:
        """Все peer-проверки по работе — доступно штатному проверяющему ПЗ (04 §9, §3).

        Контракт не подтверждён, раздел 9.
        """
        resp = self.client.get(f"/homework/{work_id}/peer-reviews")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def get_aggregates(self, work_id: int) -> Dict:
        """Агрегированные значения по критериям: среднее по числовым (округление до
        0,1), текстовые — списком без агрегации (04 §5.1).

        Контракт не подтверждён, раздел 5.
        """
        resp = self.client.get(f"/homework/{work_id}/peer-reviews/aggregates")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    def set_final_result(self, work_id: int, reviewer_user_id: int, result: Dict) -> Dict:
        """Выставить/изменить итоговый результат по работе. По приоритетной версии (04)
        доступно любому штатному проверяющему этого ПЗ; администратор без такого
        назначения получает отказ (04 §9, §3 — роли).

        Контракт не подтверждён, раздел 9.
        """
        resp = self.client.put(
            f"/homework/{work_id}/final-result",
            json={"data": {"attributes": {"reviewer_user_id": reviewer_user_id, **result}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Work {work_id}: final result set by {reviewer_user_id}")
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

    def get_work_status(self, content_id: int, work_id: int) -> str:
        """Статус работы p2p-ПЗ (03 §8.2: «Не сдано» → «Сдано» → «На взаимопроверке» →
        «Взаимопроверка завершена, ожидает итогового результата» → «Итоговый результат
        выставлен»; 04 §10 подтверждает верхнеуровневый список). По аналогии с
        HomeworkEndpoint.get_status — тот же путь на уровне content/user, здесь на
        уровне work_id p2p-работы.

        Контракт не подтверждён, раздел 10.
        """
        resp = self.client.get(f"/content/{content_id}/peer-review/works/{work_id}/status")
        expect_status(resp, 200)
        data = resp.json().get("data", {})
        return data.get("attributes", {}).get("status") or data.get("status")

    def get_review_status(self, review_id: int) -> str:
        """Статус назначенной peer-проверки (03 §8: «Назначена» → «В процессе» →
        «Проверено», либо «Приостановлена» при возврате на доработку, либо «Отменена»,
        если проверка больше не требуется).

        Контракт не подтверждён, раздел 10.
        """
        resp = self.client.get(f"/peer-reviews/{review_id}/status")
        expect_status(resp, 200)
        data = resp.json().get("data", {})
        return data.get("attributes", {}).get("status") or data.get("status")
