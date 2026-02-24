# DOCX Content Sync (No Layout Break)

This workflow syncs edited DOCX content into `main.tex` **without** converting DOCX to TeX and **without** replacing LaTeX layout structure.

## What it updates

- `\section{Scope}` item list
- `\section{Prerequisites}` item list
- `\section{Maintenance Notes}` item list
- Rows in these tables:
  - `\subsection{Top Navigation}`
  - `\subsection{Left Navigation (Common Signed-out Items)}`
  - `\subsection{Home Feed Video Card}`
- `\screenshotbox` captions (by order)

## What it does NOT change

- Document class/packages
- Geometry and styles
- `longtable` structure and commands
- Figure file paths (`images/*.png`)
- LaTeX command layout

## Usage

Dry run:

```bash
python3 scripts/sync_docx_to_latex.py manual_styled_v4.docx --tex main.tex --dry-run
```

Apply:

```bash
python3 scripts/sync_docx_to_latex.py manual_styled_v4.docx --tex main.tex
```

Rebuild:

```bash
latexmk -pdf main.tex
```

## Reverse sync (LaTeX -> existing DOCX template)

This does not convert whole file. It patches content blocks in the existing DOCX:

```bash
python3 scripts/sync_latex_to_docx.py --tex main.tex --docx manual_styled_v3.docx --dry-run
python3 scripts/sync_latex_to_docx.py --tex main.tex --docx manual_styled_v3.docx
```

## Notes

- Keep section/subsection names recognizable in DOCX (e.g., `Top Navigation`), or that block may be skipped.
- If a block cannot be matched, the script leaves the original LaTeX block unchanged.

## Dynamic PoC sync (ID-based)

When working with `manual_spec.json` + dynamic templates, sync by block IDs instead of fixed English headings:

```bash
python3 scripts/sync_latex_to_docx.py \
  --tex main.dynamic.tex \
  --docx manual_styled_dynamic.docx \
  --spec manual_spec.json \
  --out manual.dynamic.docx
```

Rules:
- Markdown carries `MANUAL_BLOCK:<block_id>` token paragraphs.
- Sync script replaces those blocks by ID (`paragraph|bullet_list|numbered_list|table`).
- Figure blocks are left for image sync phase.
