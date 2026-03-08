from __future__ import annotations

from pathlib import Path
from typing import Any

from app.integrations.mailgun_client import MailgunClient
from app.integrations.ollama_client import OllamaClient
from app.scraping.uarb_scraper import UARBScraper
from app.services.email_summary import build_summary_prompt_input, draft_reply_email, fallback_reply_email
from app.services.job_workspace import create_job_workspace
from app.services.models import DocumentType
from app.storage.zip_builder import zip_files
from app.core.settings import settings


def run_inbound_email_pipeline(*, payload: dict[str, Any], task_id: str | None = None) -> dict[str, Any]:

    sender = str(payload["sender"]).strip()
    subject = str(payload.get("subject") or "").strip()
    matter_number = str(payload["matter_number"]).strip()
    document_type = DocumentType(payload["document_type"])

    mailgun = MailgunClient(
        api_key=settings.MAILGUN_API_KEY,
        domain=settings.MAILGUN_DOMAIN,
        from_email=settings.MAILGUN_FROM,
    )

    if payload.get("parse_strategy") == "clarification_needed":
        mailgun.send_message(
            to_email=sender,
            subject="Clarification needed",
            text=(
                "Hi,\n\n"
                "We couldn't understand your request.\n\n"
                "Please include:\n"
                "- Matter number (e.g. M12205)\n"
                "- Document type (exhibits, transcripts, key documents, etc.)\n\n"
                "Example:\n"
                "M12205 exhibits\n\n"
                "Thanks!"
            ),
        )
        return {
            "ok": True,
            "sender": sender,
            "clarification_requested": True,
        }


    workspace = create_job_workspace(
        base_dir=Path("tmp_jobs"),
        task_id=task_id,
        matter_number=matter_number,
        document_type=document_type,
    )

    scraper = UARBScraper()
    overview, downloads = scraper.download_documents(
        matter_number=matter_number,
        document_type=document_type,
        out_dir=workspace.downloads_dir,
    )

    zip_path = None
    if downloads:
        zip_path = zip_files(
            files=[d.saved_path for d in downloads],
            zip_path=workspace.zip_path,
        )

    summary_input = build_summary_prompt_input(
        sender=sender,
        subject=subject,
        matter_number=matter_number,
        requested_document_type=document_type,
        overview=overview,
        downloaded_count=len(downloads),
    )

    email_body = fallback_reply_email(summary_input)

    # USING LLM (OLLAMA) FOR LOCAL USE
    """ 
    ollama = OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
    )

    try:
        email_body = draft_reply_email(
            ollama=ollama,
            summary_input=summary_input,
        )
    except Exception:
        email_body = fallback_reply_email(summary_input)
    """

    print('\n' + email_body)

    mailgun.send_message(
        to_email=sender,
        subject=f"Documents for {matter_number}",
        text=email_body,
        attachment_paths=[zip_path] if zip_path else [],
    )

    return {
        "ok": True,
        "sender": sender,
        "matter_number": matter_number,
        "document_type": document_type.value,
        "downloaded_count": len(downloads),
        "zip_path": str(zip_path) if zip_path else None,
        "workspace": str(workspace.root_dir),
    }

