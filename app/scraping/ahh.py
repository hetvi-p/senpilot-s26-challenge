import re

from pathlib import Path

from playwright.sync_api import sync_playwright



UARB_URL = "https://uarb.novascotia.ca/fmi/webd/UARB15"

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

def _click_tab(page, tab_prefix: str) -> None:
    tab = page.get_by_text(re.compile(rf"^{re.escape(tab_prefix)}\s*-\s*\d+\s*$"))
    tab.first.click()
    page.wait_for_timeout(300)

def main():
    matter_number = "M12205"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=250)
        page = browser.new_page()

        open_search_result(page, matter_number)
        
        page.get_by_text(matter_number).click()
        page.wait_for_timeout(10000)


        out_dir = Path("downloads")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        _click_tab(page, "Exhibits")
        page.wait_for_timeout(10000)

        clicked = 0
        target = 9
        seen = set()

        panel = page.locator(".v-panel.iwp-list-base-layout-style").first

        while clicked < target:
            buttons = page.get_by_role("button", name="GO GET IT")
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

                    if key in seen:
                        continue

                    seen.add(key)
                    clicked += 1
                    found_new = True

                    print(f"Clicked {clicked}/{target}")

                    page.wait_for_timeout(700)

                    if clicked >= target:
                        break

                except Exception as e:
                    print(f"Skipping button {i}: {e}")

            if clicked >= target:
                break

            if not found_new:
                panel.hover()
                page.mouse.wheel(0, 300)
                page.wait_for_timeout(700) 

        for i in seen:
            print(f"Seen key: {i}")
        browser.close()



if __name__ == "__main__":
    main()


