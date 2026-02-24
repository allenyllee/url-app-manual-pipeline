# Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file.

## Available skills
- `url-app-manual-pipeline`: Generate an end-to-end web app user manual from a URL with screenshots, LaTeX typesetting, and DOCX sync without direct tex-to-docx conversion.  
  File: `skills/url-app-manual-pipeline/SKILL.md`

## How to use skills
- If user names the skill (or request clearly matches it), use this local skill file.
- Prefer local repo skill files over global `~/.codex/skills` copies when both exist.
- When any local skill file under `skills/url-app-manual-pipeline/` is modified, always prompt:
  "Do you want me to sync these updates to `~/.codex/skills/url-app-manual-pipeline`?"
