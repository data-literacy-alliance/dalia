#!/bin/bash
# convert-privacy-policy.sh
# Converts DOCX privacy policy files to Markdown using the pandoc/core container.
# Usage: make convert-privacy-policy (or ./scripts/convert-privacy-policy.sh)
# Output: content/privacy-policy/de.md (and en.md if a Privacy*.docx is present)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"        # dalia20/
REPO_ROOT="$(dirname "$PROJECT_DIR")"          # git root (dalia_2.0/)
DOCS_DIR="$REPO_ROOT/docs/privacy_policy"
OUT_DIR="$PROJECT_DIR/content/privacy-policy"

mkdir -p "$OUT_DIR"

convert_docx() {
    local input_file="$1"
    local output_name="$2"
    local filename
    filename="$(basename "$input_file")"

    echo "Converting: $filename → $output_name"
    podman run --rm \
        -v "$DOCS_DIR:/input:z" \
        -v "$OUT_DIR:/output:z" \
        docker.io/pandoc/core \
        "/input/$filename" \
        -f docx -t markdown \
        --wrap=none \
        -o "/output/$output_name"
    echo "Written: $OUT_DIR/$output_name"
}

# German — latest Datenschutz*.docx
DE_DOCX=$(ls "$DOCS_DIR"/Datenschutz*.docx 2>/dev/null | sort | tail -1 || true)
if [ -n "$DE_DOCX" ]; then
    convert_docx "$DE_DOCX" "de.md"
else
    echo "WARNING: No Datenschutz*.docx found in $DOCS_DIR"
fi

# English — latest Privacy*.docx or privacy*.docx
EN_DOCX=$(ls "$DOCS_DIR"/[Pp]rivacy*.docx 2>/dev/null | sort | tail -1 || true)
if [ -n "$EN_DOCX" ]; then
    convert_docx "$EN_DOCX" "en.md"
else
    echo "INFO: No English DOCX found — skipping en.md"
fi

echo ""
echo "Done. Files in $OUT_DIR:"
ls -la "$OUT_DIR/"
