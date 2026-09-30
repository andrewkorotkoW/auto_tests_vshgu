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
        """Включить/выключить взаимопроверку в карточке ПЗ.

        Контракт не подтверждён, раздел 4. Предполагается payload по аналогии с
        homework_pass_fail.py/homework_ten_point.py (доп. атрибут в payload создания
        активности), здесь — отдельный PATCH по аналогии с examine()/change_state()
        (точечное изменение уже созданного ПЗ).
        """
        resp = self.client.patch(f"/content/{content_id}/peer-review", json={
            "data": {"attributes": {"enabled": enabled}}
        })
        expect_status(resp, (200, 201))
        logger.info(f"Homework {content_id}: peer-review enabled={enabled}")
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

    def get_criteria(self, content_id: int) -> List[Dict]:
        """Форма критериев p2p-ПЗ (03 §7, 04 §5). Этап 1 не планирует автотест на сам
        конструктор (тип: manual), метод нужен как подготовка данных для peer-проверки.

        Контракт не подтверждён, раздел 5.
        """
        resp = self.client.get(f"/content/{content_id}/peer-review/criteria")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def set_criteria(self, content_id: int, criteria: List[Dict]) -> Dict:
        """Сохранить форму критериев. После первой полученной peer-проверки добавление/
        удаление критериев запрещено (04 §5.2) — это ограничение сервера, не клиента.

        Контракт не подтверждён, раздел 5.
        """
        resp = self.client.post(f"/content/{content_id}/peer-review/criteria", json={
            "data": {"attributes": {"criteria": criteria}}
        })
        expect_status(resp, (200, 201))
        logger.info(f"Homework {content_id}: criteria saved ({len(criteria)} items)")
        return resp.json()

    # ── §2/§6: настройки p2p-ПЗ в потоке (участники, режим, лимиты) ─────────

    def set_stream_participants(self, program_id: int, stream_id: int, content_id: int, user_ids: List[int]) -> Dict:
        """Список участников взаимопроверки в потоке — только слушатели этого потока
        (04 §2, 03 §5.1).

        Контракт не подтверждён, раздел 2.
        """
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/content/{content_id}/peer-review/participants",
            json={"data": {"attributes": {"user_ids": user_ids}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Stream {stream_id}, content {content_id}: p2p participants set {user_ids}")
        return resp.json()

    def set_distribution_mode(self, program_id: int, stream_id: int, content_id: int, mode: str) -> Dict:
        """Режим распределения работ в потоке: "manual" или "auto" (04 §6.1—6.2).

        Контракт не подтверждён, раздел 6.
        """
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/content/{content_id}/peer-review/settings",
            json={"data": {"attributes": {"distribution_mode": mode}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Stream {stream_id}, content {content_id}: distribution_mode={mode}")
        return resp.json()

    def set_works_per_listener(self, program_id: int, stream_id: int, content_id: int, count: int) -> Dict:
        """«Количество работ для проверки одним слушателем» в автоматическом режиме
        (04 §6.2).

        Контракт не подтверждён, раздел 6.
        """
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/content/{content_id}/peer-review/settings",
            json={"data": {"attributes": {"works_per_listener": count}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Stream {stream_id}, content {content_id}: works_per_listener={count}")
        return resp.json()

    def set_minimum_reviews_per_work(self, program_id: int, stream_id: int, content_id: int, count: int) -> Dict:
        """Минимальное количество peer-проверок на одну работу — применяется независимо
        от режима распределения (04 §6.2, §10.1).

        Контракт не подтверждён, раздел 6.
        """
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/content/{content_id}/peer-review/settings",
            json={"data": {"attributes": {"minimum_reviews_per_work": count}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Stream {stream_id}, content {content_id}: minimum_reviews_per_work={count}")
        return resp.json()

    # ── §6: распределение работ ──────────────────────────────────────────────

    def assign_work_manually(self, program_id: int, stream_id: int, content_id: int, work_id: int, reviewer_user_id: int) -> Dict:
        """Ручное назначение конкретной чужой работы конкретному слушателю-проверяющему
        (04 §6.1). Сервер должен отклонять назначение собственной работы автору.

        Контракт не подтверждён, раздел 6.
        """
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/content/{content_id}/peer-review/assignments",
            json={"data": {"attributes": {"work_id": work_id, "reviewer_user_id": reviewer_user_id}}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Work {work_id} assigned to reviewer {reviewer_user_id} (manual)")
        return resp.json()

    def run_automatic_distribution(self, program_id: int, stream_id: int, content_id: int) -> Dict:
        """Запуск автоматического распределения по потоку с учётом works_per_listener
        и исключением собственных работ (04 §6.2).

        Контракт не подтверждён, раздел 6.
        """
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/content/{content_id}/peer-review/distribute",
            json={},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Stream {stream_id}, content {content_id}: automatic distribution started")
        return resp.json()

    def list_assignments(self, program_id: int, stream_id: int, content_id: int, reviewer_user_id: Optional[int] = None) -> List[Dict]:
        """Назначенные peer-проверки по ПЗ в потоке — для слушателя-проверяющего
        (список «чужих» работ, 04 §3.1/§6.1) или все, если reviewer_user_id не задан.

        Контракт не подтверждён, раздел 6.
        """
        endpoint = f"/programs/{program_id}/streams/{stream_id}/content/{content_id}/peer-review/assignments"
        if reviewer_user_id is not None:
            endpoint += f"?filters[reviewer_user_id]={reviewer_user_id}"
        resp = self.client.get(endpoint)
        expect_status(resp, 200)
        return resp.json().get("data", [])

    # ── §3/§8: peer-проверка слушателем-проверяющим ─────────────────────────

    def submit_peer_review(self, work_id: int, reviewer_user_id: int, criteria_values: Dict, final_confirm: bool = False) -> Dict:
        """Сохранить/обновить peer-проверку. До финального подтверждения значения можно
        менять (04 §8.1); final_confirm=True фиксирует проверку — дальше редактирование
        должно быть заблокировано.

        Контракт не подтверждён, раздел 8.
        """
        resp = self.client.post(
            f"/homework/{work_id}/peer-reviews",
            json={"data": {"attributes": {
                "reviewer_user_id": reviewer_user_id,
                "criteria_values": criteria_values,
                "final_confirm": final_confirm,
            }}},
        )
        expect_status(resp, (200, 201))
        logger.info(f"Work {work_id}: peer review by {reviewer_user_id} saved (final_confirm={final_confirm})")
        return resp.json()

    def get_peer_review(self, work_id: int, review_id: int) -> Dict:
        """Прочитать сохранённую peer-проверку — например, чтобы убедиться, что
        значения не меняются после финального подтверждения (04 §8.1).

        Контракт не подтверждён, раздел 8.
        """
        resp = self.client.get(f"/homework/{work_id}/peer-reviews/{review_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

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
