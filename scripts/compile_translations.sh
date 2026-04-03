#!/bin/bash
# =============================================================================
# Wakka — Translation Compilation Script
# Compiles Qt TS files to QM binary files
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
I18N_DIR="$PROJECT_ROOT/main/ui/i18n"

echo "🔨 Wakka Translation Compiler"
echo "============================="
echo ""

# Check for lrelease
if command -v lrelease-qt6 &> /dev/null; then
    LRELEASE="lrelease-qt6"
elif command -v lrelease &> /dev/null; then
    LRELEASE="lrelease"
else
    echo "⛔ Error: lrelease not found"
    echo "   Install: sudo pacman -S qt6-tools"
    exit 1
fi

echo "Using: $LRELEASE"
echo ""

# Compile all TS files
for ts_file in "$I18N_DIR"/*.ts; do
    if [ -f "$ts_file" ]; then
        filename=$(basename "$ts_file")
        echo "📄 Compiling $filename..."
        $LRELEASE "$ts_file"
    fi
done

echo ""
echo "✅ Compilation complete!"
echo ""
echo "📂 Generated .qm files:"
ls -lh "$I18N_DIR"/*.qm 2>/dev/null || echo "   No .qm files generated"