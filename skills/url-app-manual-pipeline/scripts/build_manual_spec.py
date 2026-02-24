#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


LOCALE_TEXT = {
    "en": {
        "title_suffix": "Web App Manual",
        "scope": "Scope",
        "scope_intro": "This manual summarizes key visible user interactions captured from the target web app.",
        "prereq": "Prerequisites",
        "maint": "Maintenance Notes",
        "flows": "Task Flows",
        "build": "Build",
        "controls": "Primary Controls",
        "caption_prefix": "Captured screen",
        "missing_note": "Some scenes were unavailable during capture and were degraded with fallback screenshots.",
    },
    "zh-TW": {
        "title_suffix": "網站操作手冊",
        "scope": "範圍",
        "scope_intro": "本手冊整理目標網站可見的主要操作與流程。",
        "prereq": "前置條件",
        "maint": "維護說明",
        "flows": "操作流程",
        "build": "建置",
        "controls": "主要控制項",
        "caption_prefix": "畫面擷圖",
        "missing_note": "部分場景在擷取時不可用，已以替代截圖降級處理。",
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build dynamic manual spec from URL + capture manifest")
    p.add_argument("--url", required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--locale", default="en", choices=["en", "zh-TW"])
    p.add_argument("--llm-mode", default="rewrite", choices=["off", "rewrite"])
    p.add_argument("--search-query", default="test")
    return p.parse_args()


def with_scheme(url: str) -> str:
    if "://" in url:
        return url
    return f"https://{url}"


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"scenes": [], "capabilities": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def make_block(block_id: str, block_type: str, **kwargs) -> dict:
    block = {"block_id": block_id, "type": block_type}
    block.update(kwargs)
    return block


def apply_rewrite(spec: dict, locale: str) -> tuple[dict, bool]:
    if locale == "zh-TW":
        suffix = "（系統自動整理）"
    else:
        suffix = " (auto-refined)"

    for section in spec.get("sections", []):
        if section.get("level") == 1 and not section["title"].endswith(suffix):
            section["title"] = f"{section['title']}{suffix}"
        for block in section.get("blocks", []):
            if block.get("type") == "paragraph":
                text = block.get("text", "")
                if text and not text.endswith(".") and locale == "en":
                    block["text"] = text + "."
    return spec, True


def unique_ids(sections: list[dict]) -> None:
    seen = set()
    for section in sections:
        for block in section.get("blocks", []):
            bid = block["block_id"]
            if bid in seen:
                raise ValueError(f"Duplicate block_id: {bid}")
            seen.add(bid)


def main() -> int:
    args = parse_args()
    url = with_scheme(args.url)
    parsed = urlparse(url)
    host = (parsed.netloc or "target app").replace("www.", "")
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    text = LOCALE_TEXT[args.locale]

    manifest = load_manifest(args.manifest)
    scenes = manifest.get("scenes", [])
    caps = manifest.get("capabilities", {})

    # Intentionally non-deterministic ordering choices for PoC dynamic structure.
    rnd = random.Random(f"{host}:{now}")

    title = f"{host} {text['title_suffix']}"

    scope_blocks = [
        make_block("scope_intro", "paragraph", text=text["scope_intro"]),
        make_block(
            "scope_points",
            "bullet_list",
            items=[
                f"Target URL: {url}",
                "Desktop viewport focus (recommended >= 1280px)",
                "UI can vary by login state, locale, and experiments",
            ],
        ),
    ]

    prereq_items = [
        "A browser can access the target URL",
        "Network and scripts are allowed for the page to render",
        f"Search keyword for demo flow: {args.search_query}",
    ]
    if args.locale == "zh-TW":
        prereq_items = [
            "瀏覽器可正常連線到目標網址",
            "頁面允許必要腳本與網路請求",
            f"示範搜尋關鍵字：{args.search_query}",
        ]

    prereq_blocks = [make_block("prereq_points", "bullet_list", items=prereq_items)]

    table_rows: list[list[str]] = []
    if caps.get("has_top_nav"):
        table_rows.append(["Top Navigation", "Navigation", "Main route and utility actions"])
    if caps.get("has_side_nav"):
        table_rows.append(["Side Navigation", "Navigation", "Section switching and quick entry"])
    if caps.get("has_search_input"):
        table_rows.append(["Search Input", "Input", "Keyword query entry"])
    if caps.get("has_card"):
        table_rows.append(["Primary Card", "Link/Button", "Open a detail or content page"])
    if not table_rows:
        table_rows.append(["Main Content", "Container", "Primary interactive area"])

    controls_blocks = [
        make_block(
            "controls_table",
            "table",
            table_id="primary_controls",
            columns=["Control", "Type", "Function"],
            rows=table_rows,
        )
    ]

    figures = []
    for i, scene in enumerate(scenes, start=1):
        figure_id = scene.get("figure_id") or f"figure_{i:02d}"
        caption = scene.get("caption") or f"{text['caption_prefix']} {i}: {scene.get('scene_type', 'scene')}"
        figures.append(
            make_block(
                f"fig_block_{i:02d}",
                "figure",
                figure_id=figure_id,
                caption=caption,
                image_rel=scene.get("image_rel", ""),
                anchor_section_id="flows",
                order=i,
            )
        )

    flow_steps = [
        "Open the home page and confirm primary regions are visible",
        f"Enter keyword '{args.search_query}' when search is available",
        "Open one item to verify detail-level navigation",
    ]
    if args.locale == "zh-TW":
        flow_steps = [
            "開啟首頁並確認主要區域可見",
            f"若有搜尋欄，輸入關鍵字「{args.search_query}」",
            "點選一個項目以確認可進入明細頁",
        ]

    flow_blocks = [make_block("flow_steps", "numbered_list", items=flow_steps)] + figures

    maint_items = [
        "Regenerate screenshots after major UI updates",
        "Review table labels for domain-specific terminology",
        "Re-run pipeline when capture manifest indicates degraded scenes",
    ]
    if any(s.get("degraded") for s in scenes):
        maint_items.append(text["missing_note"])

    if args.locale == "zh-TW":
        maint_items = [
            "重大 UI 變更後請重新擷取截圖",
            "表格欄位文字請依領域術語校對",
            "若 manifest 顯示降級場景，請重新執行流程",
        ] + ([text["missing_note"]] if any(s.get("degraded") for s in scenes) else [])

    maint_blocks = [make_block("maint_points", "bullet_list", items=maint_items)]

    build_cmd = "latexmk -pdf main.dynamic.tex"
    build_blocks = [
        make_block("build_text", "paragraph", text="Run this in source directory:" if args.locale == "en" else "請在 source 目錄執行："),
        make_block("build_cmd", "paragraph", text=build_cmd),
    ]

    sections = [
        {"section_id": "scope", "title": text["scope"], "level": 1, "order": 1, "blocks": scope_blocks},
        {"section_id": "prerequisites", "title": text["prereq"], "level": 1, "order": 2, "blocks": prereq_blocks},
        {"section_id": "controls", "title": text["controls"], "level": 1, "order": 3, "blocks": controls_blocks},
        {"section_id": "flows", "title": text["flows"], "level": 1, "order": 4, "blocks": flow_blocks},
        {"section_id": "maintenance", "title": text["maint"], "level": 1, "order": 5, "blocks": maint_blocks},
        {"section_id": "build", "title": text["build"], "level": 1, "order": 6, "blocks": build_blocks},
    ]

    # Dynamic optional section insertion / reorder in PoC.
    if rnd.random() < 0.5:
        extra = {
            "section_id": "quick_notes",
            "title": "Quick Notes" if args.locale == "en" else "快速說明",
            "level": 1,
            "order": 3,
            "blocks": [
                make_block(
                    "quick_notes_paragraph",
                    "paragraph",
                    text=(
                        "This section is dynamically inserted in PoC runs to validate paired-template flexibility"
                        if args.locale == "en"
                        else "此章節由 PoC 動態插入，用於驗證成對模板可變能力"
                    ),
                )
            ],
        }
        sections.insert(2, extra)
        for idx, section in enumerate(sections, start=1):
            section["order"] = idx

    unique_ids(sections)

    spec = {
        "meta": {
            "spec_version": "0.1-poc",
            "locale": args.locale,
            "url": url,
            "host": host,
            "app_target": title,
            "generated_at": now,
            "generator_mode": "dynamic-poc",
        },
        "sections": sections,
        "trace": {
            "rules_used": [
                "manifest_scene_to_figure",
                "capability_to_controls_table",
                "dynamic_optional_section_insertion",
            ],
            "llm_rewrite_applied": False,
            "fallbacks": [s.get("figure_id") for s in scenes if s.get("degraded")],
        },
    }

    if args.llm_mode == "rewrite":
        try:
            spec, rewritten = apply_rewrite(spec, args.locale)
            spec["trace"]["llm_rewrite_applied"] = rewritten
            spec["trace"]["rules_used"].append("llm_rewrite_heuristic")
        except Exception:
            spec["trace"]["rules_used"].append("llm_rewrite_fallback_to_rules")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"spec: {args.out}")
    print(f"sections: {len(spec['sections'])}")
    print(f"figures: {sum(1 for s in spec['sections'] for b in s['blocks'] if b['type'] == 'figure')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
