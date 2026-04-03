#!/bin/bash
# =============================================================================
# Wakka — Translation Extraction Script
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MAIN_DIR="$PROJECT_ROOT/main"
I18N_DIR="$MAIN_DIR/ui/i18n"

echo "🔍 Wakka Translation Extractor"
echo "=============================="
echo ""

mkdir -p "$I18N_DIR"

# Find Python files
PY_FILES=$(find "$MAIN_DIR" -name "*.py" -type f | grep -v "__pycache__")

echo "📁 Found $(echo "$PY_FILES" | wc -l) Python files"
echo ""

# Extract with pylupdate
if command -v pylupdate6 &> /dev/null; then
    PYLUPDATE="pylupdate6"
elif command -v pylupdate5 &> /dev/null; then
    PYLUPDATE="pylupdate5"
else
    echo "⛔ Error: pylupdate not found"
    echo "   Install: pip install pyqt6-tools"
    exit 1
fi

echo "🔧 Using: $PYLUPDATE"
echo ""

echo "📝 Extracting translations..."
$PYLUPDATE $PY_FILES -ts "$I18N_DIR/wakka_es.ts" -ts "$I18N_DIR/wakka_en.ts"

echo ""
echo "✅ Extraction complete!"
ls -lh "$I18N_DIR"/*.ts