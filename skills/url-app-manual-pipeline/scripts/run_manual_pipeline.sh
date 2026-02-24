#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <url> [job_dir]"
  exit 1
fi

URL="$1"
REPO_ROOT="$(pwd)"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JOB_DIR="${2:-$REPO_ROOT/manual_jobs/$(date +%Y%m%d-%H%M%S)}"
JOBS_ROOT="$(dirname "$JOB_DIR")"
VENV_DIR="${MANUAL_VENV_DIR:-$SKILL_DIR/.runtime/.venv}"
BOOTSTRAP="${MANUAL_BOOTSTRAP:-1}"
AUTO_INSTALL_SYSTEM_DEPS="${MANUAL_AUTO_INSTALL_SYSTEM_DEPS:-0}"
USE_LOCAL_SOURCES="${MANUAL_USE_LOCAL_SOURCES:-0}"
SEARCH_QUERY="${MANUAL_SEARCH_QUERY:-test}"
CLEAN_EMPTY_DIRS="${MANUAL_CLEAN_EMPTY_DIRS:-1}"
ALLOW_LEGACY_TEST_VENV="${MANUAL_ALLOW_LEGACY_TEST_VENV:-0}"

MANUAL_TEMPLATE_MODE="${MANUAL_TEMPLATE_MODE:-static}"
MANUAL_LOCALE="${MANUAL_LOCALE:-en}"
MANUAL_LLM_MODE="${MANUAL_LLM_MODE:-rewrite}"
MANUAL_DYNAMIC_MAX_SHOTS="${MANUAL_DYNAMIC_MAX_SHOTS:-12}"
MANUAL_DYNAMIC_MIN_SCENES="${MANUAL_DYNAMIC_MIN_SCENES:-1}"
MANUAL_POC_DIR="${MANUAL_POC_DIR:-$JOB_DIR/poc_dynamic}"

SOURCE_DIR="$JOB_DIR/source"
OUTPUT_DIR="$JOB_DIR/output"
IMG_DIR="$SOURCE_DIR/images"
PY_BIN="$VENV_DIR/bin/python"

POC_SOURCE_DIR="$MANUAL_POC_DIR/source"
POC_OUTPUT_DIR="$MANUAL_POC_DIR/output"
POC_IMG_DIR="$POC_SOURCE_DIR/images"

validate_venv_dir() {
  case "$VENV_DIR" in
    /mnt/DATA/test/.venv|/mnt/DATA/test/.venv/*)
      if [[ "$ALLOW_LEGACY_TEST_VENV" != "1" ]]; then
        echo "Refusing legacy venv path: $VENV_DIR" >&2
        echo "Use skill runtime venv (default) or set MANUAL_VENV_DIR explicitly." >&2
        echo "If you really need it, set MANUAL_ALLOW_LEGACY_TEST_VENV=1." >&2
        exit 1
      fi
      ;;
  esac
}

cleanup_current_job_empty_dirs() {
  if [[ "$CLEAN_EMPTY_DIRS" != "1" ]]; then
    return 0
  fi
  if [[ -d "$JOB_DIR" ]]; then
    find "$JOB_DIR" -depth -type d -empty -delete 2>/dev/null || true
  fi
}

cleanup_stale_empty_jobs() {
  if [[ "$CLEAN_EMPTY_DIRS" != "1" ]]; then
    return 0
  fi
  if [[ -d "$JOBS_ROOT" ]]; then
    find "$JOBS_ROOT" -mindepth 1 -maxdepth 1 -type d -empty \
      ! -path "$JOB_DIR" -delete 2>/dev/null || true
  fi
}

trap cleanup_current_job_empty_dirs EXIT

cleanup_stale_empty_jobs
validate_venv_dir

mkdir -p "$SOURCE_DIR" "$OUTPUT_DIR" "$IMG_DIR" "$POC_SOURCE_DIR" "$POC_OUTPUT_DIR" "$POC_IMG_DIR"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

install_system_deps() {
  case "$(uname -s)" in
    Linux)
      if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y pandoc latexmk texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended
        return 0
      fi
      if command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y pandoc texlive-latex texlive-collection-latexrecommended texlive-collection-fontsrecommended texlive-collection-latexextra
        return 0
      fi
      ;;
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        brew install pandoc basictex
        return 0
      fi
      ;;
  esac
  return 1
}

require_or_install_system_cmds() {
  local missing=()
  local c
  for c in "$@"; do
    if ! command -v "$c" >/dev/null 2>&1; then
      missing+=("$c")
    fi
  done

  if [[ ${#missing[@]} -eq 0 ]]; then
    return 0
  fi

  if [[ "$AUTO_INSTALL_SYSTEM_DEPS" != "1" ]]; then
    echo "Missing required commands: ${missing[*]}" >&2
    echo "Set MANUAL_AUTO_INSTALL_SYSTEM_DEPS=1 to try auto-install." >&2
    exit 1
  fi

  echo "Auto-installing system dependencies (requires sudo/admin) ..."
  if ! install_system_deps; then
    echo "Auto-install failed: unsupported OS/package manager." >&2
    echo "Please install manually: pandoc + latexmk (+ LaTeX packages)." >&2
    exit 1
  fi

  for c in "$@"; do
    need_cmd "$c"
  done
}

bootstrap_python_env() {
  need_cmd python3
  if [[ ! -x "$PY_BIN" ]]; then
    mkdir -p "$(dirname "$VENV_DIR")"
    python3 -m venv "$VENV_DIR"
  fi
  if ! "$PY_BIN" -c "import playwright, docx" >/dev/null 2>&1; then
    if ! "$PY_BIN" -m pip install --upgrade pip; then
      echo "Failed to bootstrap Python runtime: cannot upgrade pip." >&2
      echo "Check network/PyPI access, or use MANUAL_BOOTSTRAP=0 with a prebuilt MANUAL_VENV_DIR." >&2
      exit 1
    fi
    if ! "$PY_BIN" -m pip install playwright python-docx; then
      echo "Failed to install Python deps: playwright, python-docx." >&2
      echo "Pipeline aborted. Fix dependency install, then rerun." >&2
      exit 1
    fi
  fi
  if ! "$PY_BIN" -m playwright install chromium; then
    echo "Failed to install Playwright Chromium browser." >&2
    echo "Pipeline aborted. Ensure browser download is reachable, then rerun." >&2
    exit 1
  fi
}

require_python_runtime_deps() {
  if ! "$PY_BIN" -c "import playwright, docx" >/dev/null 2>&1; then
    echo "Missing Python deps in runtime: playwright, python-docx." >&2
    echo "Pipeline aborted. Run with MANUAL_BOOTSTRAP=1, or install deps into $VENV_DIR." >&2
    exit 1
  fi
}

verify_required_screenshots() {
  local required=(
    "home-overview.png"
    "top-nav.png"
    "left-nav.png"
    "video-card.png"
    "flow-search-step1.png"
    "flow-search-step2.png"
    "flow-open-video-step1.png"
    "flow-open-video-step2.png"
  )
  local f
  local missing=()
  for f in "${required[@]}"; do
    if [[ ! -s "$IMG_DIR/$f" ]]; then
      missing+=("$f")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Missing required screenshots: ${missing[*]}" >&2
    echo "Pipeline aborted to avoid LaTeX placeholder images." >&2
    echo "Fix runtime/browser capture issues, then rerun." >&2
    exit 1
  fi
}

require_or_install_system_cmds pandoc latexmk

if [[ "$BOOTSTRAP" == "1" ]]; then
  bootstrap_python_env
else
  if [[ ! -x "$PY_BIN" ]]; then
    echo "Python env not found at: $VENV_DIR" >&2
    echo "Set MANUAL_BOOTSTRAP=1 (default) or create the env manually." >&2
    exit 1
  fi
fi

require_python_runtime_deps

if [[ "$MANUAL_TEMPLATE_MODE" == "dynamic" ]]; then
  MANIFEST_PATH="$POC_SOURCE_DIR/capture_manifest.json"
  RAW_SPEC="$POC_SOURCE_DIR/manual_spec.raw.json"
  SPEC_PATH="$POC_SOURCE_DIR/manual_spec.json"

  "$PY_BIN" "$SKILL_DIR/scripts/capture_manual_screens.py" \
    --url "$URL" \
    --outdir "$POC_IMG_DIR" \
    --search-query "$SEARCH_QUERY" \
    --mode dynamic \
    --manifest-out "$MANIFEST_PATH" \
    --max-shots "$MANUAL_DYNAMIC_MAX_SHOTS" \
    --min-scenes "$MANUAL_DYNAMIC_MIN_SCENES"

  "$PY_BIN" "$SKILL_DIR/scripts/build_manual_spec.py" \
    --url "$URL" \
    --manifest "$MANIFEST_PATH" \
    --out "$RAW_SPEC" \
    --locale "$MANUAL_LOCALE" \
    --llm-mode "$MANUAL_LLM_MODE" \
    --search-query "$SEARCH_QUERY"

  "$PY_BIN" "$SKILL_DIR/scripts/merge_capture_manifest.py" \
    --spec "$RAW_SPEC" \
    --manifest "$MANIFEST_PATH" \
    --images-root "$POC_IMG_DIR" \
    --out "$SPEC_PATH"

  "$PY_BIN" "$SKILL_DIR/scripts/validate_manual_spec.py" \
    --spec "$SPEC_PATH"

  "$PY_BIN" "$SKILL_DIR/scripts/render_from_spec.py" \
    --spec "$SPEC_PATH" \
    --tex-template "$SKILL_DIR/references/main.dynamic.template.tex" \
    --md-template "$SKILL_DIR/references/manual_word.dynamic.template.md" \
    --out-tex "$POC_SOURCE_DIR/main.dynamic.tex" \
    --out-md "$POC_SOURCE_DIR/manual_word_v3.dynamic.md"

  (
    cd "$POC_SOURCE_DIR"
    latexmk -pdf -interaction=nonstopmode main.dynamic.tex
  )
  cp "$POC_SOURCE_DIR/main.dynamic.pdf" "$POC_OUTPUT_DIR/manual.dynamic.pdf"

  pandoc "$POC_SOURCE_DIR/manual_word_v3.dynamic.md" -o "$POC_SOURCE_DIR/manual_styled_dynamic.docx" --toc --number-sections

  "$PY_BIN" "$SKILL_DIR/scripts/sync_latex_to_docx.py" \
    --tex "$POC_SOURCE_DIR/main.dynamic.tex" \
    --docx "$POC_SOURCE_DIR/manual_styled_dynamic.docx" \
    --spec "$SPEC_PATH" \
    --out "$POC_OUTPUT_DIR/manual.dynamic.docx"

  "$PY_BIN" "$SKILL_DIR/scripts/sync_latex_images_to_docx.py" \
    --tex "$POC_SOURCE_DIR/main.dynamic.tex" \
    --docx "$POC_OUTPUT_DIR/manual.dynamic.docx" \
    --spec "$SPEC_PATH"

  echo "Done (dynamic PoC)."
  echo "PoC source: $POC_SOURCE_DIR"
  echo "PoC outputs: $POC_OUTPUT_DIR/manual.dynamic.pdf , $POC_OUTPUT_DIR/manual.dynamic.docx"
  exit 0
fi

# static flow (legacy default)
if [[ "$USE_LOCAL_SOURCES" == "1" && -f "$REPO_ROOT/main.tex" && -f "$REPO_ROOT/manual_word_v3.md" ]]; then
  cp "$REPO_ROOT/main.tex" "$SOURCE_DIR/main.tex"
  cp "$REPO_ROOT/manual_word_v3.md" "$SOURCE_DIR/manual_word_v3.md"
else
  "$PY_BIN" "$SKILL_DIR/scripts/render_manual_templates.py" \
    --url "$URL" \
    --tex-template "$SKILL_DIR/references/main.template.tex" \
    --md-template "$SKILL_DIR/references/manual_word_v3.template.md" \
    --out-tex "$SOURCE_DIR/main.tex" \
    --out-md "$SOURCE_DIR/manual_word_v3.md" \
    --search-query "$SEARCH_QUERY"
fi

"$PY_BIN" "$SKILL_DIR/scripts/capture_manual_screens.py" \
  --url "$URL" \
  --outdir "$IMG_DIR" \
  --search-query "$SEARCH_QUERY" \
  --mode static \
  --manifest-out "$SOURCE_DIR/capture_manifest.json"
verify_required_screenshots

(
  cd "$SOURCE_DIR"
  latexmk -pdf -interaction=nonstopmode main.tex
)
cp "$SOURCE_DIR/main.pdf" "$OUTPUT_DIR/manual.pdf"

pandoc "$SOURCE_DIR/manual_word_v3.md" -o "$SOURCE_DIR/manual_styled_v3.docx" --toc --number-sections

"$PY_BIN" "$SKILL_DIR/scripts/sync_latex_to_docx.py" \
  --tex "$SOURCE_DIR/main.tex" \
  --docx "$SOURCE_DIR/manual_styled_v3.docx" \
  --out "$OUTPUT_DIR/manual.docx"

"$PY_BIN" "$SKILL_DIR/scripts/sync_latex_images_to_docx.py" \
  --tex "$SOURCE_DIR/main.tex" \
  --docx "$OUTPUT_DIR/manual.docx"

echo "Done."
echo "Source files: $SOURCE_DIR"
echo "Outputs: $OUTPUT_DIR/manual.pdf , $OUTPUT_DIR/manual.docx"
