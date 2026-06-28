"""Debug script for UARB navigation — run with: python scripts/debug_navigate.py"""

from pathlib import Path

from playwright.sync_api import sync_playwright

from regulatory_agent.config import settings

OUTPUT = Path("output/debug")
OUTPUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(120000)
        print("Loading...")
        page.goto(settings.uarb_base_url, wait_until="domcontentloaded")

        for wait_s in [5, 10, 15, 20, 30]:
            page.wait_for_timeout(wait_s * 1000)
            body = page.locator("body").inner_text()
            has_home = "Go Directly to Matter" in body
            has_matter = "M12205" in body or "M00001" in body
            print(f"After {wait_s}s cumulative: len={len(body)} home={has_home} matter={has_matter}")
            if has_home or has_matter:
                break

        page.screenshot(path=OUTPUT / "01_loaded.png", full_page=True)
        (OUTPUT / "01_loaded.html").write_text(page.content(), encoding="utf-8")
        body = page.locator("body").inner_text()
        print(body[:2000])

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
