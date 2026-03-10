#!/usr/bin/env bash
# Tax Receipt Autopilot — Mac/Linux Installer
# Run once to install Python dependencies for bank statement parsing.
# Usage: bash install.sh

set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
REQUIREMENTS="$SKILL_DIR/scripts/requirements.txt"
VALIDATOR="$SKILL_DIR/scripts/setup_validator.py"

echo ""
echo "Tax Receipt Autopilot — Setup"
echo "=============================="
echo ""

# --- Find Python ---
PYTHON=""
for cmd in python3 python py; do
    if command -v "$cmd" &>/dev/null; then
        # Make sure it's Python 3, not Python 2
        VER=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "0")
        if [ "$VER" = "3" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Python 3 not found."
    echo ""
    echo "Install it from: https://python.org/downloads"
    echo "(Install with default settings, make sure 'Add to PATH' is checked)"
    echo ""
    echo "NOTE: Python is only needed for CSV/PDF bank statement parsing."
    echo "You can use the skill without it — just paste bank rows into Claude"
    echo "or submit receipt photos directly."
    echo ""
    exit 0
fi

PYTHON_VERSION=$($PYTHON --version 2>&1)
echo "Python found: $PYTHON_VERSION"
echo ""

# --- Optional: venv recommendation ---
# Installing into system Python is fine for a personal tool, but if you want
# a cleaner setup that won't conflict with other Python projects, run:
#
#   python3 -m venv ~/.tax-autopilot-venv
#   source ~/.tax-autopilot-venv/bin/activate
#   bash install.sh
#
# Then activate the venv before each session:  source ~/.tax-autopilot-venv/bin/activate

# --- Install core dependencies ---
echo "Installing core dependencies..."
if ! "$PYTHON" -m pip install -r "$REQUIREMENTS" --quiet --upgrade; then
    echo ""
    echo "pip install failed."
    echo "Common fixes:"
    echo "  • Try: $PYTHON -m pip install -r scripts/requirements.txt --user"
    echo "  • Or run with sudo: sudo $PYTHON -m pip install -r scripts/requirements.txt"
    echo "  • Or use a virtual env (see the venv note at the top of this file)"
    echo ""
    exit 1
fi
echo "Core dependencies installed."
echo ""

# --- Install optional speedup (requires C compiler — fails gracefully) ---
echo "Installing optional fuzzy matching speedup (python-Levenshtein)..."
if "$PYTHON" -m pip install "python-Levenshtein>=0.12.0" --quiet 2>/dev/null; then
    echo "Speedup installed — fuzzy matching will be faster."
else
    echo "Speedup skipped — C compiler not available (this is fine)."
    echo "Fuzzy matching still works, just slightly slower without it."
fi
echo ""

# --- Run validator ---
if [ -f "$VALIDATOR" ]; then
    echo "Running setup check..."
    echo ""
    "$PYTHON" "$VALIDATOR"
else
    echo "Validation skipped (validator not found at $VALIDATOR)"
fi
