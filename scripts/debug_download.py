"""Try multiple click strategies for GO GET IT."""

from playwright.sync_api import sync_playwright

from regulatory_agent.scraper.browser import wait_for_ready
from regulatory_agent.scraper.navigate import go_to_matter


def try_click(label: str, page, action) -> bool:
    downloads = []

    def capture(d):
        downloads.append(d)

    page.once("download", capture)
    try:
        action()
    except Exception as exc:
        print(f"{label}: click error {exc}")
        return False
    page.wait_for_timeout(15_000)
    ok = len(downloads) > 0
    print(f"{label}: download={ok} pages={len(page.context.pages)}")
    if downloads:
        print(f"  file={downloads[0].suggested_filename}")
    return ok


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(120000)
        go_to_matter(page, "M12205")
        page.get_by_text("Other Documents", exact=False).first.click()
        wait_for_ready(page)
        page.wait_for_timeout(5000)

        btn = page.get_by_role("button", name="GO GET IT").first
        box = btn.bounding_box()
        assert box

        strategies = []

        def plain():
            btn.click()

        def force():
            btn.click(force=True)

        def mouse():
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

        def dom():
            btn.evaluate("el => el.click()")

        def enter():
            btn.focus()
            page.keyboard.press("Enter")

        def dbl():
            btn.dblclick()

        for label, fn in [
            ("plain", plain),
            ("force", force),
            ("mouse", mouse),
            ("dom", dom),
            ("enter", enter),
            ("dblclick", dbl),
        ]:
            if try_click(label, page, fn):
                break
            page.wait_for_timeout(2000)

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
