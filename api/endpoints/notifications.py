from typing import Dict, Optional
from urllib.parse import urlencode

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger


class NotificationsEndpoint:
    """Методы для работы с уведомлениями (/api/v1/notifications/*)."""

    def __init__(self, client: ApiClient):
        self.client = client

    # ── Уведомления ──────────────────────────────────────────────────────

    def list(self, per_page: int = 2000) -> list:
        """Список уведомлений. GET /notifications пагинирован (25 записей на страницу
        по умолчанию, ~660+ записей на develop) — без per-page=<большое число> список
        обрывается на первой странице и не находит свежесозданные уведомления
        (см. find_by_name и отчёт разведки)."""
        resp = self.client.get(f"/notifications?per-page={per_page}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def get(self, notification_id: int) -> Dict:
        """Уведомление по ID."""
        resp = self.client.get(f"/notifications/{notification_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def creators(self) -> list:
        """Справочник создателей уведомлений (для фильтра)."""
        resp = self.client.get("/notifications/creators")
        expect_status(resp, 200)
        return resp.json()["data"]

    def receivers(self) -> list:
        """Справочник получателей уведомлений (для выбора в форме создания)."""
        resp = self.client.get("/notifications/receivers")
        expect_status(resp, 200)
        return resp.json()["data"]

    def text_variables(self) -> Dict:
        """Справочник переменных подстановки текста ({userFullName} и т.п.)."""
        resp = self.client.get("/notifications/text-variables")
        expect_status(resp, 200)
        return resp.json()["data"]

    def create(self, payload: dict) -> Dict:
        """Создание и отправка уведомления."""
        resp = self.client.post("/notifications/create", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Notification created: ID={data.get('id')}, name={data.get('name')}")
        return data

    def find_by_name(self, name: str) -> Optional[Dict]:
        """POST /notifications/create отдаёт users=[] в ответе на создание —
        для проверки фактических получателей уведомление находят по имени в списке."""
        for notification in self.list():
            if notification.get("name") == name:
                return notification
        return None

    def resend(self, notification_id: int) -> Dict:
        """Повторная отправка уведомления."""
        resp = self.client.post(f"/notifications/resend/{notification_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def delete(self, notification_ids: list) -> bool:
        """Удаление уведомлений по списку ID.

        Контракт: `POST /notifications/delete?notification_ids[0]=<id>&…` — id в query
        (проверено на develop 11.11.2026: GET /notifications/{id} → 404 через 3 с). До этого
        клиент слал JSON {"ids": [...]}: сервер отвечал 200 и ничего не удалял — отсюда
        «отложенное, непредсказуемо долгое удаление» в отчёте разведки и 1300+
        накопившихся Автотест_* уведомлений в админке. Тот же приём, что у delete_templates."""
        query = urlencode({f"notification_ids[{i}]": nid for i, nid in enumerate(notification_ids)})
        resp = self.client.post(f"/notifications/delete?{query}")
        success = resp.status_code in (200, 202, 204)
        if success:
            logger.info(f"Notifications delete requested: {notification_ids}")
        else:
            logger.warning(f"Delete notifications failed: {resp.status_code} {resp.text[:200]}")
        return success

    # ── Шаблоны уведомлений ─────────────────────────────────────────────

    def list_templates(self, per_page: int = 2000) -> list:
        """Список шаблонов уведомлений. Пагинирован так же, как GET /notifications
        (25 на страницу, по возрастанию id): на develop к 11.11.2026 шаблонов стало
        больше 25, и свежесозданный уходил на вторую страницу — без per-page тест «список
        содержит созданный» падал, а «шаблон не пропадает после удаления» ловил не лаг
        удаления, а ту же пагинацию."""
        resp = self.client.get(f"/notifications/templates?per-page={per_page}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def create_template(self, payload: dict) -> Dict:
        """Создание шаблона уведомления."""
        resp = self.client.post("/notifications/templates", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Notification template created: ID={data['id']}, name={data.get('name')}")
        return data

    def get_template(self, template_id: int) -> Dict:
        """Шаблон уведомления по ID."""
        resp = self.client.get(f"/notifications/templates/{template_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def update_template(self, template_id: int, payload: dict) -> Dict:
        """Обновление шаблона уведомления."""
        resp = self.client.put(f"/notifications/templates/{template_id}", json=payload)
        expect_status(resp, 200)
        return resp.json()["data"]

    def delete_templates(self, template_ids: list) -> bool:
        """Удаление шаблонов уведомлений по списку ID.

        Контракт подсмотрен перехватом запроса админки (вкладка «Шаблоны», 11.11.2026):
        `POST /notifications/templates/delete?template_ids[0]=<id>&template_ids[1]=…` — id в
        query-параметрах, тело пустое. До этого клиент слал JSON {"ids": [...]}: сервер
        отвечал 200 {"status":"success"}, но ничего не удалял — отсюда ложный «кандидат
        в дефект: шаблон не пропадает из списка» и 40+ накопившихся Автотест_* шаблонов."""
        query = urlencode({f"template_ids[{i}]": template_id for i, template_id in enumerate(template_ids)})
        resp = self.client.post(f"/notifications/templates/delete?{query}")
        success = resp.status_code in (200, 202, 204)
        if success:
            logger.info(f"Notification templates deleted: {template_ids}")
        else:
            logger.warning(f"Delete templates failed: {resp.status_code} {resp.text[:200]}")
        return success

    # ── Шаблоны писем при саморегистрации ───────────────────────────────

    def list_register_templates(self) -> list:
        """Список шаблонов уведомлений о саморегистрации (register_application,
        user_verified_email, application_accepted, application_rejected)."""
        resp = self.client.get("/notifications/register-templates")
        expect_status(resp, 200)
        return resp.json()["data"]

    def get_register_template(self, template_type: str) -> Dict:
        """Шаблон саморегистрации по типу. Для неизвестного type API отвечает 200
        с {"type": null, "title": null, "body": null} вместо 404 — см. отчёт разведки."""
        resp = self.client.get(f"/notifications/register-templates/{template_type}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def update_register_template(self, template_type: str, title: str, body: str) -> Dict:
        """Обновление шаблона саморегистрации. Формат тела — единственный рабочий,
        подтверждённый разведкой (обычный плоский {"title", "body"} даёт 422)."""
        payload = {"data": {"attributes": {"type": template_type, "title": title, "body": body}}}
        resp = self.client.post(f"/notifications/register-templates/{template_type}", json=payload)
        expect_status(resp, 200)
        return resp.json()["data"]

    # ── Шаблоны формы оценки/комментирования (review) ───────────────────

    def list_review_templates(self) -> list:
        """Список шаблонов уведомлений формы оценки и комментирования."""
        resp = self.client.get("/notifications/review-templates")
        expect_status(resp, 200)
        return resp.json()["data"]

    def get_review_template(self, template_id: int) -> Dict:
        """Шаблон формы оценки/комментирования по ID."""
        resp = self.client.get(f"/notifications/review-templates/{template_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def update_review_template(self, template_id: int, payload: dict) -> Dict:
        """Обновление шаблона формы оценки/комментирования."""
        resp = self.client.put(f"/notifications/review-templates/{template_id}", json=payload)
        expect_status(resp, 200)
        return resp.json()["data"]
