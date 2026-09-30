"""Предполагаемый клиент API интеграции с МТС Линк — ветки/контракта ещё нет
(миссия `docs/missions/2026-09-30_tz2026_mts_link.md`, части 0–14 в
`docs/requirements/tz2026/mts_link/10_…`–`25_…`).

Методы построены по аналогии с уже существующими эндпоинтами очных мероприятий:
`api/endpoints/schedule_items.py` (create/get/delete элемента расписания — мероприятие
«МТС Линк» создаётся тем же способом, с `type="mts_link"` вместо `"webinar"`, см.
`api/helpers/data_generator.py:generate_schedule_item_payload` — контракт полей
create/content_type/url/teacher_ids/listeners/files/region подтверждён разведкой на
`--env develop`, только значение типа "mts_link" — предположение) и
`api/endpoints/external_buk.py` (асинхронная интеграция с фоновым статусом — оттуда
взят паттерн поллинга `wait_for_*`).

Разведка на develop (только чтение, без создания данных) также подтвердила структуру
карточки тенанта: `/admin/organization/{id}`, вкладки «Управление» (пользователи),
«Настройки» (брендинг), «Связь ОМТ КАС» (оргструктура) — блока интеграции МТС Линк там
сейчас нет ни на одной вкладке, и в репозитории нет ни одного SQL-хелпера к БД стенда
(`external_requests_audit`, упомянутый в требованиях к логированию, не реализован даже
для БУК) — поэтому `get_request_log_entries_via_sql` ниже поднимает понятную ошибку, а
не притворяется рабочим.

Каждый метод явно помечен docstring «контракт не подтверждён, часть N». Когда появится
реализация, метод нужно свести с реальным контрактом (путь/payload/статусы) — сигнатуру
можно менять.
"""
import os
import time
from typing import Dict, List, Optional

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger

MTS_LINK_EVENT_TYPE = "mts_link"

INTEGRATION_PARTS = ("creation", "webinar_data", "participants", "lecturers", "files")

SYNC_TERMINAL_STATUSES = {"success", "error"}

# Ограничения на файлы презентаций для вебинара (часть 5, раздел «Ограничения по файлам») —
# точные значения нигде не зафиксированы (МТС Линк API их не документирует в открытом
# доступе, в требованиях части 5 указано только «до отправки», без чисел) — используются
# как разумные дефолты для теста ошибочного сценария, подлежат уточнению у разработки.
MAX_PRESENTATION_FILE_SIZE_MB = 100
ALLOWED_PRESENTATION_EXTENSIONS = (".pdf", ".ppt", ".pptx")


class MtsLinkEndpoint:
    """Методы для работы с интеграцией МТС Линк поверх обычных очных мероприятий
    (элементов расписания, см. api/endpoints/schedule_items.py)."""

    def __init__(self, client: ApiClient):
        self.client = client

    # ── часть 0.1: настройки интеграции тенанта ──────────────────────────

    def get_tenant_settings(self, tenant_id: int) -> Dict:
        """Настройки интеграции МТС Линк в карточке тенанта. Токен в ответе должен
        быть замаскирован (11_часть_0.1…, раздел «Отображение токена»).

        Контракт не подтверждён, часть 0.1.
        """
        resp = self.client.get(f"/admin/organizations/{tenant_id}/mts-link-settings")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    def save_tenant_settings(self, tenant_id: int, token: Optional[str] = None, **other_fields):
        """Сохранить настройки интеграции тенанта. token=None — поле токена не
        передаётся в payload вовсе (правило «не тронули — остаётся прежним»,
        11_часть_0.1…, раздел «Правило редактирования»), а не передаётся пустой
        строкой. Статус ответа не проверяется здесь: у кейсов есть и позитивные
        (200), и негативные (400/401/403/422/503) ожидания — проверка в тесте.

        Контракт не подтверждён, часть 0.1.
        """
        attributes = dict(other_fields)
        if token is not None:
            attributes["token"] = token
        resp = self.client.put(
            f"/admin/organizations/{tenant_id}/mts-link-settings",
            json={"data": {"attributes": attributes}},
        )
        logger.info(f"Tenant {tenant_id}: save mts-link settings -> {resp.status_code}")
        return resp

    def get_tenant_integration_enabled(self, tenant_id: int) -> bool:
        """Признак «интеграция настроена и проверена» из карточки тенанта.

        Контракт не подтверждён, часть 0.1.
        """
        data = self.get_tenant_settings(tenant_id)
        return bool(data.get("attributes", {}).get("integration_configured"))

    # ── часть 0/1: создание мероприятия «МТС Линк» ───────────────────────

    def build_event_payload(self, **overrides) -> dict:
        """Payload очного мероприятия типа «МТС Линк» — тот же контракт, что у обычного
        элемента расписания (см. generate_schedule_item_payload, подтверждено
        разведкой), но type="mts_link" вместо "webinar", и url всегда пустой при
        создании (поле недоступно для заполнения, часть 0, раздел «Форма создания»).

        Контракт не подтверждён: значение type="mts_link" и его обработка бэкендом —
        часть 0/1.
        """
        from api.helpers.data_generator import generate_schedule_item_payload
        overrides.setdefault("item_type", MTS_LINK_EVENT_TYPE)
        overrides["url"] = ""
        return generate_schedule_item_payload(**overrides)

    def get_event_integration_data(self, schedule_item_id: int) -> Dict:
        """Сохранённые id вебинара/сессии и ссылка на мероприятие — часть 1, раздел
        «Результат».

        Контракт не подтверждён, часть 1.
        """
        resp = self.client.get(f"/schedule-item/{schedule_item_id}/mts-link")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    # ── часть 7: статусы интеграции (сводный + по 5 частям) ──────────────

    def get_integration_status(self, schedule_item_id: int) -> Dict:
        """Статусы интеграции мероприятия: сводный + по 5 частям (создание вебинара,
        данные вебинара, участники, лекторы, файлы презентаций) — часть 7, раздел
        «Карточка мероприятия». Ожидаемая форма: {"summary_status": ..., "parts":
        {"creation": ..., "webinar_data": ..., "participants": ..., "lecturers": ...,
        "files": ...}}.

        Контракт не подтверждён, часть 7.
        """
        resp = self.client.get(f"/schedule-item/{schedule_item_id}/mts-link/status")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    def get_part_status(self, schedule_item_id: int, part: str) -> Optional[str]:
        """Статус одной части синхронизации (см. INTEGRATION_PARTS).

        Контракт не подтверждён, часть 7.
        """
        return self.get_integration_status(schedule_item_id).get("parts", {}).get(part)

    def get_summary_status(self, schedule_item_id: int) -> Optional[str]:
        """Сводный статус мероприятия — «Ошибка», если хотя бы одна часть с ошибкой;
        «В процессе», пока хоть одна часть выполняется; «Успешно», когда все части
        успешны (часть 7, раздел «Состояния»).

        Контракт не подтверждён, часть 7.
        """
        return self.get_integration_status(schedule_item_id).get("summary_status")

    def wait_for_part_status(
        self,
        schedule_item_id: int,
        part: str,
        timeout: float = 60.0,
        poll_interval: float = 3.0,
    ) -> Optional[str]:
        """Поллинг статуса одной части синхронизации до терминального состояния
        («success»/«error», см. SYNC_TERMINAL_STATUSES) — общий помощник для всех
        асинхронных частей 1–6, 14. Таймаут/интервал — предположение (план, п.4,
        вопрос 5: точные интервалы автоматических ретраев не подтверждены разработкой).

        Контракт не подтверждён.
        """
        deadline = time.monotonic() + timeout
        last_status = None
        while time.monotonic() < deadline:
            last_status = self.get_part_status(schedule_item_id, part)
            logger.info(f"MTS Link event {schedule_item_id}: part={part} status={last_status}")
            if last_status in SYNC_TERMINAL_STATUSES:
                return last_status
            time.sleep(poll_interval)
        return last_status

    def wait_for_summary_status(
        self, schedule_item_id: int, timeout: float = 60.0, poll_interval: float = 3.0
    ) -> Optional[str]:
        """Поллинг сводного статуса мероприятия до терминального состояния.

        Контракт не подтверждён, часть 7.
        """
        deadline = time.monotonic() + timeout
        last_status = None
        while time.monotonic() < deadline:
            last_status = self.get_summary_status(schedule_item_id)
            if last_status in SYNC_TERMINAL_STATUSES:
                return last_status
            time.sleep(poll_interval)
        return last_status

    # ── часть 2: обновление данных вебинара ───────────────────────────────

    def update_event(self, program_id: int, stream_id: int, module_id: int, item_id: int, attributes: dict):
        """Обновление полей мероприятия. В api/endpoints/schedule_items.py метода
        обновления нет — PUT на тот же путь, что create, предполагается по REST-
        конвенции остальных сущностей потока (streams/modules).

        Контракт не подтверждён, часть 2.
        """
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/schedule-items/{item_id}",
            json={"data": {"attributes": attributes}},
        )
        logger.info(f"Schedule item {item_id}: update -> {resp.status_code}")
        return resp

    # ── часть 3/4: участники и лекторы ────────────────────────────────────

    def list_participants_sync_state(self, schedule_item_id: int) -> List[Dict]:
        """Состояние сверки состава слушателей: id участия, персональная ссылка,
        признак софт-делита — часть 3.

        Контракт не подтверждён, часть 3.
        """
        resp = self.client.get(f"/schedule-item/{schedule_item_id}/mts-link/participants")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def get_participant_sync_state(self, schedule_item_id: int, user_id: int) -> Optional[Dict]:
        """Состояние сверки одного слушателя.

        Контракт не подтверждён, часть 3.
        """
        for participant in self.list_participants_sync_state(schedule_item_id):
            if participant.get("user_id") == user_id:
                return participant
        return None

    def list_lecturers_sync_state(self, schedule_item_id: int) -> List[Dict]:
        """Состояние сверки состава лекторов (ведущих вебинара) — часть 4.

        Контракт не подтверждён, часть 4.
        """
        resp = self.client.get(f"/schedule-item/{schedule_item_id}/mts-link/lecturers")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def get_lecturer_sync_state(self, schedule_item_id: int, user_id: int) -> Optional[Dict]:
        """Состояние сверки одного лектора.

        Контракт не подтверждён, часть 4.
        """
        for lecturer in self.list_lecturers_sync_state(schedule_item_id):
            if lecturer.get("user_id") == user_id:
                return lecturer
        return None

    # ── часть 5: файлы презентаций ─────────────────────────────────────────

    def list_files_sync_state(self, schedule_item_id: int) -> List[Dict]:
        """Состояние сверки файлов презентаций, привязанных к вебинару — часть 5.

        Контракт не подтверждён, часть 5.
        """
        resp = self.client.get(f"/schedule-item/{schedule_item_id}/mts-link/files")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def validate_file_before_upload(self, file_path: str) -> Optional[str]:
        """Проверка формата/размера файла презентации до отправки в МТС Линк (часть 5,
        раздел «Ограничения по файлам») — возвращает текст ошибки с указанием файла, либо
        None, если файл проходит. Пороги — MAX_PRESENTATION_FILE_SIZE_MB/
        ALLOWED_PRESENTATION_EXTENSIONS, оба предположительны.

        Контракт не подтверждён, часть 5.
        """
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_PRESENTATION_EXTENSIONS:
            return f"Файл «{name}»: недопустимый формат {ext or '(без расширения)'}"
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
        except OSError as exc:
            return f"Файл «{name}»: не удалось прочитать размер ({exc})"
        if size_mb > MAX_PRESENTATION_FILE_SIZE_MB:
            return f"Файл «{name}»: размер {size_mb:.1f} МБ превышает лимит {MAX_PRESENTATION_FILE_SIZE_MB} МБ"
        return None

    def attach_file(self, program_id: int, stream_id: int, module_id: int, item_id: int, file_path: str):
        """Прикрепить презентацию к мероприятию — по аналогии с ApiClient.upload
        (multipart, см. api/client.py). Путь эндпоинта на существующих элементах
        расписания не подтверждён.

        Контракт не подтверждён, часть 5.
        """
        with open(file_path, "rb") as fh:
            resp = self.client.upload(
                f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/schedule-items/{item_id}/files",
                files={"file": fh},
            )
        logger.info(f"Schedule item {item_id}: attach file {file_path} -> {resp.status_code}")
        return resp

    # ── часть 6: удаление ──────────────────────────────────────────────────

    def get_deletion_audit(self, schedule_item_id: int) -> List[Dict]:
        """Записи request_log_audit по удалению вебинара/сессии — часть 6, раздел
        «Результат».

        Контракт не подтверждён, часть 6/10.
        """
        return self.get_request_log_entries(schedule_item_id=schedule_item_id, operation="delete")

    def wait_for_deletion(
        self, schedule_item_id: int, timeout: float = 60.0, poll_interval: float = 3.0
    ) -> List[Dict]:
        """Поллинг request_log_audit до появления успешной записи об удалении (вебинар +
        сессия) — часть 6, раздел «Результат»/«Поведение при ошибке» (ждём авторетрай).

        Контракт не подтверждён, часть 6.
        """
        deadline = time.monotonic() + timeout
        entries: List[Dict] = []
        while time.monotonic() < deadline:
            entries = self.get_deletion_audit(schedule_item_id)
            if any(e.get("success") for e in entries):
                return entries
            logger.info(f"Schedule item {schedule_item_id}: deletion not confirmed yet, retrying")
            time.sleep(poll_interval)
        return entries

    # ── часть 8: ручной перезапуск синхронизации ────────────────────────

    def retry_part(self, schedule_item_id: int, part: str) -> Dict:
        """Ручной перезапуск конкретной части синхронизации — кнопка «Повторить»
        доступна только у части в статусе «Ошибка» (часть 8, раздел «Флоу»).

        Контракт не подтверждён, часть 8.
        """
        resp = self.client.post(f"/schedule-item/{schedule_item_id}/mts-link/retry", json={"part": part})
        expect_status(resp, (200, 202))
        logger.info(f"MTS Link event {schedule_item_id}: retry part={part}")
        return resp.json()

    # ── часть 9: процент посещения ───────────────────────────────────────

    def get_listener_attendance(self, schedule_item_id: int, user_id: int) -> Dict:
        """Процент посещения слушателя по мероприятию «МТС Линк» — ячейка посещения
        в таблице слушателей потока (часть 9). Источник «фактической длительности
        вебинара» не назван в требованиях (план, п.6, вопрос 5) — форма ответа ниже
        предположительна: {"percent": int|None, "credited": bool}.

        Контракт не подтверждён, часть 9.
        """
        resp = self.client.get(f"/schedule-item/{schedule_item_id}/mts-link/attendance/{user_id}")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    # ── часть 10: логирование ────────────────────────────────────────────

    def get_action_log(self, entity_type: str, entity_id: int) -> List[Dict]:
        """Журнал действий пользователей (кто/когда изменил настройки тенанта или
        создал/изменил/удалил мероприятие) — часть 10, раздел «Что логируем», п.1–2.

        Контракт не подтверждён, часть 10.
        """
        resp = self.client.get(f"/admin/logs?entity_type={entity_type}&entity_id={entity_id}")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def get_request_log_entries(
        self,
        schedule_item_id: Optional[int] = None,
        operation: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Записи request_log_audit (запрос/ответ/признак успеха по операции обмена с
        МТС Линк) — часть 10, раздел «Что логируем», п.3. Первая попытка — через API;
        если отдельного API не появится, см. get_request_log_entries_via_sql (план,
        п.4, вопрос 4).

        Контракт не подтверждён, часть 10.
        """
        params = [f"limit={limit}"]
        if schedule_item_id is not None:
            params.append(f"filters[schedule_item_id]={schedule_item_id}")
        if operation is not None:
            params.append(f"filters[operation]={operation}")
        resp = self.client.get(f"/admin/mts-link/request-log-audit?{'&'.join(params)}")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def get_request_log_entries_via_sql(
        self,
        schedule_item_id: Optional[int] = None,
        operation: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """SQL-фоллбэк к таблице request_log_audit, если отдельного API не появится
        (план, п.4, вопрос 4). В требованиях к логированию упоминается идея такого
        хелпера «по аналогии с external_requests_audit в tests/api/buk», но в этом
        репозитории такого хелпера нет ни для одной интеграции (проверено — во всём
        tests/api/buk нет ни одного обращения к БД, только HTTP). Требует
        MTS_LINK_DB_DSN (.env.example) и установленный DB-драйвер — ни то, ни другое
        пока не настроено в проекте, поэтому метод сразу поднимает понятную ошибку
        вместо тихого падения где-то внутри SQL-запроса.

        Контракт не подтверждён, часть 10.
        """
        dsn = os.getenv("MTS_LINK_DB_DSN")
        if not dsn:
            raise NotImplementedError(
                "get_request_log_entries_via_sql: не задан MTS_LINK_DB_DSN (.env.example) — "
                "SQL-фоллбэк к request_log_audit ещё не настроен. Используйте "
                "get_request_log_entries (API), когда появится контракт (план, п.4, вопрос 4)."
            )
        try:
            import psycopg2  # локальный импорт: зависимость нужна только этому фоллбэку
        except ImportError as exc:
            raise NotImplementedError(
                "get_request_log_entries_via_sql: пакет psycopg2 не установлен — добавьте его "
                "в requirements.txt, когда станет известен реальный движок БД тестового стенда."
            ) from exc

        query = "SELECT * FROM request_log_audit WHERE 1=1"
        args: List = []
        if schedule_item_id is not None:
            query += " AND schedule_item_id = %s"
            args.append(schedule_item_id)
        if operation is not None:
            query += " AND operation = %s"
            args.append(operation)
        query += " ORDER BY created_at DESC LIMIT %s"
        args.append(limit)

        with psycopg2.connect(dsn) as conn, conn.cursor() as cursor:
            cursor.execute(query, args)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    # ── часть 11: запись вебинара ────────────────────────────────────────

    def get_recording_info(self, schedule_item_id: int) -> Dict:
        """Статус конвертации и ссылка на запись вебинара в «Результатах активности» —
        часть 0 (статус конвертации) и часть 11 (плеер, зачёт посещения по просмотру).

        Контракт не подтверждён, часть 0/11.
        """
        resp = self.client.get(f"/schedule-item/{schedule_item_id}/mts-link/recording")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    # ── часть 14: индивидуальная траектория ───────────────────────────────

    def get_it_webinar(self, assignment_id: int) -> Dict:
        """Вебинар, созданный фоном под конкретное назначение в индивидуальной
        траектории (один вебинар на назначение, один зарегистрированный слушатель) —
        часть 14.

        Контракт не подтверждён, часть 14.
        """
        resp = self.client.get(f"/individual-trajectory/assignments/{assignment_id}/mts-link")
        expect_status(resp, 200)
        return resp.json().get("data", {})
