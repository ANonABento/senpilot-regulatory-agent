"""Quick test: matter search with button index 1."""

from playwright.sync_api import sync_playwright

from regulatory_agent.config import settings
from regulatory_agent.scraper.browser import wait_for_ready


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(120000)
        page.goto(settings.uarb_base_url)
        wait_for_ready(page)
        page.wait_for_function(
            "() => document.body.innerText.includes('Go Directly to Matter')",
            timeout=120000,
        )

        matter_box = page.locator('.fm-textarea:has(.placeholder:text-is("eg M01234"))')
        matter_box.locator(".text").click(force=True)
        page.keyboard.press("Control+A")
        page.keyboard.type("M12205", delay=30)
        print("Typed. Field:", repr(matter_box.locator(".text").inner_text()))

        page.locator("button").filter(has_text="Search").nth(1).click(force=True)
        page.wait_for_timeout(20000)

        body = page.locator("body").inner_text()
        print("M12205:", "M12205" in body)
        print("Exhibits - 13:", "Exhibits - 13" in body)
        print("Other Documents - 21:", "Other Documents - 21" in body)
        print(body[:2000])
        browser.close()


if __name__ == "__main__":
    main()
