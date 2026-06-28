"""Dump header label + value leaf nodes (with coords) for several matters."""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from regulatory_agent.scraper.metadata import _leaf_text_nodes
from regulatory_agent.scraper.navigate import go_to_matter

MATTERS = ["M12205", "M12383"]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for matter in MATTERS:
            page = browser.new_context(accept_downloads=True).new_page()
            page.set_default_timeout(120000)
            go_to_matter(page, matter)
            page.wait_for_timeout(1500)
            nodes = [n for n in _leaf_text_nodes(page) if 110 <= n["y"] <= 330]
            nodes.sort(key=lambda n: (n["x"], n["y"]))
            print(f"\n========== {matter} header nodes (sorted by x) ==========")
            for n in nodes:
                band = "LABEL" if n["y"] <= 165 else "value"
                print(f"  x={n['x']:>4} y={n['y']:>4} [{band}] {n['t']!r}")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
