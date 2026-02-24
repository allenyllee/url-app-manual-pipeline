# URL App Manual Pipeline

Generate end-to-end web app manuals from a URL with screenshots, PDF (LaTeX), and DOCX (Word) outputs.

Primary workflow is **English-first documentation**, with **Traditional Chinese support** (including XeLaTeX path for Chinese PDF).

## What This Repo Does

- Captures UI screenshots from a target website using Playwright
- Builds a manual source package (`.tex`, `.md`, images, spec)
- Produces:
  - `manual.pdf` / `manual.dynamic.pdf`
  - `manual.docx` / `manual.dynamic.docx`
- Keeps DOCX synchronized from LaTeX/spec blocks (not direct full-file TeX->DOCX conversion)

## Main Entry Point

```bash
skills/url-app-manual-pipeline/scripts/run_manual_pipeline.sh "<URL>" [job_dir]
```

## Modes

### 1) Static mode (default)

```bash
MANUAL_TEMPLATE_MODE=static \
skills/url-app-manual-pipeline/scripts/run_manual_pipeline.sh "https://example.com"
```

Outputs:
- `<job_dir>/source/main.tex`
- `<job_dir>/source/manual_word_v3.md`
- `<job_dir>/output/manual.pdf`
- `<job_dir>/output/manual.docx`

### 2) Dynamic mode (spec-driven)

```bash
MANUAL_TEMPLATE_MODE=dynamic \
MANUAL_LOCALE=en \
skills/url-app-manual-pipeline/scripts/run_manual_pipeline.sh "https://example.com"
```

Outputs:
- `<job_dir>/poc_dynamic/source/manual_spec.json`
- `<job_dir>/poc_dynamic/source/main.dynamic.tex`
- `<job_dir>/poc_dynamic/source/manual_word_v3.dynamic.md`
- `<job_dir>/poc_dynamic/output/manual.dynamic.pdf`
- `<job_dir>/poc_dynamic/output/manual.dynamic.docx`

## Important Environment Variables

- `MANUAL_TEMPLATE_MODE=static|dynamic` (default: `static`)
- `MANUAL_LOCALE=en|zh-TW` (default: `en`)
- `MANUAL_LLM_MODE=off|rewrite` (default: `rewrite`)
- `MANUAL_DYNAMIC_MAX_SHOTS=<int>` (default: `12`)
- `MANUAL_DYNAMIC_MIN_SCENES=<int>` (default: `1`)
- `MANUAL_LATEX_ENGINE=auto|pdflatex|xelatex` (default: `auto`)
  - `auto`: dynamic + `zh-TW` uses `xelatex`, otherwise `pdflatex`
- `MANUAL_SEARCH_QUERY="keyword"`

## Prerequisites

- `python3`
- `pandoc`
- `latexmk`
- Playwright runtime (auto-bootstrap supported in skill runtime venv)

For Chinese PDF (`zh-TW`), install XeLaTeX/CJK support if needed:
- `xelatex`
- `xeCJK` related TeX packages
- CJK fonts (for example Noto CJK)

## Key Scripts

- `skills/url-app-manual-pipeline/scripts/run_manual_pipeline.sh`
- `skills/url-app-manual-pipeline/scripts/capture_manual_screens.py`
- `skills/url-app-manual-pipeline/scripts/build_manual_spec.py`
- `skills/url-app-manual-pipeline/scripts/render_from_spec.py`
- `skills/url-app-manual-pipeline/scripts/sync_latex_to_docx.py`
- `skills/url-app-manual-pipeline/scripts/sync_latex_images_to_docx.py`
- `skills/url-app-manual-pipeline/scripts/validate_manual_spec.py`

## Chinese Notes (繁中重點)

- 主要流程：先產生 `manual_spec.json`（dynamic 模式），再同源渲染成 TeX/MD，最後同步到 DOCX。
- 不走整份 TeX 直接轉 DOCX；而是以 block/figure ID 同步內容與圖片位置。
- 若要輸出中文 PDF，建議使用 `MANUAL_LOCALE=zh-TW` 並確保環境有 `xelatex` 與 CJK 字型。

## Quick Examples

English dynamic:

```bash
MANUAL_TEMPLATE_MODE=dynamic MANUAL_LOCALE=en \
skills/url-app-manual-pipeline/scripts/run_manual_pipeline.sh "https://www.youtube.com/"
```

Traditional Chinese dynamic:

```bash
MANUAL_TEMPLATE_MODE=dynamic MANUAL_LOCALE=zh-TW \
skills/url-app-manual-pipeline/scripts/run_manual_pipeline.sh "https://www.youtube.com/"
```

## Related Docs

- `skills/url-app-manual-pipeline/SKILL.md`
- `skills/url-app-manual-pipeline/references/DOCX_CONTENT_SYNC.md`
- `skills/url-app-manual-pipeline/references/DOCX_IMAGE_SYNC.md`
- `skills/url-app-manual-pipeline/references/PLAYWRIGHT_SETUP.md`
