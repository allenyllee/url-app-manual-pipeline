#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge capture manifest into manual spec figure blocks")
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--images-root", type=Path, default=None)
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest.exists() else {"scenes": []}

    by_figure = {s.get("figure_id"): s for s in manifest.get("scenes", []) if s.get("figure_id")}
    removed: list[str] = []

    for section in spec.get("sections", []):
        new_blocks = []
        for block in section.get("blocks", []):
            if block.get("type") != "figure":
                new_blocks.append(block)
                continue

            fig_id = block.get("figure_id")
            scene = by_figure.get(fig_id)
            if not scene:
                removed.append(fig_id or "unknown")
                continue

            image_rel = scene.get("image_rel") or block.get("image_rel", "")
            if args.images_root and image_rel:
                image_path = (args.images_root / Path(image_rel).name).resolve()
                if not image_path.exists():
                    removed.append(fig_id or "unknown")
                    continue

            block["image_rel"] = image_rel
            block["caption"] = scene.get("caption", block.get("caption", ""))
            new_blocks.append(block)

        section["blocks"] = new_blocks

    trace = spec.setdefault("trace", {})
    fallbacks = trace.setdefault("fallbacks", [])
    for scene in manifest.get("scenes", []):
        if scene.get("degraded") and scene.get("figure_id"):
            if scene["figure_id"] not in fallbacks:
                fallbacks.append(scene["figure_id"])
    trace["removed_figures"] = removed

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"out spec: {args.out}")
    print(f"removed figures: {len(removed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
