"""Клиент API интеграции с МТС Линк поверх обычных очных мероприятий (элементов
расписания, см. api/endpoints/schedule_items.py).

Статус/обновление/вложения (часть этого файла, что реально используется
tests/{api,ui}/mts_link/*) сведены с реальным контрактом живой разведкой 02.11.2026
(создание+редактирование настоящих вебинаров на стенде mts-link-release-main):

- Статус интеграции — НЕ отдельный эндпоинт. Все варианты вида
  `/schedule-item/{id}/mts-link...` (…/status, …/participants, …/lecturers, …/files,
  …/attendance/{uid}, …/retry, а также голый …/mts-link) и `/admin/mts-link/
  request-log-audit`, `/admin/logs` — подтверждённо 404 (прямыми вызовами, несколько
  раз). Реальный статус лежит полем `attributes.mts_link` в обычном ответе
  `GET .../schedule-items/{id}` (ScheduleItemsEndpoint.get, уже рабочий путь):
      {
        "mts_webinar_id": int,
        "webinar_status": "syncing" | "synced" | "finished" (после «Завершить мероприятие»
                           в МТС Линк, 03.11.2026) | вероятно "error" (не подтверждено),
        "record_status": "pending" | "in_progress" | "success" (04.11.2026, ~3 ч после
                          recordFile.ready),
        "record_link": str | None — ссылка на mp4 в хранилище МТС Линк
                       (events-storage.webinar.ru), НЕ в ЛМС; копия записи в ЛМС лежит
                       в attributes.results_activities[].material.file.url (/static/…),
        "participants_sync_status": "pending" | "success" | вероятно "error",
        "lecturers_sync_status": тот же набор значений,
        "files_sync_status": тот же набор значений,
        "stats_sync_status": тот же набор значений,
      }
  Значения "syncing"/"synced"/"finished" у webinar_status, "pending"/"in_progress"/"success"
  у record_status (конвертация записи после recordFile.ready) и "pending"/"success" у остальных
  подтверждены живьём (несколько снэпшотов); "error" — по аналогии и по наличию
  кнопки «Повторить синхронизацию» в форме редактирования, НЕ пойман живьём (не
  вышло стабильно спровоцировать ошибку синхронизации на реальном проде).//
- НЕТ детализации по отдельным участникам/лекторам (ни личной ссылки, ни роли,
  ни признака синка) — только агрегированные *_sync_status выше. listeners в
  attributes самого элемента расписания остаётся пустым массивом даже после
  успешной сверки участников (проверено живьём) — это не список синхронизированных
  участников МТС Линк.
- Обновление элемента (часть 2) — `PUT .../schedule-items/{id}` требует ПОЛНЫЙ
  payload (как при создании), частичный `{"data":{"attributes": {...только
  изменённое...}}}` падает 500/422 (не хватает обязательных полей вроде `type`).
  update_event() ниже сам подтягивает текущие атрибуты и мёрджит их перед PUT —
  вызывающий код как раньше передаёт только то, что хочет изменить.
- Файлы презентаций (часть 5) — НЕТ эндпоинта `.../schedule-items/{id}/files`.
  Реальный путь — `POST /upload/schedule_item_files` (multipart, поле `files[]`,
  можно сразу несколько файлов), возвращает `[{"material_id"/"id", "uuid", ...}]`;
  чтобы реально привязать файл к мероприятию, этот material нужно ещё добавить в
  `attributes.files` элемента расписания через ПОЛНЫЙ PUT (см. update_event) —
  каждый элемент files там по факту `{"id": material_id, "uuid": ...,
  "can_download": true}`. attach_file() ниже делает оба шага. У привязанных файлов
  в ответе НЕТ индивидуального статуса синхронизации/привязки — только
  метаданные материала (имя/размер/url) плюс агрегированный files_sync_status
  выше.

Асинхронный джоб синхронизации может идти заметно дольше, чем казалось изначально:
живьём на одном и том же стенде наблюдались и ~1 минута, и ~6 минут до terminal-
статуса без видимой внешней причины — дефолтные таймауты ниже подняты
соответственно. Не дождались за отведённое время — не обязательно ошибка
интеграции, возможно просто не повезло с очередью.

Методы ниже этой части (настройки тенанта, запись вебинара, посещаемость,
журнал действий/аудит запросов) НЕ пересмотрены; индивидуальная траектория —
пересмотрена живьём 10.11.2026 (см. секцию в конце класса). Остальные НЕ пересмотрены в этом
заходе — живой разведкой 02.11.2026 не покрыты, остаются как были написаны до
появления ветки, с тем же предупреждением «контракт не подтверждён».
"""
import os
import time
from typing import Dict, List, Optional

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger

MTS_LINK_EVENT_TYPE = "mts_link"

# Ключи — то, что передают тесты (часть этого набора — исторические алиасы на тот же
# реальный field, см. _PART_FIELD). Значения множества ниже — то, что реально
# наблюдалось в attributes.mts_link живьём 02.11.2026.
INTEGRATION_PARTS = ("creation", "participants", "lecturers", "files", "stats")

# "webinar_data" — алиас на тот же webinar_status, что и "creation": в реальной форме
# редактирования только ОДИН блок «Синхронизация вебинара», не два отдельных (для
# создания и для последующих правок) — старое разделение на "creation"/"webinar_data"
# было домыслом до разведки.
_PART_FIELD = {
    "creation": "webinar_status",
    "webinar_data": "webinar_status",
    "participants": "participants_sync_status",
    "lecturers": "lecturers_sync_status",
    "files": "files_sync_status",
    "stats": "stats_sync_status",
}

# Терминальные значения по частям — у webinar_status подтверждённое успешное
# значение "synced" (НЕ "success", как у остальных *_sync_status полей); "finished" —
# после завершения мероприятия ведущим (живой эфир 03.11.2026), для ожидания создания
# тоже терминален. "error" по каждой части — предположение (см. докстринг модуля).
_TERMINAL_BY_PART = {
    "creation": {"synced", "finished", "error"},
    "webinar_data": {"synced", "finished", "error"},
    "participants": {"success", "error"},
    "lecturers": {"success", "error"},
    "files": {"success", "error"},
    "stats": {"success", "error"},
}

# Наблюдалась живьём синхронизация до ~6 минут на одном и том же стенде без видимой
# причины (см. докстринг модуля) — дефолт намеренно большой, старые 60-90 c были
# занижены.
DEFAULT_POLL_TIMEOUT = 300.0
DEFAULT_POLL_INTERVAL = 5.0

# Ограничения на файлы презентаций для вебинара — точные значения нигде не
# зафиксированы (МТС Линк API их не документирует в открытом доступе), используются
# как разумные дефолты для клиентской проверки перед отправкой, подлежат уточнению
# у разработки.
MAX_PRESENTATION_FILE_SIZE_MB = 100
ALLOWED_PRESENTATION_EXTENSIONS = (".pdf", ".ppt", ".pptx")


class MtsLinkEndpoint:
    """Методы для работы с интеграцией МТС Линк поверх обычных очных мероприятий
    (элементов расписания, см. api/endpoints/schedule_items.py)."""

    def __init__(self, client: ApiClient):
        self.client = client

    # ── настройки интеграции тенанта (НЕ пересмотрено 02.11.2026) ────────

    def get_tenant_settings(self, tenant_id: int) -> Dict:
        """Контракт не подтверждён (не пересматривалось в заходе 02.11.2026, см.
        докстринг модуля)."""
        resp = self.client.get(f"/admin/organizations/{tenant_id}/mts-link-settings")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    def save_tenant_settings(self, tenant_id: int, token: Optional[str] = None, **other_fields):
        """Контракт не подтверждён (не пересматривалось в заходе 02.11.2026, см.
        докстринг модуля)."""
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
        """Контракт не подтверждён (не пересматривалось в заходе 02.11.2026, см.
        докстринг модуля)."""
        data = self.get_tenant_settings(tenant_id)
        return bool(data.get("attributes", {}).get("integration_configured"))

    # ── создание мероприятия «МТС Линк» ───────────────────────────────────

    def build_event_payload(self, **overrides) -> dict:
        """Payload очного мероприятия типа «МТС Линк» — тот же контракт, что у
        обычного элемента расписания (generate_schedule_item_payload)."""
        from api.helpers.data_generator import generate_schedule_item_payload
        overrides.setdefault("item_type", MTS_LINK_EVENT_TYPE)
        overrides["url"] = ""
        return generate_schedule_item_payload(**overrides)

    # ── статус интеграции: поле attributes.mts_link, см. докстринг модуля ─

    def get_integration_status(self, item: Dict) -> Dict:
        """Статус интеграции мероприятия — поле attributes.mts_link на обычном GET
        элемента расписания (нет отдельного эндпоинта, см. докстринг модуля). `item`
        — объект, который возвращает фикстура created_schedule_item (нужны
        program_id/stream_id/module_id/id)."""
        resp = self.client.get(
            f"/programs/{item['program_id']}/streams/{item['stream_id']}"
            f"/modules/{item['module_id']}/schedule-items/{item['id']}"
        )
        expect_status(resp, 200)
        return resp.json()["data"]["attributes"].get("mts_link") or {}

    def get_part_status(self, item: Dict, part: str) -> Optional[str]:
        """Статус одной части синхронизации (см. INTEGRATION_PARTS/_PART_FIELD)."""
        field = _PART_FIELD[part]
        return self.get_integration_status(item).get(field)

    def get_summary_status(self, item: Dict) -> Optional[str]:
        """Сводный статус, ВЫЧИСЛЕННЫЙ из частей ниже — отдельного summary-поля в
        API нет (не подтверждено и само наличие «сводного статуса» как видимого
        пользователю понятия — см. докстринг модуля). "error", если хотя бы одна
        часть в ошибке; "success", когда части все терминальны и успешны; иначе
        None (ещё идёт)."""
        status = self.get_integration_status(item)
        parts = {"creation": status.get("webinar_status")}
        for part in ("participants", "lecturers", "files", "stats"):
            parts[part] = status.get(_PART_FIELD[part])
        values = list(parts.values())
        if "error" in values:
            return "error"
        success_values = {"synced", "finished", "success"}
        if all(v in success_values for v in values):
            return "success"
        return None

    def wait_for_part_status(
        self,
        item: Dict,
        part: str,
        timeout: float = DEFAULT_POLL_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> Optional[str]:
        """Поллинг статуса одной части синхронизации до терминального состояния (см.
        _TERMINAL_BY_PART)."""
        terminal = _TERMINAL_BY_PART[part]
        deadline = time.monotonic() + timeout
        last_status = None
        while time.monotonic() < deadline:
            last_status = self.get_part_status(item, part)
            logger.info(f"MTS Link item {item['id']}: part={part} status={last_status}")
            if last_status in terminal:
                return last_status
            time.sleep(poll_interval)
        return last_status

    def wait_for_summary_status(
        self, item: Dict, timeout: float = DEFAULT_POLL_TIMEOUT, poll_interval: float = DEFAULT_POLL_INTERVAL
    ) -> Optional[str]:
        """Поллинг вычисленного сводного статуса (см. get_summary_status) до
        "success"/"error"."""
        deadline = time.monotonic() + timeout
        last_status = None
        while time.monotonic() < deadline:
            last_status = self.get_summary_status(item)
            if last_status in ("success", "error"):
                return last_status
            time.sleep(poll_interval)
        return last_status

    # ── обновление мероприятия ─────────────────────────────────────────────

    def update_event(self, program_id: int, stream_id: int, module_id: int, item_id: int, attributes: dict):
        """Обновление полей мероприятия. Реальный контракт PUT требует ПОЛНЫЙ
        payload (см. докстринг модуля) — метод сам подтягивает текущие
        attributes и мёрджит переданные `attributes` поверх них, вызывающий код
        передаёт только то, что хочет изменить (как раньше)."""
        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/schedule-items/{item_id}"
        )
        expect_status(resp, 200)
        current = resp.json()["data"]["attributes"]
        merged = {
            "name": current["name"],
            "type": current["type"],
            "performance_direction_id": current["performance_direction_id"],
            "broad_topic_id": current["broad_topic_id"],
            "content_type": "offline",
            "location": current["location"],
            "url": current.get("url") or "",
            "teacher_ids": [t["id"] for t in current.get("teachers", [])],
            "listeners": current.get("listeners", []),
            "date_time_from": current["date_from"].replace(" ", "T")[:16],
            "date_time_to": current["date_to"].replace(" ", "T")[:16],
            "files": current.get("files", []),
            "region": current.get("region") or [],
            "show_activity_results": current.get("show_activity_results", True),
        }
        merged.update(attributes)
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/schedule-items/{item_id}",
            json={"data": {"attributes": merged}},
        )
        logger.info(f"Schedule item {item_id}: update -> {resp.status_code}")
        return resp

    # ── файлы презентаций ───────────────────────────────────────────────────

    def validate_file_before_upload(self, file_path: str) -> Optional[str]:
        """Проверка формата/размера файла презентации до отправки в МТС Линк —
        возвращает текст ошибки с указанием файла, либо None, если файл проходит.
        Пороги — MAX_PRESENTATION_FILE_SIZE_MB/ALLOWED_PRESENTATION_EXTENSIONS, оба
        предположительны (см. докстринг константы)."""
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
        """Прикрепить презентацию к мероприятию — два реальных шага (см. докстринг
        модуля): 1) POST /upload/schedule_item_files (multipart, поле files[]) —
        загружает файл как материал, возвращает material_id/uuid; 2) добавить этот
        материал в attributes.files элемента расписания через ПОЛНЫЙ PUT
        (update_event). Возвращает ответ второго шага (PUT) — как и раньше, у него
        есть .status_code."""
        with open(file_path, "rb") as fh:
            upload_resp = self.client.upload(
                "/upload/schedule_item_files",
                files={"files[]": fh},
            )
        expect_status(upload_resp, 200)
        material = upload_resp.json()["data"][0]

        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/schedule-items/{item_id}"
        )
        expect_status(resp, 200)
        current_files = resp.json()["data"]["attributes"].get("files", [])
        new_file_ref = {"id": material["material_id"], "uuid": material["uuid"], "can_download": True}

        put_resp = self.update_event(
            program_id, stream_id, module_id, item_id,
            attributes={"files": current_files + [new_file_ref]},
        )
        logger.info(f"Schedule item {item_id}: attach file {file_path} -> {put_resp.status_code}")
        return put_resp

    # ── запись вебинара (НЕ пересмотрено 02.11.2026) ──────────────────────

    def get_recording_info(self, schedule_item_id: int) -> Dict:
        """Контракт не подтверждён (не пересматривалось в заходе 02.11.2026, см.
        докстринг модуля)."""
        resp = self.client.get(f"/schedule-item/{schedule_item_id}/mts-link/recording")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    # ── посещаемость (НЕ пересмотрено 02.11.2026) ─────────────────────────

    def get_listener_attendance(self, schedule_item_id: int, user_id: int) -> Dict:
        """Контракт не подтверждён (не пересматривалось в заходе 02.11.2026, см.
        докстринг модуля)."""
        resp = self.client.get(f"/schedule-item/{schedule_item_id}/mts-link/attendance/{user_id}")
        expect_status(resp, 200)
        return resp.json().get("data", {})

    # ── логирование / аудит (НЕ пересмотрено 02.11.2026) ──────────────────
    # get_request_log_entries бьёт в /admin/mts-link/request-log-audit — этот путь
    # подтверждённо 404 (проверено 02.11.2026 вместе с остальными). Оставлен как
    # есть (не удалён), потому что используется за пределами сегодняшнего захода
    # (tests/api/mts_link/test_logging.py целиком об этом) — выводы и фикс того
    # файла в это изменение не входят.

    def get_action_log(self, entity_type: str, entity_id: int) -> List[Dict]:
        """Контракт не подтверждён (не пересматривалось в заходе 02.11.2026, см.
        докстринг модуля)."""
        resp = self.client.get(f"/admin/logs?entity_type={entity_type}&entity_id={entity_id}")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def get_request_log_entries(
        self,
        schedule_item_id: Optional[int] = None,
        operation: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Контракт не подтверждён; путь ниже подтверждённо 404 (проверено
        02.11.2026, см. докстринг модуля) — метод оставлен для test_logging.py, не
        пересматривался в этом заходе."""
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
        """SQL-фоллбэк к таблице request_log_audit — не настроен в проекте (см.
        исходный докстринг ниже), не пересматривалось в заходе 02.11.2026."""
        dsn = os.getenv("MTS_LINK_DB_DSN")
        if not dsn:
            raise NotImplementedError(
                "get_request_log_entries_via_sql: не задан MTS_LINK_DB_DSN (.env.example) — "
                "SQL-фоллбэк к request_log_audit ещё не настроен. Используйте "
                "get_request_log_entries (API), когда появится контракт."
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

    def get_deletion_audit(self, schedule_item_id: int) -> List[Dict]:
        """Контракт не подтверждён (не пересматривалось в заходе 02.11.2026, см.
        докстринг модуля)."""
        return self.get_request_log_entries(schedule_item_id=schedule_item_id, operation="delete")

    def wait_for_deletion(
        self, schedule_item_id: int, timeout: float = 60.0, poll_interval: float = 3.0
    ) -> List[Dict]:
        """Контракт не подтверждён (не пересматривалось в заходе 02.11.2026, см.
        докстринг модуля)."""
        deadline = time.monotonic() + timeout
        entries: List[Dict] = []
        while time.monotonic() < deadline:
            entries = self.get_deletion_audit(schedule_item_id)
            if any(e.get("success") for e in entries):
                return entries
            logger.info(f"Schedule item {schedule_item_id}: deletion not confirmed yet, retrying")
            time.sleep(poll_interval)
        return entries

    def retry_part(self, schedule_item_id: int, part: str) -> Dict:
        """Контракт не подтверждён; живой осмотр формы редактирования 02.11.2026
        показал ОДНУ общую кнопку «Повторить синхронизацию», не по кнопке на
        каждую часть, как предполагает сигнатура ниже — не пересматривалось
        подробнее в этом заходе, путь ниже не проверен."""
        resp = self.client.post(f"/schedule-item/{schedule_item_id}/mts-link/retry", json={"part": part})
        expect_status(resp, (200, 202))
        logger.info(f"MTS Link event {schedule_item_id}: retry part={part}")
        return resp.json()

    # ── индивидуальная траектория (часть 14) — контракт подтверждён живьём 10.11.2026 ──
    # Очное мероприятие в индивидуальной траектории — отдельная сущность «офлайн-контент
    # пользователя» (content_type "offline"), не schedule-item модуля:
    #   POST   /users/content/offline                      — создать (data.user_ids + attributes
    #                                                        с тем же payload, что у schedule-item)
    #   GET    /users/content/offline/user-content/{user}  — список по пользователю; у элемента
    #                                                        attributes.url и attributes.mts_link
    #                                                        в том же формате, что у schedule-item
    #   PUT|DELETE /users/content/offline/{content_id}     — правка / снятие назначения
    # В админке: карточка пользователя → «Назначения» → «Индивидуальная траектория обучения»
    # → вкладка «Очные» (недельный календарь). Старый путь
    # /individual-trajectory/assignments/{id}/mts-link не существует (404).

    IT_OFFLINE_PATH = "/users/content/offline"

    def create_it_event(self, user_id: int, **overrides) -> Dict:
        """Создать очное мероприятие «МТС Линк» в индивидуальной траектории одного
        слушателя. Payload — как у schedule-item (generate_schedule_item_payload) с
        безопасными для боевого аккаунта МТС Линк умолчаниями
        (mts_link_safe_schedule_item_kwargs: Вера-лектор, дата завтра, регион 1).
        Возвращает data созданного офлайн-контента (id, attributes)."""
        from api.helpers.data_generator import (
            generate_schedule_item_payload,
            mts_link_safe_schedule_item_kwargs,
        )
        kwargs = mts_link_safe_schedule_item_kwargs(**overrides)
        attributes = generate_schedule_item_payload(**kwargs)["data"]["attributes"]
        resp = self.client.post(self.IT_OFFLINE_PATH, json={"data": {"user_ids": [user_id], "attributes": attributes}})
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"MTS Link IT event created: content_id={data['id']} user_id={user_id}")
        return data

    def list_it_offline_contents(self, user_id: int) -> List[Dict]:
        """Все очные мероприятия индивидуальной траектории пользователя."""
        resp = self.client.get(f"{self.IT_OFFLINE_PATH}/user-content/{user_id}?page=1&per-page=9999")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def get_it_event(self, user_id: int, content_id: int) -> Optional[Dict]:
        """Элемент списка ИТ по id контента или None, если его там (уже) нет."""
        return next((c for c in self.list_it_offline_contents(user_id) if c.get("id") == content_id), None)

    def get_it_integration_status(self, user_id: int, content_id: int) -> Dict:
        """attributes.mts_link мероприятия ИТ — тот же формат, что у schedule-item."""
        event = self.get_it_event(user_id, content_id)
        return (event or {}).get("attributes", {}).get("mts_link") or {}

    def wait_for_it_part_status(
        self,
        user_id: int,
        content_id: int,
        part: str,
        timeout: float = DEFAULT_POLL_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> Optional[str]:
        """Поллинг части синхронизации мероприятия ИТ до терминального состояния
        (см. _TERMINAL_BY_PART) — аналог wait_for_part_status для schedule-item."""
        terminal = _TERMINAL_BY_PART[part]
        field = _PART_FIELD[part]
        deadline = time.monotonic() + timeout
        last_status = None
        while time.monotonic() < deadline:
            last_status = self.get_it_integration_status(user_id, content_id).get(field)
            logger.info(f"MTS Link IT content {content_id}: part={part} status={last_status}")
            if last_status in terminal:
                return last_status
            time.sleep(poll_interval)
        return last_status

    def delete_it_event(self, content_id: int) -> bool:
        """Снять мероприятие с индивидуальной траектории (DELETE). По ТЗ части 14 —
        вебинар в МТС Линк удаляется целиком, если ещё не прошёл."""
        resp = self.client.delete(f"{self.IT_OFFLINE_PATH}/{content_id}")
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"MTS Link IT event deleted: content_id={content_id}")
        else:
            logger.warning(f"MTS Link IT event delete failed: content_id={content_id}, status={resp.status_code}")
        return success

    def wait_for_it_event_removed(
        self, user_id: int, content_id: int, timeout: float = 60.0, poll_interval: float = 3.0
    ) -> bool:
        """True, когда мероприятие пропало из списка ИТ пользователя."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.get_it_event(user_id, content_id) is None:
                return True
            time.sleep(poll_interval)
        return self.get_it_event(user_id, content_id) is None
