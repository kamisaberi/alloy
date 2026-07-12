#!/bin/bash

# Safe Guard: If this script is run with 'sh' (which maps to 'dash' on Ubuntu),
# force re-execution with 'bash' to avoid syntax errors like "Bad substitution" [1].
if [ -z "$BASH_VERSION" ]; then
    exec bash "$0" "$@"
fi

# Exit immediately if a command exits with a non-zero status
set -e

# --- 1. Prevent Root / Sudo Execution ---
# Running as root or sudo will corrupt user-space permissions in ~/.local/ [2]
if [ "$EUID" -eq 0 ]; then
    echo "❌ Error: Please do NOT run this script as root or with sudo."
    echo "   Alloy installs into your local user directory (~/.local/)."
    echo "   Running as root will corrupt your local file permissions."
    exit 1
fi

# --- 2. Identify Source Directory ---
# Automatically switch to the directory where this install script is located.
# This prevents 'pip install .' from failing if run from outside the repository [3].
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Verify that we are indeed in the Alloy repository containing pyproject.toml [3]
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Could not find 'pyproject.toml' in $SCRIPT_DIR."
    echo "   Please make sure you run this script from inside the Alloy repository folder."
    exit 1
fi

# --- Configuration ---
INSTALL_DIR="$HOME/.local/share/alloy"
BIN_DIR="$HOME/.local/bin"
SHELL_CONFIG=""

echo "🔗 Starting Alloy Linux Installer..."

# --- 3. Check Dependencies & Resolve Python Executable ---
PYTHON_EXE=""

if command -v python3 &> /dev/null; then
    PYTHON_EXE="python3"
elif command -v python &> /dev/null && python -c 'import sys; sys.exit(0 if sys.version_info.major >= 3 else 1)' &> /dev/null; then
    # Fallback: if 'python' exists and is version 3
    PYTHON_EXE="python"
else
    echo "❌ Error: Python 3 could not be found in your PATH."
    echo "   Please ensure python3 or python (v3+) is installed and accessible."
    exit 1
fi

echo "✅ Using Python executable: $(command -v $PYTHON_EXE) ($($PYTHON_EXE --version))"

# Query the interpreter directly to see if venv is importable.
if ! $PYTHON_EXE -c "import venv" &> /dev/null; then
    echo "❌ Error: Python venv module is missing."
    echo "   Please install it using your package manager (e.g., 'sudo apt install python3-venv')."
    exit 1
fi

# --- 4. Create Isolated Environment ---
echo "⚙️  Creating isolated environment at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
$PYTHON_EXE -m venv "$INSTALL_DIR/venv"

# --- 5. Install Alloy ---
echo "📦 Installing Alloy and dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip setuptools wheel
"$INSTALL_DIR/venv/bin/pip" install .

# --- 6. Expose the CLI Binary via Symlink ---
echo "🚀 Exposing 'alloy' command globally..."
mkdir -p "$BIN_DIR"

# Remove old symlink if it exists, then create the new one
rm -f "$BIN_DIR/alloy"
ln -s "$INSTALL_DIR/venv/bin/alloy" "$BIN_DIR/alloy"

# --- 7. Verify PATH Configuration ---
# Detect the user's active shell using the $SHELL environment variable [4]
if [[ "$SHELL" == *"zsh"* ]] && [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]] && [ -f "$HOME/.bashrc" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
else
    SHELL_CONFIG="$HOME/.profile"
fi

# Check if ~/.local/bin is already in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "⚠️  $BIN_DIR is not in your system PATH."
    echo "Adding it to $SHELL_CONFIG..."

    # Append to the shell config file safely
    echo "" >> "$SHELL_CONFIG"
    echo "# Alloy CLI PATH" >> "$SHELL_CONFIG"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_CONFIG"

    echo "✅ PATH configured successfully."
    echo "👉 PLEASE RUN: source $SHELL_CONFIG (or restart your terminal) to apply changes."
else
    echo "✅ PATH is already correctly configured."
fi

echo "🎉 Alloy installed successfully! Type 'alloy --help' to get started."