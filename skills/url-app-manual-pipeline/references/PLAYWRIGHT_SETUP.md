# Playwright Screenshot Setup

## Installed

- Python virtual env: `skills/url-app-manual-pipeline/.runtime/.venv/`
- Package: `playwright`
- Browser: Chromium (Playwright managed)

## Bootstrap + Test command

```bash
skills/url-app-manual-pipeline/scripts/run_manual_pipeline.sh "https://www.youtube.com/"
```

Output example:

- `manual_jobs/<timestamp>/source/images/home-overview.png`
- `manual_jobs/<timestamp>/output/manual.pdf`
- `manual_jobs/<timestamp>/output/manual.docx`

## Notes

- In this environment, browser launch needs elevated execution.
- The script is the base; add more page actions/screenshots in:
  - `skills/url-app-manual-pipeline/scripts/capture_manual_screens.py`
