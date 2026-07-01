import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.client import ApiClient
from config.settings import settings
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.certificates import CertificatesEndpoint
from api.helpers.data_generator import generate_scorm_payload, generate_certificate_template_payload

def main():
    client = ApiClient(cookie=settings.DEVELOP_COOKIE, base_url=settings.BASE_URL)
    tincan_ep = TincanEndpoint(client)
    cert_ep = CertificatesEndpoint(client)

    # --- SCORM курс ---
    print("=== SCORM курс ===")
    cover_uuid = tincan_ep.upload_cover()
    print(f"✅ Обложка загружена: {cover_uuid}")

    archive_uuid = tincan_ep.upload_archive("test_data/test_lms_scorm_2004.zip")
    print(f"✅ Архив SCORM загружен: {archive_uuid}")

    ts_scorm = int(time.time() * 1000)
    scorm_payload = generate_scorm_payload(
        name=f"Автотест_SCORM_генерация_{ts_scorm}",
        archive_uuid=archive_uuid,
        cover_uuid=cover_uuid
    )
    scorm_data = tincan_ep.create(scorm_payload)
    scorm_id = scorm_data["id"]
    print(f"✅ SCORM-курс создан: ID={scorm_id}, name={scorm_data['attributes']['name']}\n")

    # --- Сертификат ---
    print("=== Сертификат ===")
    file_id = tincan_ep.upload_certificate_file()  # загрузка PDF
    print(f"✅ PDF сертификата загружен: {file_id}")

    ts_cert = int(time.time() * 1000)
    cert_payload = generate_certificate_template_payload(
        file_id=file_id,
        template_type="activity",   # или "program_stream", зависит от нужд
        name=f"Автотест_шаблон_сертификата_{ts_cert}",
        serial_prefix=str(ts_cert)[-6:]
    )
    cert_data = cert_ep.create_template(cert_payload)
    print(f"✅ Шаблон сертификата создан: ID={cert_data['id']}, name={cert_data['name']}")

if __name__ == "__main__":
    main()