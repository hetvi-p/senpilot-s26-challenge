
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeoutError, sync_playwright



from dataclasses import dataclass, asdict
from typing import Optional
from playwright.sync_api import sync_playwright
import re
from app.scraping.models import DownloadedDocument


UARB_URL = "https://uarb.novascotia.ca/fmi/webd/UARB15"


@dataclass
class MatterSearchResult:
    matter_number: Optional[str] = None
    status: Optional[str] = None
    title_description: Optional[str] = None
    type_value: Optional[str] = None
    category_value: Optional[str] = None
    date_received: Optional[str] = None
    decision_date: Optional[str] = None
    outcome: Optional[str] = None


def safe_text(locator) -> Optional[str]:
    try:
        text = locator.inner_text(timeout=5000).strip()
        return text if text else None
    except Exception:
        return None


def open_search_result(page, matter_number: str):
    page.goto(UARB_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    placeholder = page.locator("div.placeholder").filter(has_text="eg M01234").first
    placeholder.wait_for(state="visible", timeout=30000)

    inner_border = placeholder.locator(
        "xpath=ancestor::div[contains(@class, 'inner_border')]"
    ).first
    inner_border.wait_for(state="visible", timeout=10000)

    text_div = inner_border.locator("div.text").first

    try:
        text_div.click(timeout=10000)
    except Exception:
        inner_border.click(timeout=10000)

    page.wait_for_timeout(500)
    page.keyboard.type(matter_number, delay=80)
    page.wait_for_timeout(800)

    # Click the top Search button only
    search_button = page.get_by_role("button", name="Search").nth(0)
    search_button.click(timeout=20000)

    page.wait_for_timeout(6000)




def normalize_text(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def scrape_search_result_row(page) -> MatterSearchResult:
    text_nodes = page.locator("div.text")
    raw_values = []

    for i in range(text_nodes.count()):
        txt = safe_text(text_nodes.nth(i))
        if txt:
            raw_values.append(normalize_text(txt))

    print("\nNormalized div.text values:")
    for i, value in enumerate(raw_values):
        print(f"[{i}] {value!r}")

    noise = {
        "Exhibits",
        "Key Docs",
        "Other Docs",
        "Transcripts",
        "Recordings",
        "Hearings",
        "Related Matters",
        "Matter No Status",
        "Title - Description",
        "Type Category",
        "Found: 1",
        "Public Documents Database",
        "Date Received",
        "Decision Date",
        "Outcome",
    }

    values = [v for v in raw_values if (v not in noise and not v.startswith("Found:"))]

    print("\nFiltered candidate values:")
    for i, value in enumerate(values):
        print(f"[{i}] {value!r}")

    result = MatterSearchResult()

    date_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}$")

    for value in values:
        if result.matter_number is None and re.fullmatch(r"M\d{5}", value):
            result.matter_number = value
        elif result.date_received is None and date_pattern.fullmatch(value):
            result.date_received = value
        elif result.decision_date is None and date_pattern.fullmatch(value):
            result.decision_date = value
        elif result.status is None and value in {
            "Open", 
            "Closed", 
            "Pending", 
            "Suspended", 
            "Incomplete", 
            "Awaiting Final Order", 
            "Awaiting Compliance"
        }:
            result.status = value
        elif result.outcome is None and value in {
            "Allowed/Approved",
            "Allowed in part",
            "Allowed - conditions",
            "Sanctioned",
            "Dismissed/Denied",
            "Directions given",
            "Discontinued",
            "Accepted as filed",
            "Not applicable"
        }:
            result.outcome = value
        elif value.isdigit():
            continue
        elif result.title_description is None and (
            len(value) > 40 or any(k in value for k in ["Request", "Application", "Appeal", "Filing", ":", "-"])
        ):
            result.title_description = value
        elif result.type_value is None:
            result.type_value = value
        elif result.category_value is None:
            result.category_value = value
        
    return result

def extract_doc_counts(page) -> dict:
    """
    Scrape document counts from the matter detail page tabs.
    Returns:
        {
            "exhibits": 2,
            "key_documents": 0,
            "other_documents": 3,
            "transcripts": 0,
            "recordings": 0,
        }
    """

    expected_labels = {
        "Exhibits": "exhibits",
        "Key Documents": "key_documents",
        "Other Documents": "other_documents",
        "Transcripts": "transcripts",
        "Recordings": "recordings",
    }

    counts = {}

    # Grab all tab/button-like elements that may contain the labels
    tab_texts = page.locator("text=/^(Exhibits|Key Documents|Other Documents|Transcripts|Recordings)\\s*-\\s*\\d+$/").all_inner_texts()

    for text in tab_texts:
        text = text.strip()
        match = re.match(r"^(Exhibits|Key Documents|Other Documents|Transcripts|Recordings)\s*-\s*(\d+)$", text)
        if match:
            label, count = match.groups()
            counts[expected_labels[label]] = int(count)

    # Ensure all keys exist even if something is missing
    for label, key in expected_labels.items():
        counts.setdefault(key, 0)

    return counts

def _click_tab(page, tab_prefix: str) -> None:
    tab = page.get_by_text(re.compile(rf"^{re.escape(tab_prefix)}\s*-\s*\d+\s*$"))
    tab.first.click()
    page.wait_for_timeout(300)

def _download_go_get_it_files(page, out_dir: Path, limit: int) -> List[DownloadedDocument]:
    results: List[DownloadedDocument] = []

    buttons = page.get_by_role(
        "button",
        name=re.compile(r"^\s*GO\s+GET\s+IT\s*$", re.IGNORECASE)
    )

    count = buttons.count()
    if count == 0:
        return results

    to_take = min(limit, count)

    for i in range(to_take):
        # re-query buttons each loop in case DOM re-renders
        buttons = page.get_by_role(
            "button",
            name=re.compile(r"^\s*GO\s+GET\s+IT\s*$", re.IGNORECASE)
        )
        btn = buttons.nth(i)

        try:
            # Step 1: open modal
            btn.click()

            # Step 2: wait for modal
            modal = page.get_by_text("Download Files").locator(
                "xpath=ancestor::*[self::div][1]"
            )
            modal.wait_for(timeout=10000)

            # Step 3: locate file inside modal
            file_link = page.locator(
                "text=/^\\s*.+\\.(pdf|doc|docx|xls|xlsx|zip)\\s*$/i"
            ).first

            file_link.wait_for(timeout=10000)

            # Step 4: download
            with page.expect_download() as dl_info:
                file_link.click()

            download = dl_info.value

            # Use browser-suggested filename
            suggested_name = download.suggested_filename or f"document_{i+1}"
            save_path = _dedupe_path(out_dir / suggested_name)

            download.save_as(str(save_path))

            results.append(
                DownloadedDocument(
                    saved_path=save_path
                )
            )

            # Step 5: close modal
            close_btn = page.get_by_role(
                "button",
                name=re.compile(r"^\s*Close\s*$", re.IGNORECASE)
            )
            close_btn.click(timeout=5000)

            # Step 6: wait for modal to disappear
            page.locator("text=Download Files").wait_for(
                state="hidden",
                timeout=10000
            )

        except PWTimeoutError:
            continue

    return results

def _dedupe_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for n in range(2, 999):
        candidate = path.with_name(f"{stem}__{n}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}__overflow{suffix}")


def main():
    matter_number = "M12720"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=250)
        page = browser.new_page()

        open_search_result(page, matter_number)
        result = scrape_search_result_row(page)

        print("\nSCRAPED OBJECT:")
        print(asdict(result))
        
        page.get_by_text(matter_number).click()
        page.wait_for_timeout(10000)

        counts = extract_doc_counts(page)
        print(counts)

        out_dir = Path("downloads")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        _click_tab(page, "Exhibits")

        downloads = _download_go_get_it_files(page, out_dir, limit=10)
        print("\nDOWNLOADED DOCUMENTS:")
        for doc in downloads:
            print(asdict(doc))

        browser.close()


if __name__ == "__main__":
    main()