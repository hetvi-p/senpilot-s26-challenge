from pathlib import Path

from app.scraping.uarb_scraper import UARBScraper
from app.services.models import DocumentType


if __name__ == "__main__":
    scraper = UARBScraper()
    overview, docs = scraper.download_documents(
        matter_number="M12205",
        document_type=DocumentType.OTHER_DOCUMENTS,
        out_dir=Path("tmp_downloads/M12205/other_documents"),
    )
    print(overview)

    print(f"Downloaded {len(docs)} docs:")

    for d in docs:
        print("-", d.saved_path)

