from app.services.pipeline import run_inbound_email_pipeline

payload = {
    "sender": "hetvi.5612@gmail.com",
    "subject": "Docs please",
    "matter_number": "M12205",
    "document_type": "Recordings",
}

run_inbound_email_pipeline(
    payload=payload,
    task_id="manual_test",
)