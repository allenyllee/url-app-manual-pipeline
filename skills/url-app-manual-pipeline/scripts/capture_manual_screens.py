#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright


def parse_args():
    p = argparse.ArgumentParser(description="Capture manual screenshots from a web app URL.")
    p.add_argument("--url", default="https://example.com/", help="Base URL to capture")
    p.add_argument("--outdir", default="images", help="Output image directory")
    p.add_argument("--search-query", default="test", help="Query text for search flow")
    return p.parse_args()


def dismiss_overlays(page) -> None:
    # Try common consent dialogs across locales.
    candidates = [
        "button:has-text('Accept all')",
        "button:has-text('I agree')",
        "button:has-text('同意')",
        "button:has-text('全部接受')",
        "button[aria-label='Accept all']",
    ]
    for sel in candidates:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=1000):
                loc.click(timeout=1500)
                page.wait_for_timeout(1000)
                return
        except Exception:
            continue


def goto_home(page, base_url: str) -> None:
    page.goto(base_url, wait_until="domcontentloaded", timeout=90000)
    dismiss_overlays(page)
    page.wait_for_timeout(2500)


def screenshot_safe(target: Any, path: Path, full_page: bool = False, fallback_page: Any | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if full_page:
            target.screenshot(path=str(path), full_page=True)
        else:
            target.screenshot(path=str(path))
    except Exception:
        if fallback_page is None:
            raise
        if full_page:
            fallback_page.screenshot(path=str(path), full_page=True)
        else:
            fallback_page.screenshot(path=str(path))


def first_visible_locator(page, selectors: list[str], max_each: int = 10):
    for sel in selectors:
        loc = page.locator(sel)
        try:
            count = min(loc.count(), max_each)
        except Exception:
            continue
        for i in range(count):
            candidate = loc.nth(i)
            try:
                if candidate.is_visible(timeout=800):
                    return candidate
            except Exception:
                continue
    return None


def first_detail_url(page, base_url: str) -> str | None:
    base = urlparse(base_url)
    anchors = page.locator("main a[href], article a[href], a[href]")
    count = min(anchors.count(), 30)
    for i in range(count):
        try:
            href = anchors.nth(i).get_attribute("href")
            if not href:
                continue
            href = href.strip()
            if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                continue
            dest = urljoin(base_url, href)
            parsed = urlparse(dest)
            if parsed.netloc and parsed.netloc != base.netloc:
                continue
            if parsed.path in ("", "/"):
                continue
            return dest
        except Exception:
            continue
    return None


def main() -> int:
    args = parse_args()
    base_url = args.url
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1024})

        # 1) Home overview
        goto_home(page, base_url)
        screenshot_safe(page, outdir / "home-overview.png", full_page=True)

        # 2) Top nav/banner
        top_nav = first_visible_locator(page, ["header", "[role='banner']", "nav"])
        if top_nav is not None:
            screenshot_safe(top_nav, outdir / "top-nav.png", fallback_page=page)
        else:
            screenshot_safe(page, outdir / "top-nav.png")

        # 3) Left nav/side panel
        side_nav = first_visible_locator(
            page,
            [
                "aside nav",
                "aside",
                "ytd-mini-guide-renderer",
                "ytd-guide-renderer",
                "nav[aria-label*='navigation' i]",
                "[role='navigation']",
            ],
        )
        if side_nav is not None:
            screenshot_safe(side_nav, outdir / "left-nav.png", fallback_page=page)
        else:
            screenshot_safe(page, outdir / "left-nav.png")

        # 4) Representative content card
        card = first_visible_locator(
            page,
            [
                "ytd-rich-item-renderer",
                "ytd-video-renderer",
                "a#thumbnail",
                "article",
                "[data-testid*='card' i]",
                "[class*='card' i]",
                "main a[href]",
            ],
        )
        if card is None:
            screenshot_safe(page, outdir / "video-card.png")
        else:
            try:
                card.scroll_into_view_if_needed(timeout=5000)
                page.wait_for_timeout(500)
            except Exception:
                pass
            screenshot_safe(card, outdir / "video-card.png", fallback_page=page)

        # 5) Flow A step 1 - typed query in search input
        search_input = first_visible_locator(
            page,
            [
                "input#search",
                "input[name='search_query']",
                "input[type='search']",
                "input[name*='search' i]",
                "input[placeholder*='search' i]",
                "form[role='search'] input",
                "input[type='text']",
            ],
        )
        try:
            if search_input is None:
                raise RuntimeError("search input not found")
            search_input.click(timeout=3000)
            search_input.fill(args.search_query)
            page.wait_for_timeout(500)
            screenshot_safe(page, outdir / "flow-search-step1.png")

            # 6) Flow A step 2 - search results page
            page.keyboard.press("Enter")
            page.wait_for_load_state("domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            screenshot_safe(page, outdir / "flow-search-step2.png")
        except Exception:
            screenshot_safe(page, outdir / "flow-search-step1.png")
            screenshot_safe(page, outdir / "flow-search-step2.png")

        # 7) Flow B step 1 - choose an item from home
        goto_home(page, base_url)
        first_watch = first_detail_url(page, base_url)
        screenshot_safe(page, outdir / "flow-open-video-step1.png")

        # 8) Flow B step 2 - detail page loaded
        if first_watch:
            page.goto(first_watch, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3000)
            screenshot_safe(page, outdir / "flow-open-video-step2.png")
        else:
            # fallback: keep last page so output file always exists
            screenshot_safe(page, outdir / "flow-open-video-step2.png")

        browser.close()

    print("saved screenshots:")
    for name in [
        "home-overview.png",
        "top-nav.png",
        "left-nav.png",
        "video-card.png",
        "flow-search-step1.png",
        "flow-search-step2.png",
        "flow-open-video-step1.png",
        "flow-open-video-step2.png",
    ]:
        print(f"- images/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
