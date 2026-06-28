"""Test matter field input methods."""

from playwright.sync_api import sync_playwright

from regulatory_agent.config import settings
from regulatory_agent.scraper.browser import wait_for_ready


def attempt(label: str, fill_fn) -> None:
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
        fill_fn(page, matter_box)
        value = matter_box.locator(".text").inner_text().strip()
        print(f"{label}: field={value!r}")
        page.locator("button").filter(has_text="Search").nth(1).click(force=True)
        page.wait_for_timeout(12000)
        body = page.locator("body").inner_text()
        print(f"  -> M12205={('M12205' in body)} Exhibits-13={('Exhibits - 13' in body)}")
        if "No Records Found" in body:
            print("  -> No records")
        browser.close()


def fill_click_type(page, matter_box):
    matter_box.locator(".text").click(force=True)
    page.keyboard.type("M12205", delay=50)


def fill_triple_click(page, matter_box):
    matter_box.locator(".text").click(force=True, click_count=3)
    page.keyboard.type("M12205", delay=50)


def fill_placeholder(page, matter_box):
    page.locator('.placeholder:text-is("eg M01234")').click(force=True)
    page.keyboard.type("M12205", delay=50)


def fill_backspace(page, matter_box):
    matter_box.locator(".text").click(force=True)
    for _ in range(10):
        page.keyboard.press("Backspace")
    page.keyboard.type("M12205", delay=50)


if __name__ == "__main__":
    attempt("click+type", fill_click_type)
    attempt("triple_click", fill_triple_click)
    attempt("placeholder", fill_placeholder)
    attempt("backspace", fill_backspace)
