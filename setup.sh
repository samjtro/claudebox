#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="$HOME/.claudebox"
TARGET_DIR="$INSTALL_ROOT/scripts"
LINK_PATH="$HOME/.local/bin/claudebox"

# Silent installation
rm -rf "$TARGET_DIR"
mkdir -p "$INSTALL_ROOT"
cp -a scripts "$INSTALL_ROOT/"
cp -a commands "$INSTALL_ROOT/"
cp -a build "$INSTALL_ROOT/"
chmod +x "$INSTALL_ROOT/scripts/bin/claudebox"

mkdir -p "$(dirname "$LINK_PATH")"
ln -sf "$INSTALL_ROOT/scripts/bin/claudebox" "$LINK_PATH"

# Source common.sh for logo function
source "$INSTALL_ROOT/scripts/lib/common.sh"

# Show logo
echo
logo

echo "To get started, run: claudebox"
exit 0