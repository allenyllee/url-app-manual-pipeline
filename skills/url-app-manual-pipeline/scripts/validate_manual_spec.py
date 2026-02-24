#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_TYPES = {"paragraph", "bullet_list", "numbered_list", "table", "figure"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate manual_spec.json schema and consistency")
    p.add_argument("--spec", type=Path, required=True)
    return p.parse_args()


def fail(msg: str) -> None:
    raise SystemExit(f"invalid spec: {msg}")


def main() -> int:
    args = parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    meta = spec.get("meta")
    if not isinstance(meta, dict):
        fail("meta missing")
    for key in ("spec_version", "locale", "url", "host", "generated_at", "generator_mode"):
        if not meta.get(key):
            fail(f"meta.{key} missing")

    sections = spec.get("sections")
    if not isinstance(sections, list) or not sections:
        fail("sections missing or empty")

    block_ids: set[str] = set()
    expected_order = 1
    for section in sorted(sections, key=lambda s: s.get("order", 9999)):
        if section.get("order") != expected_order:
            fail(f"section order not contiguous at {section.get('section_id')}")
        expected_order += 1
        if not section.get("section_id"):
            fail("section_id missing")
        if not section.get("title"):
            fail(f"title missing for section {section.get('section_id')}")
        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            fail(f"blocks missing for section {section.get('section_id')}")
        for block in blocks:
            bid = block.get("block_id")
            btype = block.get("type")
            if not bid:
                fail(f"block_id missing in section {section.get('section_id')}")
            if bid in block_ids:
                fail(f"duplicate block_id: {bid}")
            block_ids.add(bid)
            if btype not in ALLOWED_TYPES:
                fail(f"unsupported block type: {btype}")
            if btype in ("bullet_list", "numbered_list") and not isinstance(block.get("items"), list):
                fail(f"{bid} list block missing items")
            if btype == "table":
                if not isinstance(block.get("columns"), list) or not isinstance(block.get("rows"), list):
                    fail(f"{bid} table block missing columns/rows")
            if btype == "figure":
                for key in ("figure_id", "caption", "image_rel", "anchor_section_id", "order"):
                    if block.get(key) in (None, ""):
                        fail(f"{bid} figure missing {key}")

    trace = spec.get("trace")
    if not isinstance(trace, dict):
        fail("trace missing")
    for key in ("rules_used", "llm_rewrite_applied", "fallbacks"):
        if key not in trace:
            fail(f"trace.{key} missing")

    print(f"valid spec: {args.spec}")
    print(f"sections: {len(sections)}")
    print(f"blocks: {len(block_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
