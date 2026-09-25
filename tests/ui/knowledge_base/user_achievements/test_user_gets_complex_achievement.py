"""UI: слушатель получает составное достижение — два конкретных материала («аудио + книга»,
«файл + книга», «две книги»), 3 сценария.

Перенос test_07..09_user_gets_*_complex_achievement.py коллеги (репозиторий lms,
feature/dashboard-autotests) на нашу архитектуру: материалы и составное достижение
(два условия material_set) готовятся через API (material_for_type/achievement_for из
conftest.py), действия слушателя — через UserKnowledgeBasePage, удаление через API в
teardown фикстур даже при падении теста.

Завершение каждого материала подтверждается через API (pass_material_via_api) — при
переносе выяснилось, что UI-действие (скролл книги, скачивание файла) само по себе не
создаёт сетевой запрос о прогрессе на этой версии портала (см. conftest.py и
test_user_gets_achievement_by_material.py).
"""
import allure
import pytest

from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from ui.pages.user_knowledge_base_page import UserKnowledgeBasePage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

# Сценарий -> (типы двух материалов, русская подпись условий).
COMPLEX_SCENARIOS = {
    "audio_and_book": (("audio", "book"), "аудио и книга"),
    "file_and_book": (("file", "book"), "файл и книга"),
    "two_books": (("book", "book"), "две книги"),
}


def _complete_material(kb_page: UserKnowledgeBasePage, material_type: str, material_name: str) -> None:
    if material_type == "audio":
        kb_page.listen_audio_to_end(material_name)
    elif material_type == "book":
        kb_page.read_book_to_end(material_name)
    elif material_type == "file":
        kb_page.download_file(material_name, attached_file_name="certificat.pdf")
    else:
        raise ValueError(f"Неизвестный тип материала: {material_type!r}")


@allure.feature("База знаний UI")
@allure.story("Слушатель получает составное достижение")
class TestUserGetsComplexAchievement:

    @pytest.mark.parametrize("scenario", list(COMPLEX_SCENARIOS))
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_user_gets_complex_achievement(
        self, user_page, env, kb_endpoint, kb_test_user_full_name, user_api_client,
        material_for_type, achievement_for, scenario,
    ):
        (first_type, second_type), scenario_label = COMPLEX_SCENARIOS[scenario]
        allure.dynamic.title(f"UI: слушатель получает составное достижение «{scenario_label}»")

        UserSidebarPage(user_page).dismiss_popups()

        with allure.step("1. Подготовить два материала через API"):
            first_id, first_name = material_for_type(first_type)
            second_id, second_name = material_for_type(second_type)
            logger.info(f"Материалы созданы: {first_id} ({first_name}), {second_id} ({second_name})")

        with allure.step("2. Подготовить составное достижение через API"):
            achievement_description = f"Автотестовое составное достижение: {scenario_label}"
            achievement_id, achievement_name = achievement_for(
                material_ids=[first_id, second_id], description=achievement_description,
            )
            logger.info(f"Достижение создано: ID={achievement_id}, name={achievement_name}")

        kb_page = UserKnowledgeBasePage(user_page)
        user_kb_endpoint = KnowledgeBaseEndpoint(user_api_client)

        for step_number, (material_type, material_id, material_name) in enumerate(
            ((first_type, first_id, first_name), (second_type, second_id, second_name)), start=3
        ):
            with allure.step(f"{step_number}. Изучить материал «{material_name}» до конца"):
                kb_page.open_material_by_id(env.ui_base_url, material_id, material_name)
                _complete_material(kb_page, material_type, material_name)
                user_kb_endpoint.pass_material_via_api(material_id)

        with allure.step("5. Дождаться начисления достижения (история в админке)"):
            kb_endpoint.wait_user_achievement(kb_test_user_full_name, achievement_name)

        with allure.step("6. Проверить карточку полученного достижения на странице «Достижения»"):
            kb_page.open_achievements(env.ui_base_url)
            kb_page.assert_achievement_received(achievement_name, achievement_description)
