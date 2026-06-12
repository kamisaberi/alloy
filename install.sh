#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# --- Configuration ---
INSTALL_DIR="$HOME/.local/share/alloy"
BIN_DIR="$HOME/.local/bin"
SHELL_CONFIG=""

echo "🔗 Starting Alloy Linux Installer..."

# --- 1. Check Dependencies ---
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed. Please install it first."
    exit 1
fi

# Ensure python3-venv is available
if ! python3 -m venv --help &> /dev/null; then
    echo "❌ Error: python3-venv is missing."
    echo "Please install it using your package manager (e.g., 'sudo apt install python3-venv')."
    exit 1
fi

# --- 2. Create Isolated Environment ---
echo "⚙️ Creating isolated environment at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
python3 -m venv "$INSTALL_DIR/venv"

# --- 3. Install Alloy ---
echo "📦 Installing Alloy and dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip setuptools wheel
"$INSTALL_DIR/venv/bin/pip" install .

# --- 4. Expose the CLI Binary via Symlink ---
echo "🚀 Exposing 'alloy' command globally..."
mkdir -p "$BIN_DIR"

# Remove old symlink if it exists, then create the new one
rm -f "$BIN_DIR/alloy"
ln -s "$INSTALL_DIR/venv/bin/alloy" "$BIN_DIR/alloy"

# --- 5. Verify PATH Configuration ---
# Detect the user's active shell config file
if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
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