---
name: url-app-manual-pipeline
description: >-
  Generate an end-to-end web app user manual from a URL with screenshots,
  LaTeX typesetting, and DOCX sync without direct tex to docx conversion. Use
  when the user wants to start from only a URL, produce PDF and DOCX manuals,
  keep source .tex/.md in a separate version-controlled folder, and keep DOCX
  content aligned to LaTeX while preserving Word layout.
---

# URL App Manual Pipeline

Run this skill when the user asks for a full manual pipeline from URL to `PDF + DOCX` and explicitly wants DOCX synced from LaTeX content (not direct full-file conversion).

## Workflow

1. Ensure prerequisites:
- System commands exist: `python3`, `pandoc`, `latexmk`.
- Skill scripts exist in `skills/url-app-manual-pipeline/scripts/`:
`capture_manual_screens.py`, `sync_latex_to_docx.py`, `sync_latex_images_to_docx.py`.

2. Run the one-shot pipeline script:

```bash
skills/url-app-manual-pipeline/scripts/run_manual_pipeline.sh "<URL>" [job_dir]
```

Default behavior automatically bootstraps Python runtime in
`skills/url-app-manual-pipeline/.runtime/.venv`:
- create venv
- install `playwright` + `python-docx`
- install Playwright Chromium

Optional:
- disable bootstrap: `MANUAL_BOOTSTRAP=0`
- custom venv path: `MANUAL_VENV_DIR=/path/to/.venv`
- auto-install system deps (`pandoc`, `latexmk`, LaTeX packages):
  `MANUAL_AUTO_INSTALL_SYSTEM_DEPS=1`
  (uses `apt-get` / `dnf` / `brew`, requires sudo/admin)
- render from URL templates (default): `MANUAL_USE_LOCAL_SOURCES=0`
- reuse workspace `main.tex` + `manual_word_v3.md`: `MANUAL_USE_LOCAL_SOURCES=1`
- set search-flow keyword: `MANUAL_SEARCH_QUERY="your keyword"`
- auto-delete empty folders in `<job_dir>` on exit (default on): `MANUAL_CLEAN_EMPTY_DIRS=1`
- legacy fallback venv `/mnt/DATA/test/.venv` is blocked by default:
  `MANUAL_ALLOW_LEGACY_TEST_VENV=0`
  (only set `=1` for explicit compatibility override)

3. Expected outputs:
- Source (for version control): `<job_dir>/source/`
  - `main.tex`
  - `manual_word_v3.md`
  - `images/*.png`
  - `main.pdf` (build artifact)
- Final output: `<job_dir>/output/`
  - `manual.pdf`
  - `manual.docx`

## Non-Negotiable Rules

- Do not generate DOCX by converting `main.tex` directly.
- Always use:
  - `sync_latex_to_docx.py` for text/table/heading/list sync
  - `sync_latex_images_to_docx.py` for figure placement/captions
- Keep intermediate source files in the separate `source/` folder.
- Do not claim or auto-select `/mnt/DATA/test/.venv` as a reusable runtime.
- After any local edits to this skill (`skills/url-app-manual-pipeline/**`), prompt user to sync:
  `~/.codex/skills/url-app-manual-pipeline`.

## If User Reports Mismatch

- If chapter numbers are duplicated/missing:
  rerun `sync_latex_to_docx.py` and verify heading numbering in output docx.
- If image order/position is wrong:
  rerun `sync_latex_images_to_docx.py` and verify section anchors.
- If numbered list continuation is wrong (e.g., 5.2 starts at 4):
  rerun `sync_latex_to_docx.py` to regenerate numbering overrides.
