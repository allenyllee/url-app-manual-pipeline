#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render manual templates from URL context")
    p.add_argument("--url", required=True)
    p.add_argument("--tex-template", type=Path, required=True)
    p.add_argument("--md-template", type=Path, required=True)
    p.add_argument("--out-tex", type=Path, required=True)
    p.add_argument("--out-md", type=Path, required=True)
    p.add_argument("--search-query", default="test")
    return p.parse_args()


def latex_escape(text: str) -> str:
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


def with_scheme(url: str) -> str:
    u = url.strip()
    if "://" not in u:
        return f"https://{u}"
    return u


def main() -> int:
    args = parse_args()
    url = with_scheme(args.url)
    parsed = urlparse(url)
    host = parsed.netloc or "target app"
    host_for_text = host.replace("www.", "")
    app_target = f"{host_for_text} Web App (Desktop)"

    ctx = {
        "__MANUAL_DATE__": date.today().isoformat(),
        "__APP_TARGET__": app_target,
        "__APP_TARGET_LATEX__": latex_escape(app_target),
        "__TEST_URL__": url,
        "__HOST__": host_for_text,
        "__HOST_LATEX__": latex_escape(host_for_text),
        "__SEARCH_QUERY__": args.search_query,
    }

    tex_text = args.tex_template.read_text(encoding="utf-8")
    md_text = args.md_template.read_text(encoding="utf-8")

    for k, v in ctx.items():
        tex_text = tex_text.replace(k, v)
        md_text = md_text.replace(k, v)

    # LaTeX-specific tokens should not leak.
    tex_text = tex_text.replace("__APP_TARGET__", ctx["__APP_TARGET_LATEX__"])
    tex_text = tex_text.replace("__HOST__", ctx["__HOST_LATEX__"])

    args.out_tex.write_text(tex_text, encoding="utf-8")
    args.out_md.write_text(md_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
