import json

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from uuid import uuid4

from app.core.settings import settings
from app.core.errors import WebhookAuthError, ParseError
from app.storage.token_store import MemoryTokenStore
from app.services.mailgun_webhook_auth import authenticate_mailgun_webhook
from app.services.parser import parse_email_request
from app.services.models import DocumentType
from app.integrations.ollama_client import OllamaClient
from app.services.pipeline import run_inbound_email_pipeline
from app.workers.tasks import process_inbound_email


router = APIRouter()

_token_store = MemoryTokenStore()


@router.post("/inbound")
async def inbound(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()

    # 1) Authenticate webhook
    try:
        authenticate_mailgun_webhook(
            signing_key=settings.MAILGUN_WEBHOOK_SIGNING_KEY,
            form=form,
            token_store=_token_store,
        )
    except WebhookAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

    sender = form.get("sender")
    subject = form.get("subject") or ""
    body_plain = form.get("body-plain") or ""

    message_id = form.get("Message-Id") or form.get("message-id") or form.get("Message-ID")
    if not message_id:
        headers_raw = form.get("message-headers") or form.get("message.headers")
        if isinstance(headers_raw, str):
            try:
                headers = json.loads(headers_raw)
            except json.JSONDecodeError:
                headers = []
            if isinstance(headers, list):
                for header in headers:
                    if (
                        isinstance(header, list)
                        and len(header) == 2
                        and isinstance(header[0], str)
                        and header[0].lower() == "message-id"
                    ):
                        message_id = header[1]
                        break
    message_id = str(message_id).strip().strip("<>") if message_id else ""

    if not sender:
        raise HTTPException(status_code=400, detail="Missing sender")

    # 2) Parse matter + doc type (regex first, LLM fallback)
    ollama = None
    if settings.OLLAMA_BASE_URL and settings.OLLAMA_MODEL:
        ollama = OllamaClient(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)

    try:
        parsed = parse_email_request(
            subject=subject,
            body_plain=body_plain,
            allowed_doc_types=[
                DocumentType.EXHIBITS,
                DocumentType.KEY_DOCUMENTS,
                DocumentType.OTHER_DOCUMENTS,
                DocumentType.TRANSCRIPTS,
                DocumentType.RECORDINGS,
            ],
            ollama=ollama,
        )
    except ParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 3) Enqueue the rest of the pipeline (scrape/zip/summary later)

    payload = {
            "sender": sender,
            "subject": subject,
            "body_plain": body_plain,
            "message_id": message_id,
            "matter_number": parsed.matter_number,
            "document_type": parsed.document_type.value,
            "parse_strategy": parsed.strategy,
            "parse_confidence": parsed.confidence,
        }
    

    background_tasks.add_task(
        run_inbound_email_pipeline, 
        payload=payload, 
        task_id=str(uuid4())
    )

    # Used Celery for local dev (had to switch to BackgroundTasks since Render doesnt allow in free tier)
    # process_inbound_email.delay(payload) 


    return {"queued": True, "parsed": parsed.model_dump()}
