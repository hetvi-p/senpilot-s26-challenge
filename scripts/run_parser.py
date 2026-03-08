from app.services.parser import parse_email_request
from app.core.errors import ParseError
from app.integrations.ollama_client import OllamaClient
from app.services.models import DocumentType, ParsedEmailRequest
from app.core.settings import settings


def main():
    subject = "Need Docs please"
    body_plain = "Hi Agent, Can you give me Other Documents files from M12205? Thanks!"

    ollama = None
    if settings.OLLAMA_BASE_URL and settings.OLLAMA_MODEL:
        ollama = OllamaClient(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)

    
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
    
    print(parsed)


if __name__ == "__main__":
    main()