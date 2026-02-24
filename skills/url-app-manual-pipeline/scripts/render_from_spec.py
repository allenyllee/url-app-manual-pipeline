#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render dynamic tex/md from manual spec")
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--tex-template", type=Path, required=True)
    p.add_argument("--md-template", type=Path, required=True)
    p.add_argument("--out-tex", type=Path, required=True)
    p.add_argument("--out-md", type=Path, required=True)
    return p.parse_args()


def tex_escape(text: str) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = text
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def clean_md(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def render_tex_body(spec: dict) -> str:
    lines: list[str] = []
    sections = sorted(spec.get("sections", []), key=lambda x: x.get("order", 9999))
    for section in sections:
        level = int(section.get("level", 1))
        title = tex_escape(section.get("title", "Untitled"))
        if level <= 1:
            lines.append(f"\\section{{{title}}}")
        else:
            lines.append(f"\\subsection{{{title}}}")

        for block in section.get("blocks", []):
            block_id = block.get("block_id", "unknown")
            btype = block.get("type")
            lines.append(f"% MANUAL_BLOCK:{block_id}")

            if btype == "paragraph":
                lines.append(tex_escape(block.get("text", "")))
                lines.append("")
            elif btype == "bullet_list":
                lines.append("\\begin{itemize}")
                for item in block.get("items", []):
                    lines.append(f"  \\item {tex_escape(item)}")
                lines.append("\\end{itemize}")
            elif btype == "numbered_list":
                lines.append("\\begin{enumerate}")
                for item in block.get("items", []):
                    lines.append(f"  \\item {tex_escape(item)}")
                lines.append("\\end{enumerate}")
            elif btype == "table":
                cols = block.get("columns", [])
                rows = block.get("rows", [])
                if not cols:
                    cols = ["Column 1", "Column 2", "Column 3"]
                n = max(1, len(cols))
                width = 0.92 / n
                layout = " ".join([f"p{{{width:.2f}\\linewidth}}" for _ in cols])
                lines.append(f"\\begin{{longtable}}{{{layout}}}")
                lines.append("\\toprule")
                lines.append(" & ".join(tex_escape(c) for c in cols) + r" \\")
                lines.append("\\midrule")
                lines.append("\\endhead")
                for row in rows:
                    padded = list(row) + [""] * (len(cols) - len(row))
                    lines.append(" & ".join(tex_escape(c) for c in padded[: len(cols)]) + r" \\")
                lines.append("\\bottomrule")
                lines.append("\\end{longtable}")
            elif btype == "figure":
                fig_id = block.get("figure_id", block_id)
                lines.append(f"% MANUAL_FIG:{fig_id}")
                image_rel = block.get("image_rel", "")
                caption = tex_escape(block.get("caption", ""))
                lines.append(
                    "\\screenshotbox{"
                    + tex_escape(image_rel)
                    + "}{"
                    + caption
                    + "}{Captured from live UI}"
                )
            else:
                lines.append("% unsupported block type")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_md_body(spec: dict) -> str:
    lines: list[str] = []
    sections = sorted(spec.get("sections", []), key=lambda x: x.get("order", 9999))
    for section in sections:
        level = int(section.get("level", 1))
        title = clean_md(section.get("title", "Untitled"))
        lines.append("#" * max(1, min(6, level)) + f" {title}")
        lines.append("")
        for block in section.get("blocks", []):
            block_id = block.get("block_id", "unknown")
            btype = block.get("type")
            lines.append(f"MANUAL_BLOCK:{block_id}")
            lines.append("")

            if btype == "paragraph":
                lines.append(clean_md(block.get("text", "")))
            elif btype == "bullet_list":
                for item in block.get("items", []):
                    lines.append(f"- {clean_md(item)}")
            elif btype == "numbered_list":
                for i, item in enumerate(block.get("items", []), start=1):
                    lines.append(f"{i}. {clean_md(item)}")
            elif btype == "table":
                cols = block.get("columns", [])
                rows = block.get("rows", [])
                if not cols:
                    cols = ["Column 1", "Column 2", "Column 3"]
                lines.append("| " + " | ".join(clean_md(c) for c in cols) + " |")
                lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
                for row in rows:
                    padded = list(row) + [""] * (len(cols) - len(row))
                    lines.append("| " + " | ".join(clean_md(c) for c in padded[: len(cols)]) + " |")
            elif btype == "figure":
                fig_id = block.get("figure_id", block_id)
                lines.append(f"MANUAL_FIG:{fig_id}")
                lines.append("")
                caption = clean_md(block.get("caption", ""))
                image_rel = block.get("image_rel", "")
                lines.append(f"![{caption}]({image_rel})")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    tex_tpl = args.tex_template.read_text(encoding="utf-8")
    md_tpl = args.md_template.read_text(encoding="utf-8")

    tex_body = render_tex_body(spec)
    md_body = render_md_body(spec)

    meta = spec.get("meta", {})
    ctx = {
        "__APP_TARGET__": str(meta.get("app_target", "Dynamic Manual")),
        "__MANUAL_DATE__": str(meta.get("generated_at", ""))[:10],
        "__TEST_URL__": str(meta.get("url", "")),
        "__HOST__": str(meta.get("host", "")),
        "__TEX_BODY__": tex_body,
        "__MD_BODY__": md_body,
    }

    for k, v in ctx.items():
        tex_tpl = tex_tpl.replace(k, v)
        md_tpl = md_tpl.replace(k, v)

    args.out_tex.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_tex.write_text(tex_tpl, encoding="utf-8")
    args.out_md.write_text(md_tpl, encoding="utf-8")

    print(f"spec: {args.spec}")
    print(f"out tex: {args.out_tex}")
    print(f"out md: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
