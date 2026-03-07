from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.sync_api import TimeoutError as PWTimeoutError, sync_playwright

from app.core.settings import settings
from app.scraping.models import DownloadedDocument
from app.scraping.models import MatterCounts, MatterOverview
from app.services.models import DocumentType


@dataclass
class UARBScraperConfig:
    base_url: str = settings.UARB_BASE_URL
    headless: bool = True
    nav_timeout_ms: int = 45_000
    action_timeout_ms: int = 20_000
    max_docs: int = 10


class UARBScraper:
    def __init__(self, cfg: Optional[UARBScraperConfig] = None) -> None:
        self.cfg = cfg or UARBScraperConfig()

    # ---------- Public API ----------

    def download_documents(
        self,
        *,
        matter_number: str,
        document_type: DocumentType,
        out_dir: Path,
    ) -> Tuple[MatterOverview, List[DownloadedDocument]]:
        """
        Opens matter page, extracts overview/counts, clicks requested tab, downloads up to max_docs.
        """
        out_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.cfg.headless)
            context = browser.new_context(accept_downloads=True)
            context.set_default_navigation_timeout(self.cfg.nav_timeout_ms)
            context.set_default_timeout(self.cfg.action_timeout_ms)
            page = context.new_page()

            try:
                self._open_matter_page(page, matter_number=matter_number)
                overview = self._extract_overview(page, matter_number=matter_number)

                self._click_tab(page, document_type.value)

                count = overview.counts.get(document_type)
                downloads = self._download_go_get_it_files(page, out_dir, limit=self.cfg.max_docs, count=count)
                print(overview)
                return overview, downloads

            finally:
                context.close()
                browser.close()

    # ---------- Navigation ----------

    def _open_matter_page(self, page, *, matter_number: str) -> None:
        
        page.goto(self.cfg.base_url, wait_until="domcontentloaded", timeout=60000)
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

    # ---------- Overview extraction ----------

    def _extract_overview(self, page, *, matter_number: str) -> MatterOverview:
        text_nodes = page.locator("div.text")
        raw_values = []

        for i in range(text_nodes.count()):
            txt = self._safe_text(text_nodes.nth(i))
            if txt:
                raw_values.append(self._normalize_text(txt))

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

        result = MatterOverview()

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
            elif result.category_value is None:
                result.category_value = value
            elif result.type_value is None:
                result.type_value = value
        
        page.get_by_text(matter_number).click()
        page.wait_for_timeout(10000)

        counts_map = self.extract_doc_counts(page)
        counts = MatterCounts(
            exhibits=counts_map.get("exhibits", 0),
            key_documents=counts_map.get("key_documents", 0),
            other_documents=counts_map.get("other_documents", 0),
            transcripts=counts_map.get("transcripts", 0),
            recordings=counts_map.get("recordings", 0),
        )
        result.counts = counts
    
        return result


    def extract_doc_counts(self, page) -> dict:

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
    

    def _safe_text(self, locator) -> Optional[str]:
        try:
            text = locator.inner_text(timeout=5000).strip()
            return text if text else None
        except Exception:
            return None
        
    def _normalize_text(self, text: str) -> str:
        return " ".join(text.replace("\xa0", " ").split())
    

    def _click_tab(self, page, tab_prefix: str) -> None:
        tab = page.get_by_text(re.compile(rf"^{re.escape(tab_prefix)}\s*-\s*\d+\s*$"))
        tab.first.click()
        page.wait_for_timeout(300)


    def _download_go_get_it_files(self, page, out_dir: Path, limit: int, count: int) -> List[DownloadedDocument]:
        
        results: List[DownloadedDocument] = []

        if count == 0:
            return results

        target = min(limit, count)
        downloaded_count = 0
        downloaded = set()
        
        panel = page.locator(".v-panel.iwp-list-base-layout-style").first

        while downloaded_count < target:
            buttons = page.get_by_role(
                "button",
                name=re.compile(r"^\s*GO\s+GET\s+IT\s*$", re.IGNORECASE)
            )

            count = buttons.count()
            found_new = False

            for i in range(count):
                btn = buttons.nth(i)

                try:
                    if not btn.is_visible():
                        continue

                    key = btn.evaluate("""
                        el => {
                            const row = el.closest('[role="row"]') || el.closest('.v-csslayout') || el.parentElement;
                            return row ? row.innerText : el.innerText;
                        }
                    """)

                    if key in downloaded:
                        continue

                    # Download the file linked in this row

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
                    save_path = self._dedupe_path(out_dir / suggested_name)

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
                    
                    downloaded.add(key)
                    downloaded_count += 1
                    found_new = True

                    if downloaded_count >= target:
                        break

                except PWTimeoutError:
                    print("Timeout error, skipping this file.")
                    continue

            if downloaded_count >= target:
                break

            if not found_new:
                panel.hover()
                page.mouse.wheel(0, 300)
                page.wait_for_timeout(700) 
        
        return results

    def _dedupe_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        stem, suffix = path.stem, path.suffix
        for n in range(2, 999):
            candidate = path.with_name(f"{stem}__{n}{suffix}")
            if not candidate.exists():
                return candidate
        return path.with_name(f"{stem}__overflow{suffix}")
