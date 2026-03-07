from __future__ import annotations

import json
from typing import Any

from app.integrations.ollama_client import OllamaClient
from app.scraping.models import MatterOverview
from app.services.models import DocumentType


def build_summary_prompt_input(
    *,
    sender: str,
    subject: str,
    matter_number: str,
    requested_document_type: DocumentType,
    overview: MatterOverview,
    downloaded_count: int,
) -> dict[str, Any]:
    requested_total = overview.counts.get(requested_document_type)

    return {
        "sender": sender,
        "original_subject": subject,
        "matter_number": matter_number,
        "requested_document_type": requested_document_type.value,
        "matter": {
            "status": overview.status,
            "title_description": overview.title_description,
            "type": overview.type_value,
            "category": overview.category_value,
            "date_received": overview.date_received,
            "decision_date": overview.decision_date,
            "outcome": overview.outcome,
        },
        "counts": {
            "exhibits": overview.counts.exhibits,
            "key_documents": overview.counts.key_documents,
            "other_documents": overview.counts.other_documents,
            "transcripts": overview.counts.transcripts,
            "recordings": overview.counts.recordings,
        },
        "download": {
            "requested_document_type": requested_document_type.value,
            "requested_total_available": requested_total,
            "downloaded_count": downloaded_count,
            "download_limit": 10,
        },
    }


def draft_reply_email(*, ollama: OllamaClient, summary_input: dict[str, Any]) -> str:

    
    system = """
    You are an email drafting assistant for a legal-document retrieval workflow.
    Write a concise, professional reply email from the provided JSON input.
    Return valid JSON only in this exact format:
    {
    "email_body": "..."
    }

    Requirements for the email:
    - Start with "Hi,"
    - End with:
    Best,
    UARB Document Agent :D
    - Use only facts present in the input
    - Do not invent or assume missing information
    - If some fields are missing, omit them naturally
    - Mention the matter number is about title/description
    - Mention that it relates to the type within the category when available
    - Mention date_recieved and/or decision date when available
    - Summarize the document counts:
    Exhibits, Key Documents, Other Documents, Transcripts, Recordings
    - State whether any requested documents were downloaded
    - If downloaded_count > 0, say how many were downloaded out of how many available and that they were attached as a ZIP
    - If downloaded_count == 0, say that no documents were downloaded from the requested document type tab
    - Plain text only
    - Keep it short and readable

    Your output must be valid JSON parseable by Python.
    Do not include markdown, comments, or extra keys.
    """.strip()

    prompt = f"""Draft a reply email using this case data.
    Input JSON:
    {json.dumps(summary_input, indent=2)}.
    """

    data = ollama.extract_json(
        prompt=prompt,
        system=system + ' Return JSON with exactly one key: "email_body".',
    )

    email_body = data.get("email_body")
    if not isinstance(email_body, str) or not email_body.strip():
        raise ValueError("LLM did not return a valid email_body")

    return email_body.strip()


def fallback_reply_email(summary_input: dict[str, Any]) -> str:
    matter = summary_input["matter"]
    counts = summary_input["counts"]
    download = summary_input["download"]
    matter_number = summary_input["matter_number"]

    parts = [
        f"Hi,",
        "",
        f"{matter_number} is about {matter.get('title_description') or 'the requested matter'}.",
    ]

    type_value = matter.get("type")
    category_value = matter.get("category")
    if type_value or category_value:
        if type_value and category_value:
            parts.append(f"It relates to {type_value} within the {category_value} category.")
        elif category_value:
            parts.append(f"It falls under the {category_value} category.")
        elif type_value:
            parts.append(f"It relates to {type_value}.")

    date_received = matter.get("date_received")
    final_date = matter.get("decision_date")
    if date_received and final_date:
        parts.append(
            f"The matter had an initial filing on {date_received} and a final filing or decision date of {final_date}."
        )
    elif date_received:
        parts.append(f"The matter had an initial filing on {date_received}.")
    elif final_date:
        parts.append(f"The matter has a final filing or decision date of {final_date}.")

    parts.append(
        "I found "
        f"{counts['exhibits']} Exhibits, "
        f"{counts['key_documents']} Key Documents, "
        f"{counts['other_documents']} Other Documents, "
        f"{counts['transcripts']} Transcripts, and "
        f"{counts['recordings']} Recordings."
    )

    if download["downloaded_count"] > 0:
        parts.append(
            f"I downloaded {download['downloaded_count']} out of the "
            f"{download['requested_total_available']} available {download['requested_document_type']} "
            f"and attached them as a ZIP."
        )
    else:
        parts.append(
            f"No documents were downloaded from the {download['requested_document_type']} tab."
        )

    parts.append("")
    parts.append("Best,")
    parts.append("UARB Document Agent :D")

    return "\n".join(parts)