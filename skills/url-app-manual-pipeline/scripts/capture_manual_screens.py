#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright


def parse_args():
    p = argparse.ArgumentParser(description="Capture manual screenshots from a web app URL.")
    p.add_argument("--url", default="https://example.com/", help="Base URL to capture")
    p.add_argument("--outdir", default="images", help="Output image directory")
    p.add_argument("--search-query", default="test", help="Query text for search flow")
    p.add_argument("--mode", choices=["static", "dynamic"], default="static")
    p.add_argument("--manifest-out", default=None, help="Output capture manifest path")
    p.add_argument("--max-shots", type=int, default=12)
    p.add_argument("--min-scenes", type=int, default=1)
    return p.parse_args()


def dismiss_overlays(page) -> None:
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
    page.wait_for_timeout(2000)


def screenshot_safe(target: Any, path: Path, full_page: bool = False, fallback_page: Any | None = None) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if full_page:
            target.screenshot(path=str(path), full_page=True)
        else:
            target.screenshot(path=str(path))
        return False
    except Exception:
        if fallback_page is None:
            raise
        if full_page:
            fallback_page.screenshot(path=str(path), full_page=True)
        else:
            fallback_page.screenshot(path=str(path))
        return True


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
    count = min(anchors.count(), 40)
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


def manifest_path(args, outdir: Path) -> Path:
    if args.manifest_out:
        return Path(args.manifest_out)
    return outdir.parent / "capture_manifest.json"


def capture_static(page, base_url: str, outdir: Path, search_query: str) -> tuple[list[str], dict]:
    goto_home(page, base_url)
    screenshot_safe(page, outdir / "home-overview.png", full_page=True)

    top_nav = first_visible_locator(page, ["header", "[role='banner']", "nav"])
    if top_nav is not None:
        screenshot_safe(top_nav, outdir / "top-nav.png", fallback_page=page)
    else:
        screenshot_safe(page, outdir / "top-nav.png")

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

    has_search = search_input is not None
    try:
        if search_input is None:
            raise RuntimeError("search input not found")
        search_input.click(timeout=3000)
        search_input.fill(search_query)
        page.wait_for_timeout(500)
        screenshot_safe(page, outdir / "flow-search-step1.png")
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        screenshot_safe(page, outdir / "flow-search-step2.png")
    except Exception:
        screenshot_safe(page, outdir / "flow-search-step1.png")
        screenshot_safe(page, outdir / "flow-search-step2.png")

    goto_home(page, base_url)
    first_watch = first_detail_url(page, base_url)
    screenshot_safe(page, outdir / "flow-open-video-step1.png")

    if first_watch:
        page.goto(first_watch, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(3000)
        screenshot_safe(page, outdir / "flow-open-video-step2.png")
    else:
        screenshot_safe(page, outdir / "flow-open-video-step2.png")

    saved = [
        "home-overview.png",
        "top-nav.png",
        "left-nav.png",
        "video-card.png",
        "flow-search-step1.png",
        "flow-search-step2.png",
        "flow-open-video-step1.png",
        "flow-open-video-step2.png",
    ]

    scenes = [
        {"figure_id": "home_overview", "scene_type": "home_overview", "file": "home-overview.png", "image_rel": "images/home-overview.png", "source_url": base_url, "confidence": 0.95, "degraded": False},
        {"figure_id": "primary_nav", "scene_type": "primary_nav", "file": "top-nav.png", "image_rel": "images/top-nav.png", "source_url": base_url, "confidence": 0.85, "degraded": False},
        {"figure_id": "side_navigation", "scene_type": "side_navigation", "file": "left-nav.png", "image_rel": "images/left-nav.png", "source_url": base_url, "confidence": 0.8, "degraded": False},
        {"figure_id": "primary_card", "scene_type": "primary_content", "file": "video-card.png", "image_rel": "images/video-card.png", "source_url": base_url, "confidence": 0.8, "degraded": False},
        {"figure_id": "flow_search_entry", "scene_type": "task_entry", "file": "flow-search-step1.png", "image_rel": "images/flow-search-step1.png", "source_url": base_url, "confidence": 0.75, "degraded": not has_search},
        {"figure_id": "flow_search_result", "scene_type": "task_result", "file": "flow-search-step2.png", "image_rel": "images/flow-search-step2.png", "source_url": base_url, "confidence": 0.75, "degraded": not has_search},
        {"figure_id": "flow_open_entry", "scene_type": "task_entry", "file": "flow-open-video-step1.png", "image_rel": "images/flow-open-video-step1.png", "source_url": base_url, "confidence": 0.8, "degraded": False},
        {"figure_id": "flow_open_result", "scene_type": "task_result", "file": "flow-open-video-step2.png", "image_rel": "images/flow-open-video-step2.png", "source_url": first_watch or base_url, "confidence": 0.8, "degraded": first_watch is None},
    ]

    capabilities = {
        "has_search_input": has_search,
        "has_top_nav": top_nav is not None,
        "has_side_nav": side_nav is not None,
        "has_card": card is not None,
    }

    return saved, {"scenes": scenes, "capabilities": capabilities}


def capture_dynamic(page, base_url: str, outdir: Path, search_query: str, max_shots: int, min_scenes: int) -> dict:
    scene_rows: list[dict] = []

    def add_scene(figure_id: str, scene_type: str, path_name: str, degraded: bool, confidence: float, source_url: str, caption: str) -> None:
        scene_rows.append(
            {
                "figure_id": figure_id,
                "scene_type": scene_type,
                "file": path_name,
                "image_rel": f"images/{path_name}",
                "source_url": source_url,
                "confidence": confidence,
                "degraded": degraded,
                "caption": caption,
            }
        )

    goto_home(page, base_url)

    # 1) Required minimal scenes
    degraded = screenshot_safe(page, outdir / "home-overview.png", full_page=True)
    add_scene("home_overview", "home_overview", "home-overview.png", degraded, 0.95 if not degraded else 0.5, base_url, "Home overview")

    top_nav = first_visible_locator(page, ["header", "[role='banner']", "nav"])
    if top_nav is not None:
        degraded = screenshot_safe(top_nav, outdir / "primary-nav.png", fallback_page=page)
    else:
        degraded = screenshot_safe(page, outdir / "primary-nav.png")
        degraded = True
    add_scene("primary_nav", "primary_nav", "primary-nav.png", degraded, 0.85 if not degraded else 0.45, base_url, "Primary navigation")

    content = first_visible_locator(page, ["main", "article", "[role='main']", "[class*='content' i]"])
    if content is not None:
        degraded = screenshot_safe(content, outdir / "primary-content.png", fallback_page=page)
    else:
        degraded = screenshot_safe(page, outdir / "primary-content.png")
        degraded = True
    add_scene("primary_content", "primary_content", "primary-content.png", degraded, 0.82 if not degraded else 0.4, base_url, "Primary content area")

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

    if search_input is not None:
        try:
            search_input.click(timeout=3000)
            search_input.fill(search_query)
            page.wait_for_timeout(500)
            degraded = screenshot_safe(page, outdir / "task-entry.png")
            add_scene("task_entry", "task_entry", "task-entry.png", degraded, 0.8 if not degraded else 0.45, base_url, "Task entry")
            page.keyboard.press("Enter")
            page.wait_for_load_state("domcontentloaded", timeout=60000)
            page.wait_for_timeout(2200)
            degraded = screenshot_safe(page, outdir / "task-result.png")
            add_scene("task_result", "task_result", "task-result.png", degraded, 0.8 if not degraded else 0.45, page.url, "Task result")
        except Exception:
            degraded = screenshot_safe(page, outdir / "task-entry.png")
            add_scene("task_entry", "task_entry", "task-entry.png", True or degraded, 0.35, base_url, "Task entry (fallback)")
            degraded = screenshot_safe(page, outdir / "task-result.png")
            add_scene("task_result", "task_result", "task-result.png", True or degraded, 0.35, page.url, "Task result (fallback)")
    else:
        degraded = screenshot_safe(page, outdir / "task-entry.png")
        add_scene("task_entry", "task_entry", "task-entry.png", True or degraded, 0.3, base_url, "Task entry (fallback)")
        degraded = screenshot_safe(page, outdir / "task-result.png")
        add_scene("task_result", "task_result", "task-result.png", True or degraded, 0.3, page.url, "Task result (fallback)")

    # 2) Optional scenes up to max_shots
    goto_home(page, base_url)
    optional_specs = []

    side_nav = first_visible_locator(page, ["aside nav", "aside", "[role='navigation']"])
    if side_nav is not None:
        optional_specs.append(("side_navigation", "side_navigation", "side-navigation.png", side_nav, "Side navigation"))

    card = first_visible_locator(page, ["article", "[data-testid*='card' i]", "[class*='card' i]", "main a[href]"])
    if card is not None:
        optional_specs.append(("content_card", "content_card", "content-card.png", card, "Representative content card"))

    detail = first_detail_url(page, base_url)
    if detail:
        try:
            page.goto(detail, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2200)
            optional_specs.append(("detail_page", "detail_page", "detail-page.png", page, "Detail page"))
        except Exception:
            pass

    for figure_id, scene_type, file_name, target, caption in optional_specs:
        if len(scene_rows) >= max_shots:
            break
        degraded = screenshot_safe(target, outdir / file_name, fallback_page=page)
        add_scene(
            figure_id,
            scene_type,
            file_name,
            degraded,
            0.72 if not degraded else 0.4,
            page.url,
            caption,
        )

    # Ensure min scenes requirement.
    if len(scene_rows) < max(1, min_scenes):
        degraded = screenshot_safe(page, outdir / "fallback-scene.png")
        add_scene("fallback_scene", "fallback", "fallback-scene.png", True or degraded, 0.2, page.url, "Fallback scene")

    capabilities = {
        "has_search_input": search_input is not None,
        "has_top_nav": top_nav is not None,
        "has_side_nav": side_nav is not None,
        "has_card": card is not None,
    }

    return {"scenes": scene_rows, "capabilities": capabilities}


def main() -> int:
    args = parse_args()
    base_url = args.url
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest_out = manifest_path(args, outdir)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1024})

        if args.mode == "static":
            saved, m = capture_static(page, base_url, outdir, args.search_query)
            manifest = {
                "url": base_url,
                "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "mode": "static",
                "scenes": m["scenes"],
                "capabilities": m["capabilities"],
            }
            print("saved screenshots:")
            for name in saved:
                print(f"- images/{name}")
        else:
            m = capture_dynamic(page, base_url, outdir, args.search_query, args.max_shots, args.min_scenes)
            manifest = {
                "url": base_url,
                "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "mode": "dynamic",
                "scenes": m["scenes"],
                "capabilities": m["capabilities"],
            }
            print("saved screenshots:")
            for row in m["scenes"]:
                print(f"- images/{row['file']}")

        browser.close()

    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
