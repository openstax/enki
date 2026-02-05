#!/bin/bash

set -euo pipefail

DIR="${1:-.}"

echo "Searching for docx files for missing alt text in: $DIR"
echo ""
echo "=== Files with missing alt text ==="
for f in "$DIR"/*.docx; do
    [ -f "$f" ] || continue
    missing_alt_text=()
    found=false
    while read -r id; do
        missing_alt_text+=("$id")
        found=true
    done < <(unzip -p "$f" word/document.xml | xmlstarlet sel -t -m '//*[local-name()="docPr" and not(@descr)]' -v '@id' -n)
    if $found; then
        echo ""
        echo "--- $(basename "$f") ---"
        for id in "${missing_alt_text[@]}"; do
            echo "id: $id"
        done
    fi
done
