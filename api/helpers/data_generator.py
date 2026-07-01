import os
import random
import string
import time
from typing import Tuple
from .constants import (
    MALE_NAMES, FEMALE_NAMES,
    MALE_SURNAMES, FEMALE_SURNAMES,
    MALE_PATRONYMICS, FEMALE_PATRONYMICS
)

def random_email(domain: str = "gmail.com") -> str:
    """Генерация уникального email с меткой времени."""
    timestamp = int(time.time() * 1000)
    return f"auto_test_{timestamp}@{domain}"

def random_user_data() -> Tuple[str, str, str]:
    """Генерация случайных ФИО (мужчина или женщина)."""
    if random.choice([True, False]):
        name = random.choice(MALE_NAMES)
        surname = random.choice(MALE_SURNAMES)
        patronymic = random.choice(MALE_PATRONYMICS)
    else:
        name = random.choice(FEMALE_NAMES)
        surname = random.choice(FEMALE_SURNAMES)
        patronymic = random.choice(FEMALE_PATRONYMICS)
    return name, surname, patronymic


def random_phone() -> str:
    """Генерация случайного телефона."""
    return f"9{random.randint(100000000, 999999999)}"


def generate_user_payload(
    email: str = None,
    name: str = None,
    surname: str = None,
    patronymic: str = None,
    password: str = "SecurePass123",
    date_of_birth: str = "1990-10-10",
    region_id: int = 1,
    municipality_id: int = 158
) -> dict:
    """Генерация полного payload для создания пользователя."""
    if not email:
        email = random_email()
    if not name or not surname or not patronymic:
        name, surname, patronymic = random_user_data()

    return {
        "data": {
            "attributes": {
                "fields": {
                    "personal_phone_number": 0,
                    "phone_number": 0,
                    "email": 0,
                    "position": 0,
                    "position_level": 0,
                    "organisation": 0,
                    "car_brand": 0,
                    "car_number": 0
                },
                "roles": None,
                "tags": [],
                "email": email,
                "surname": surname,
                "name": name,
                "login": email,
                "patronymic": patronymic,
                "system_password": password,
                "password": password,
                "date_of_birth": date_of_birth,
                "region_id": region_id,
                "municipality_id": municipality_id
            }
        }
    }

def generate_program_payload(
    name: str = None,
    description: str = None,
    is_active: bool = True,
    color: str = "45ace1",
    completed_color: str = "e3f3fb",
    completed_text_color: str = "00385d",
    tenant_organization_id: str = ""
) -> dict:
    """Генерация payload для создания программы."""
    if not name:
        timestamp = int(time.time() * 1000)
        name = f"API-test_{timestamp}"
    if not description:
        description = f"<p>{name}</p>"

    return {
        "data": {
            "attributes": {
                "name": name,
                "tenant_organization_id": tenant_organization_id,
                "description": description,
                "is_active": is_active,
                "color": color,
                "completed_color": completed_color,
                "completed_text_color": completed_text_color,
            }
        }
    }

def generate_stream_payload(
        name: str = None,
        location: str = "Москва",
        date_from: str = None,
        date_to: str = None,
        is_active: bool = True,
        duration: str = "123",
        passed_percent: int = 100,
        project: int = 1,
        program_level: int = 4,
        program_department: int = 7,
        program_type: int = 10,
        learning_format: int = 13,
        academic_directors: list = None,
        experts_entity_name: str = "13"
) -> dict:
    """Генерация payload для создания потока."""
    from datetime import datetime, timedelta

    if not name:
        timestamp = int(time.time() * 1000)
        name = f"API_stream_{timestamp}"
    if academic_directors is None:
        academic_directors = [1]

    # Даты: сегодня + 30 дней
    today = datetime.now()
    if not date_from:
        date_from = today.strftime("%Y-%m-%d")
    if not date_to:
        date_to = (today + timedelta(days=30)).strftime("%Y-%m-%d")

    return {
        "data": {
            "attributes": {
                "name": name,
                "location": location,
                "date_from": date_from,
                "date_to": date_to,
                "is_active": is_active,
                "chats": [],
                "commentable": True,
                "duration": duration,
                "passed_percent": passed_percent,
                "project": project,
                "is_registration_by_link_enabled": False,
                "is_disciplines_required": False,
                "managers_ids": [],
                "external_managers": [],
                "program_level": program_level,
                "program_department": program_department,
                "program_type": program_type,
                "learning_format": learning_format,
                "academic_directors": academic_directors,
                "experts_entity_name": experts_entity_name
            }
        }
    }

def generate_module_payload(
        name: str = None,
        location: str = "Москва",
        date_from: str = None,
        date_to: str = None
) -> dict:
    """Генерация payload для создания модуля."""
    from datetime import datetime, timedelta

    if not name:
        timestamp = int(time.time() * 1000)
        name = f"API_module_{timestamp}"

    today = datetime.now()
    if not date_from:
        date_from = today.strftime("%Y-%m-%d")
    if not date_to:
        date_to = (today + timedelta(days=30)).strftime("%Y-%m-%d")

    return {
        "data": {
            "attributes": {
                "name": name,
                "location": location,
                "date_from": date_from,
                "date_to": date_to
            }
        }
    }

def generate_module_update_payload(
        name: str = None,
        location: str = "Москва",
        date_from: str = None,
        date_to: str = None,
        must_use_module_region: bool = True,
        region_id: int = 33,
        region_name: str = "Москва"
) -> dict:
    """Генерация payload для обновления модуля."""
    from datetime import datetime, timedelta

    if not name:
        name = f"Updated_module_{int(time.time() * 1000)}"

    today = datetime.now()
    if not date_from:
        date_from = today.strftime("%Y-%m-%d")
    if not date_to:
        date_to = (today + timedelta(days=30)).strftime("%Y-%m-%d")

    return {
        "data": {
            "attributes": {
                "name": name,
                "location": location,
                "date_from": date_from,
                "date_to": date_to,
                "must_use_module_region": must_use_module_region,
                "region": {
                    "region_id": region_id,
                    "region_name": region_name
                }
            }
        }
    }

def generate_schedule_item_payload(
        name: str = None,
        item_type: str = "webinar",
        performance_direction_id: int = 1,
        broad_topic_id: int = 2,
        content_type: str = "offline",
        location: str = "Москва",
        url: str = "",
        teacher_ids: list = None,
        date_time_from: str = None,
        date_time_to: str = None,
        region_id: int = 33,
        region_name: str = "Москва"
) -> dict:
    """Генерация payload для элемента расписания."""
    from datetime import datetime, timedelta

    if not name:
        timestamp = int(time.time() * 1000)
        name = f"Автотест_{timestamp}"
    if teacher_ids is None:
        teacher_ids = [4]

    today = datetime.now()
    if not date_time_from:
        date_time_from = today.strftime("%Y-%m-%dT10:05")
    if not date_time_to:
        date_time_to = (today + timedelta(hours=1)).strftime("%Y-%m-%dT11:05")

    return {
        "data": {
            "attributes": {
                "name": name,
                "type": item_type,
                "performance_direction_id": performance_direction_id,
                "broad_topic_id": broad_topic_id,
                "content_type": content_type,
                "location": location,
                "url": url,
                "teacher_ids": teacher_ids,
                "listeners": [],
                "date_time_from": date_time_from,
                "date_time_to": date_time_to,
                "files": [],
                "region": {
                    "region_id": region_id,
                    "region_name": region_name
                }
            }
        }
    }
def generate_aos_payload(
    name: str = None,
    name_client: str = None,
    test_type: str = "feedback",
    description: str = None,
    schedule_item_ids: list = None,
    is_last_day: bool = False,
    tenant_organization_id: int = 2,
    completion_percent: int = 60
) -> dict:
    """Генерация payload для создания АОС."""
    if not name:
        timestamp = int(time.time() * 1000)
        name = f"автотест_api_{timestamp}"
    if not name_client:
        name_client = name
    if not description:
        description = f"<p>{name}</p>"
    if schedule_item_ids is None:
        schedule_item_ids = []

    return {
        "type": test_type,
        "name": name,
        "name_client": name_client,
        "topic": "",
        "cover_uuid": "",
        "description": description,
        "screens": {
            "intro": {
                "title": "Вступительный слайд",
                "button_text": "Начать",
                "is_active": True
            },
            "onSuccess": {
                "title": "Успешное прохождение",
                "description": "Поздравляем, вы успешно завершили тестирование!"
            },
            "onFail": {
                "title": "Неправильное прохождение",
                "description": "К сожалению, вы не прошли тестирование."
            },
            "default": {
                "title": "",
                "description": ""
            }
        },
        "settings": {
            "completion_condition": {
                "condition_type": "percentage",
                "percentage": {"percent": completion_percent, "questions": 0},
                "score": {"count": 0}
            },
            "passage_time": {"count": 0, "is_active": False},
            "tries": {"count": 3, "is_active": False},
            "shuffle_questions_qty": {"is_active": False, "count": 0},
            "shuffle_questions": {"is_active": True},
            "shuffle_answers": {"is_active": True},
            "is_allow_question_move": {"is_active": True},
            "feedback": {
                "is_active": False,
                "onSuccess": {"text": "Верно!"},
                "onFail": {"text": "Неверно!"},
                "default": {"text": ""}
            }
        },
        "additional_params": {
            "schedule_items": {
                "ids": schedule_item_ids,
                "is_last_day": is_last_day
            },
            "tenant_organization_id": tenant_organization_id
        }
    }

def generate_lpd_payload(
    lpd_id: str = None,
    name: str = None,
    name_client: str = None,
    description: str = None,
    duration: str = "12",
    activity_category_id: int = 1
) -> dict:
    """Генерация payload для создания LPD."""
    if not lpd_id:
        lpd_id = get_next_lpd_id()
    if not name:
        name = f"Автотест_ЛПД_{lpd_id}"
    if not name_client:
        name_client = f"Автотест_ЛПД_{lpd_id}_внешка"
    if not description:
        description = f"<p>Автотест_ЛПД_{lpd_id}</p>"

    return {
        "data": {
            "attributes": {
                "inspectors": [],
                "teachers": [],
                "duration": duration,
                "teacher_ids": [],
                "content_type": "lpd",
                "lpd_id": lpd_id,
                "name": name,
                "name_client": name_client,
                "activity_category_id": activity_category_id,
                "description": description,
                "cover_uuid": "",
                "sub_files_uuids": ""
            },
            "includes": {
                "archive": [],
                "image": [],
                "spreadsheet": [],
                "video": [],
                "pdf": [],
                "document": [],
                "offline": [],
                "webinar": [],
                "cover": [],
                "sub_files": []
            }
        }
    }

_lpd_counter = 1234576

def get_next_lpd_id() -> str:
    global _lpd_counter
    _lpd_counter += 1
    return str(_lpd_counter)

def generate_tincan_payload(
    name: str = None,
    name_client: str = None,
    description: str = None,
    duration: str = "12",
    activity_category_id: int = 7,
    archive_uuid: str = "",
    cover_uuid: str = "",
    sub_files_uuids: list = None
) -> dict:
    if sub_files_uuids is None:
        sub_files_uuids = []
    if not name:
        name = f"Автотест_Tincan_{int(time.time())}"
    if not name_client:
        name_client = f"{name}_внешка"
    if not description:
        description = f"<p>{name}</p>"

    return {
        "data": {
            "attributes": {
                "inspectors": [],
                "teachers": [],
                "duration": duration,
                "teacher_ids": [],
                "content_type": "course-tincan",
                "name": name,
                "name_client": name_client,
                "activity_category_id": activity_category_id,
                "description": description,
                "allow_load_sub_files_from_program": True,
                "archive_uuid": archive_uuid,
                "cover_uuid": cover_uuid,
                "sub_files_uuids": sub_files_uuids
            },
            "includes": {
                "archive": [],
                "image": [],
                "spreadsheet": [],
                "video": [],
                "pdf": [],
                "document": [],
                "offline": [],
                "webinar": [],
                "cover": [],
                "sub_files": []
            }
        }
    }


def generate_cas_payload(
        cas_location_uuid: str = None,
        cas_organization_uuid: str = None,
        tenant_organization_id: int = 2
) -> dict:
    import random
    from .constants import CAS_LOCATIONS, CAS_ORGANIZATIONS

    if not cas_location_uuid:
        cas_location_uuid, _ = random.choice(CAS_LOCATIONS)
    if not cas_organization_uuid:
        cas_organization_uuid, _ = random.choice(CAS_ORGANIZATIONS)

    return {
        "cas_location_uuid": cas_location_uuid,
        "cas_organization_uuid": cas_organization_uuid,
        "tenant_organization_id": tenant_organization_id
    }

def generate_external_cas_program_payload(
    name: str = None,
    description: str = None,
    organization_uuid: str = None,
    location_uuid: str = None
) -> dict:
    if not name:
        name = f"Автотест_программа_КАС_{int(time.time())}"
    if not description:
        description = f"Описание {name}"
    return {
        "name": name,
        "description": description,
        "organization_uuid": organization_uuid,
        "location_uuid": location_uuid
    }

def generate_external_cas_stream_payload(
        date_from: str = None,
        date_to: str = None,
        managers_email: list = None
) -> dict:
    from datetime import datetime, timedelta

    today = datetime.now()
    if not date_from:
        date_from = today.strftime("%Y-%m-%d")
    if not date_to:
        date_to = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    if managers_email is None:
        managers_email = ["admin1@org2.ru", "admin2@org2.ru", "admin3@org2.ru", "admin4@org2.ru"]
    return {
        "date_from": date_from,
        "date_to": date_to,
        "managers_email": managers_email
    }


def generate_external_cas_user_payload(
        name: str = None,
        surname: str = None,
        patronymic: str = None,
        email: str = None,
        date_of_birth: str = None,
        personal_phone_number: str = None,
        organisation: str = "Devspark",
        position: str = "AQA",
        region: str = "Москва",
        cas_uuid: str = None,
        gender: int = 1,
        organization_uuid: str = None,
        location_uuid: str = None
) -> dict:
    import random, time

    if not name:
        name = random.choice(["Иван", "Пётр", "Сергей", "Алексей", "Дмитрий"])
    if not surname:
        surname = random.choice(["Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов"])
    if not patronymic:
        patronymic = random.choice(["Иванович", "Петрович", "Сергеевич", "Алексеевич", "Дмитриевич"])
    if not email:
        timestamp = int(time.time() * 1000)
        email = f"cas_user_{timestamp}@mail.com"
    if not date_of_birth:
        year = random.randint(1970, 1990)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        date_of_birth = f"{year}-{month:02d}-{day:02d}"
    if not personal_phone_number:
        phone = f"+7 {random.randint(900, 999)} {random.randint(100, 999)} {random.randint(10, 99)}-{random.randint(10, 99)}"
        personal_phone_number = phone
    if not cas_uuid:
        cas_uuid = f"cas-{int(time.time())}-{random.randint(1000, 9999)}"

    return {
        "name": name,
        "patronymic": patronymic,
        "surname": surname,
        "date_of_birth": date_of_birth,
        "personal_phone_number": personal_phone_number,
        "organisation": organisation,
        "position": position,
        "region": region,
        "cas_uuid": cas_uuid,
        "email": email,
        "gender": gender,
        "organization_uuid": organization_uuid,
        "location_uuid": location_uuid
    }

def generate_cas_sync_payload(
        name: str = None,
        surname: str = None,
        patronymic: str = None,
        date_of_birth: str = None,
        personal_phone_number: str = None,
        organisation: str = "Имэдж Спарк",
        position: str = "AQA",
        region: str = "Москва",
        cas_uuid: str = None
) -> dict:
    import random, time

    if not name:
        name = random.choice(["Иван", "Пётр", "Сергей"])
    if not surname:
        surname = random.choice(["Иванов", "Петров", "Сидоров"])
    if not patronymic:
        patronymic = random.choice(["Иванович", "Петрович", "Сергеевич"])
    if not date_of_birth:
        year = random.randint(1979, 2000)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        date_of_birth = f"{year}-{month:02d}-{day:02d}"
    if not personal_phone_number:
        phone = f"+7 {random.randint(900, 999)} {random.randint(100, 999)} {random.randint(10, 99)}-{random.randint(10, 99)}"
        personal_phone_number = phone
    if not cas_uuid:
        cas_uuid = get_next_cas_uuid()

    return {
        "sync_status": "synced",
        "name": name,
        "patronymic": patronymic,
        "surname": surname,
        "date_of_birth": date_of_birth,
        "personal_phone_number": personal_phone_number,
        "organisation": organisation,
        "position": position,
        "region": region,
        "cas_uuid": cas_uuid
    }

def get_next_cas_uuid() -> str:
    """Возвращает cas_uuid_N, увеличивая счётчик из файла."""
    counter_file = os.path.join(os.path.dirname(__file__), '../../test_data/cas_uuid_counter.txt')
    try:
        with open(counter_file, 'r') as f:
            counter = int(f.read().strip())
    except:
        counter = 37
    with open(counter_file, 'w') as f:
        f.write(str(counter + 1))
    return f"cas_uuid_{counter}"


def generate_external_content_payload(
        name: str = None,
        description: str = None,
        content_type: str = "external_content",
        external_type: str = "simulator",
        cover_uuid: str = "44389e67-3424-4b77-9197-ed8980380851",
        duration: str = ""
) -> dict:
    if not name:
        name = f"Автотест_внешний_контент_{int(time.time())}"
    if not description:
        description = f"<p>{name}</p>"

    return {
        "data": {
            "attributes": {
                "duration": duration,
                "content_type": content_type,
                "name": name,
                "description": description,
                "external_type": external_type,
                "cover_uuid": cover_uuid,
                "sub_files_uuids": ""
            },
            "includes": {
                "archive": [], "image": [], "spreadsheet": [], "video": [],
                "pdf": [], "document": [], "offline": [], "webinar": [],
                "cover": [{
                    "uuid": cover_uuid,
                    "attributes": {
                        "name": "cover.png",
                        "type": "image/png",
                        "size": 1174809,
                        "url": f"https://portal-develop.d2.devspark.ru/static/covers/{cover_uuid}/cover.png",
                        "created_at": "2026-05-26 16:58:41",
                        "update_at": "2026-05-26 16:58:41"
                    }
                }],
                "sub_files": []
            },
            "permissions": []
        }
    }

def generate_test_payload(
    name: str = None,
    name_client: str = None,
    topic: str = "Автотест",
    description: str = None,
    cover_uuid: str = "c0bd6d02-d9d4-4cd8-a064-a3dbe7b4aa99",
    completion_percent: int = 60,
    tries_count: int = 3,
    tries_active: bool = False,
    passage_time_count: int = 0,
    passage_time_active: bool = False,
    shuffle_questions: bool = True,
    shuffle_answers: bool = True,
    is_allow_question_move: bool = True,
    shuffle_questions_qty_active: bool = False,
    shuffle_questions_qty_count: int = 0,
    feedback_active: bool = False,
    tenant_organization_id: int = 2
) -> dict:
    """Генерация payload для создания теста (type=test)."""
    if not name:
        timestamp = int(time.time() * 1000)
        name = f"Автотест_тест_админка_{timestamp}"
    if not name_client:
        name_client = f"{name}_внешка"
    if not description:
        description = f"<p>Описание - автотест</p>"

    return {
        "type": "test",
        "name": name,
        "name_client": name_client,
        "topic": topic,
        "cover_uuid": cover_uuid,
        "description": description,
        "screens": {
            "intro": {
                "title": "Вступительный слайд",
                "button_text": "Начать",
                "is_active": True
            },
            "onSuccess": {
                "title": "Успешное прохождение",
                "description": "Поздравляем, вы успешно завершили тестирование!"
            },
            "onFail": {
                "title": "Неправильное прохождение",
                "description": "К сожалению, вы не прошли тестирование."
            },
            "default": {
                "title": "",
                "description": ""
            }
        },
        "settings": {
            "completion_condition": {
                "condition_type": "percentage",
                "percentage": {"percent": completion_percent, "questions": 0},
                "score": {"count": 0}
            },
            "passage_time": {"count": passage_time_count, "is_active": passage_time_active},
            "tries": {"count": tries_count, "is_active": tries_active},
            "shuffle_questions_qty": {"is_active": shuffle_questions_qty_active, "count": shuffle_questions_qty_count},
            "shuffle_questions": {"is_active": shuffle_questions},
            "shuffle_answers": {"is_active": shuffle_answers},
            "is_allow_question_move": {"is_active": is_allow_question_move},
            "feedback": {
                "is_active": feedback_active,
                "onSuccess": {"text": "Верно!"},
                "onFail": {"text": "Неверно!"},
                "default": {"text": ""}
            }
        },
        "additional_params": {"tenant_organization_id": tenant_organization_id}
    }

def generate_test_update_payload(
    content_id: int,
    name: str = None,
    name_client: str = None,
    topic: str = None,
    description: str = None,
    cover_uuid: str = "",
    completion_percent: int = 0,
    tries_count: int = 3,
    tries_active: bool = True,
    passage_time_count: int = 0,
    passage_time_active: bool = False,
    shuffle_questions_active: bool = False,
    shuffle_answers_active: bool = False,
    is_allow_question_move_active: bool = False,
    feedback_active: bool = False
) -> dict:
    """Генерация payload для обновления теста (PUT)."""
    if name is None:
        name = f"Обновлённый_тест_{int(time.time() * 1000)}"
    if not name_client:
        name_client = name
    if not topic:
        topic = "Автотест"
    if not description:
        description = f"<p>{name}</p>"

    return {
        "content_id": content_id,
        "type": "test",
        "cover_uuid": cover_uuid,
        "name": name,
        "name_client": name_client,
        "topic": topic,
        "description": description,
        "settings": {
            "completion_condition": {
                "condition_type": "percentage",
                "percentage": {"percent": completion_percent, "questions": 0},
                "score": {"count": 0}
            },
            "passage_time": {"count": passage_time_count, "is_active": passage_time_active},
            "tries": {"count": tries_count, "is_active": tries_active},
            "shuffle_questions_qty": {"count": 0, "is_active": False},
            "shuffle_questions": {"count": 0, "is_active": shuffle_questions_active},
            "shuffle_answers": {"count": 0, "is_active": shuffle_answers_active},
            "proctoring": {
                "is_active": False,
                "mode": "offline",
                "allow_to_use_websites": False,
                "allow_to_use_books": False,
                "allow_to_use_paper": True,
                "allow_to_use_messengers": False,
                "allow_to_use_calculator": True,
                "allow_to_use_excel": False,
                "allow_to_use_human_assistant": False,
                "allow_absence_in_frame": False,
                "allow_voices": False,
                "allow_wrong_gaze_direction": False,
                "custom_rules": ""
            },
            "is_allow_question_move": {"count": 0, "is_active": is_allow_question_move_active},
            "feedback": {
                "is_active": feedback_active,
                "onSuccess": {"text": "Верно!"},
                "onFail": {"text": "Неверно!"},
                "default": {"text": None}
            }
        }
    }

def generate_question_payload(
    order: int = 1,
    question_type: str = "single",
    text: str = None,
    time: int = 2,
    weight: int = 1,
    answers: list = None
) -> dict:
    """Генерация payload для вопроса теста."""
    import uuid
    if not text:
        text = f"Вопрос #{order}"
    if not answers:
        answers = [
            {
                "id": str(uuid.uuid4()),
                "actions": [],
                "correct": True,
                "text": "Правильный ответ"
            },
            {
                "id": str(uuid.uuid4()),
                "actions": [],
                "correct": False,
                "text": "Неправильный ответ"
            }
        ]
    return {
        "order": order,
        "type": question_type,
        "text": text,
        "settings": {
            "time": time,
            "weight": weight
        },
        "answers": answers
    }

def generate_poll_payload(
    name: str = None,
    name_client: str = None,
    topic: str = "Автотест",
    description: str = None,
    cover_uuid: str = "c0bd6d02-d9d4-4cd8-a064-a3dbe7b4aa99",
    completion_percent: int = 60,
    tenant_organization_id: int = 2
) -> dict:
    """Генерация payload для создания опроса (type=poll)."""
    if not name:
        timestamp = int(time.time() * 1000)
        name = f"Автотест_опрос_админка_{timestamp}"
    else:
        timestamp = int(time.time() * 1000)
    if not name_client:
        name_client = f"Автотест_опрос_внешка_{timestamp}"
    if not description:
        description = f"<p>Описание - автотест опроса</p>"

    return {
        "type": "poll",
        "name": name,
        "name_client": name_client,
        "topic": topic,
        "cover_uuid": cover_uuid,
        "description": description,
        "screens": {
            "intro": {
                "title": "Вступительный слайд",
                "button_text": "Начать",
                "is_active": True
            },
            "onSuccess": {
                "title": "Успешное прохождение",
                "description": "Поздравляем, вы успешно завершили тестирование!"
            },
            "onFail": {
                "title": "Неправильное прохождение",
                "description": "К сожалению, вы не прошли тестирование."
            },
            "default": {
                "title": "Спасибо за прохождение опроса!",
                "description": ""
            }
        },
        "settings": {
            "completion_condition": {
                "condition_type": "percentage",
                "percentage": {"percent": completion_percent, "questions": 0},
                "score": {"count": 0}
            },
            "passage_time": {"count": 0, "is_active": False},
            "tries": {"count": 1, "is_active": False},
            "shuffle_questions_qty": {"is_active": False, "count": 0},
            "shuffle_questions": {"is_active": True},
            "shuffle_answers": {"is_active": True},
            "is_allow_question_move": {"is_active": True},
            "feedback": {
                "is_active": False,
                "onSuccess": {"text": "Верно!"},
                "onFail": {"text": "Неверно!"},
                "default": {"text": ""}
            }
        },
        "additional_params": {"tenant_organization_id": tenant_organization_id}
    }

def generate_test_update_proctoring_payload(
    content_id: int,
    name: str,
    is_active: bool = True,
    mode: str = "offline",
    allow_to_use_websites: bool = True,
    allow_to_use_books: bool = True,
    allow_to_use_paper: bool = True,
    allow_to_use_messengers: bool = True,
    allow_to_use_calculator: bool = True,
    allow_to_use_excel: bool = True,
    allow_to_use_human_assistant: bool = True,
    allow_absence_in_frame: bool = True,
    allow_voices: bool = True,
    allow_wrong_gaze_direction: bool = True,
    custom_rules: str = ""
) -> dict:
    """Генерация payload для активации прокторинга."""
    return {
        "content_id": content_id,
        "type": "test",
        "cover_uuid": "",
        "name": name,
        "name_client": name,
        "topic": name,
        "description": f"<p>{name}</p>",
        "settings": {
            "completion_condition": {
                "condition_type": "percentage",
                "percentage": {"percent": 0, "questions": 0},
                "score": {"count": 0}
            },
            "passage_time": {"count": 0, "is_active": False},
            "tries": {"count": 3, "is_active": False},
            "shuffle_questions_qty": {"count": 0, "is_active": False},
            "shuffle_questions": {"count": 0, "is_active": True},
            "shuffle_answers": {"count": 0, "is_active": True},
            "proctoring": {
                "is_active": is_active,
                "mode": mode,
                "allow_to_use_websites": allow_to_use_websites,
                "allow_to_use_books": allow_to_use_books,
                "allow_to_use_paper": allow_to_use_paper,
                "allow_to_use_messengers": allow_to_use_messengers,
                "allow_to_use_calculator": allow_to_use_calculator,
                "allow_to_use_excel": allow_to_use_excel,
                "allow_to_use_human_assistant": allow_to_use_human_assistant,
                "allow_absence_in_frame": allow_absence_in_frame,
                "allow_voices": allow_voices,
                "allow_wrong_gaze_direction": allow_wrong_gaze_direction,
                "custom_rules": custom_rules
            },
            "is_allow_question_move": {"count": 0, "is_active": True},
            "feedback": {
                "is_active": False,
                "onSuccess": {"text": "Верно!"},
                "onFail": {"text": "Неверно!"},
                "default": {"text": None}
            }
        }
    }
def generate_material_payload(
    name: str = None,
    content_id: int = 7,
    material_type: str = "course",
    is_visible: bool = True,
    short_description: str = "",
    description: str = "",
    article_text: str = "",
    cover_uuid: str = "",
    duration: int = 0,
    files: list = None,
    authors: list = None,
    bundles: list = None,
    categories: list = None,
    competencies: list = None,
    tags: list = None,
    professional_areas: list = None,
) -> dict:
    """Генерация payload для создания материала в базе знаний."""
    if not name:
        timestamp = int(time.time() * 1000)
        name = f"Автотест_Курс_{timestamp}"
    if files is None:
        files = []
    if authors is None:
        authors = [{"name": "AQA", "avatar_url": "", "avatar_uuid": ""}]
    if bundles is None:
        bundles = [4]
    if categories is None:
        categories = [7]
    if competencies is None:
        competencies = [7]
    if tags is None:
        tags = [8]
    if professional_areas is None:
        professional_areas = []

    return {
        "data": {
            "id": None,
            "name": name,
            "content_id": content_id,
            "short_description": short_description,
            "type": material_type,
            "is_visible": is_visible,
            "description": description,
            "article_text": article_text,
            "cover_uuid": cover_uuid,
            "duration": duration,
            "files": files,
            "authors": authors,
            "bundles": bundles,
            "categories": categories,
            "competencies": competencies,
            "tags": tags,
            "professional_areas": professional_areas,
        }
    }
def generate_homework_payload(
    name: str = None,
    name_client: str = None,
    description: str = None,
    duration: str = "10",
    activity_category_id: int = 10,
    grade_type: str = "five_point",
    teacher_ids: list = None,
    inspector_ids: list = None,
    cover_uuid: str = "",
    archive_uuid: str = "",
    sub_files_uuids: list = None,
) -> dict:
    """Генерация payload для создания практического задания (homework)."""
    if not name:
        timestamp = int(time.time() * 1000)
        name = f"Автотест_практическое_задание_админка_{timestamp}"
    if not name_client:
        # для уникальности используем тот же timestamp
        ts = int(time.time() * 1000)
        name_client = f"Автотест_практическое_задание_внешка_{ts}"
    if not description:
        description = "<p>Автотест_практическое_задание_описание</p>"
    if teacher_ids is None:
        teacher_ids = [16]   # ID преподавателя по умолчанию
    if inspector_ids is None:
        inspector_ids = [16]
    if sub_files_uuids is None:
        sub_files_uuids = []

    return {
        "data": {
            "attributes": {
                "inspectors": [],
                "teachers": [],
                "duration": duration,
                "teacher_ids": teacher_ids,
                "content_type": "homework",
                "grade_type": grade_type,
                "name": name,
                "name_client": name_client,
                "activity_category_id": activity_category_id,
                "description": description,
                "inspector_ids": inspector_ids,
                "archive_uuid": archive_uuid,
                "cover_uuid": cover_uuid,
                "sub_files_uuids": sub_files_uuids
            },
            "includes": {
                "archive": [],
                "image": [],
                "spreadsheet": [],
                "video": [],
                "pdf": [],
                "document": [],
                "offline": [],
                "webinar": [],
                "cover": [],
                "sub_files": []
            }
        }
    }

def generate_homework_ten_point_payload(
    name: str = None,
    name_client: str = None,
    description: str = None,
    duration: str = "10",
    activity_category_id: int = 10,
    teacher_ids: list = None,
    inspector_ids: list = None,
    cover_uuid: str = "",
    archive_uuid: str = "",
    sub_files_uuids: list = None,
) -> dict:
    """Генерация payload для 10‑балльного практического задания."""
    if not name:
        timestamp = int(time.time() * 1000)
        name = f"Автотест_ПР_10баллов_{timestamp}"
    if not name_client:
        ts = int(time.time() * 1000)
        name_client = f"Автотест_ПР_10баллов_внешка_{ts}"
    if not description:
        description = "<p>Автотест_ПР_10баллов_описание</p>"
    if teacher_ids is None:
        teacher_ids = [16]
    if inspector_ids is None:
        inspector_ids = [16]
    if sub_files_uuids is None:
        sub_files_uuids = []

    return {
        "data": {
            "attributes": {
                "inspectors": [],
                "teachers": [],
                "duration": duration,
                "teacher_ids": teacher_ids,
                "content_type": "homework",
                "grade_type": "ten_point",       # <-- ключевое отличие
                "name": name,
                "name_client": name_client,
                "activity_category_id": activity_category_id,
                "description": description,
                "inspector_ids": inspector_ids,
                "archive_uuid": archive_uuid,
                "cover_uuid": cover_uuid,
                "sub_files_uuids": sub_files_uuids
            },
            "includes": {
                "archive": [],
                "image": [],
                "spreadsheet": [],
                "video": [],
                "pdf": [],
                "document": [],
                "offline": [],
                "webinar": [],
                "cover": [],
                "sub_files": []
            }
        }
    }
def generate_homework_pass_fail_payload(
    name: str = None,
    name_client: str = None,
    description: str = None,
    duration: str = "10",
    activity_category_id: int = 10,
    teacher_ids: list = None,
    inspector_ids: list = None,
    cover_uuid: str = "",
    archive_uuid: str = "",
    sub_files_uuids: list = None,
) -> dict:
    """Генерация payload для практического задания (зачёт/незачёт)."""
    if not name:
        timestamp = int(time.time() * 1000)
        name = f"Автотест_ПР_зачёт_{timestamp}"
    if not name_client:
        ts = int(time.time() * 1000)
        name_client = f"Автотест_ПР_зачёт_внешка_{ts}"
    if not description:
        description = "<p>Автотест_ПР_зачёт_описание</p>"
    if teacher_ids is None:
        teacher_ids = [16]
    if inspector_ids is None:
        inspector_ids = [16]
    if sub_files_uuids is None:
        sub_files_uuids = []

    return {
        "data": {
            "attributes": {
                "inspectors": [],
                "teachers": [],
                "duration": duration,
                "teacher_ids": teacher_ids,
                "content_type": "homework",
                "grade_type": "pass_fail",       # <-- ключевое отличие
                "name": name,
                "name_client": name_client,
                "activity_category_id": activity_category_id,
                "description": description,
                "inspector_ids": inspector_ids,
                "archive_uuid": archive_uuid,
                "cover_uuid": cover_uuid,
                "sub_files_uuids": sub_files_uuids
            },
            "includes": {
                "archive": [],
                "image": [],
                "spreadsheet": [],
                "video": [],
                "pdf": [],
                "document": [],
                "offline": [],
                "webinar": [],
                "cover": [],
                "sub_files": []
            }
        }
    }
def generate_certificate_template_payload(
    name: str = None,
    template_type: str = "program_stream",  # или "activity"
    file_id: str = None,
    config: str = "program3",  # зависит от типа
    serial_prefix: str = None,
) -> dict:
    """Генерация payload для создания шаблона сертификата."""
    ts = int(time.time() * 1000)
    if not name:
        name = f"Автотест_шаблон_сертификата_{ts}"
    if not serial_prefix:
        serial_prefix = str(ts)[-6:]  # уникальный префикс
    if template_type == "activity":
        config = "activity2"
    return {
        "file_id": file_id,
        "name": name,
        "type": template_type,
        "config": config,
        "marks": {
            "userFio": True,
            "duration": True,
            "completionDate": True,
            "activityName": True,
            "programName": True,
            "programPeriod": True,
            "programScheduledItemsVisitsPercent": True,
            "programCompletionPercent": True,
            "serialNumber": True,
        },
        "serial_prefix": serial_prefix,
    }