# DOCX Image Sync

Use this when you edit screenshots directly in Word and want to sync them back to `images/` for LaTeX.

## 1) Add tags in Word

For each screenshot, add a paragraph with a unique tag near that image:

- `IMG:home-overview`
- `IMG:top-nav`
- `IMG:left-nav`
- `IMG:video-card`
- `IMG:flow-search-step1`
- `IMG:flow-search-step2`
- `IMG:flow-open-video-step1`
- `IMG:flow-open-video-step2`

Rule: each `IMG:<token>` should appear after the corresponding image in the document.

## 2) Run sync

```bash
python3 scripts/sync_docx_images.py manual_styled_v4.docx --outdir images
```

Dry run:

```bash
python3 scripts/sync_docx_images.py manual_styled_v4.docx --outdir images --dry-run
```

## 3) Rebuild PDF

```bash
latexmk -pdf main.tex
```
