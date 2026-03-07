from app.services.parser import parse_email_request
from app.core.errors import ParseError
from app.integrations.ollama_client import OllamaClient
from app.services.models import DocumentType, ParsedEmailRequest
from app.core.settings import settings


def main():
    subject = "q"
    body_plain = "q"

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
        ollama=ollama,  # Assuming no Ollama integration for this test
    )
    
    print(parsed)


if __name__ == "__main__":
    main()