#!/bin/sh
#
# Single-file "claudebox" installer & updater (silent on success)
# macOS (bash 3.2+) & Linux compatible
# Release SHA256: __ARCHIVE_SHA256__
#

# Fail fast and report errors
set -e
trap 'echo "⛔ Installation error at line $LINENO" >&2' ERR

# Silence all normal output
exec 1>/dev/null

# 1) Dev-mode detection - if running from a git repo, just execute directly
if [ -f ./main.sh ] && [ -d ./lib ]; then
  exec bash ./main.sh "$@"
fi

# 2) "Release" mode install/update
INSTALL_DIR="$HOME/.claudebox"
ARCHIVE_SHA256="__ARCHIVE_SHA256__"
ARCHIVE_PATH="$INSTALL_DIR/archive.tar.gz"

mkdir -p "$INSTALL_DIR"

# 3) Choose checksum tool
if   command -v sha256sum >/dev/null 2>&1; then
  CHKPROG="sha256sum"; CHKARG=""
elif command -v shasum   >/dev/null 2>&1; then
  CHKPROG="shasum";   CHKARG="-a 256"
else
  echo "⛔ sha256sum or shasum required." >&2
  exit 1
fi

# 4) Compare and extract if needed
if [ -f "$ARCHIVE_PATH" ] \
  && [ "$($CHKPROG $CHKARG "$ARCHIVE_PATH" | awk '{print $1}')" = "$ARCHIVE_SHA256" ]; then
  :  # up-to-date, silent
else
  SKIP=$(awk '/^__ARCHIVE_BELOW__/ {print NR+1; exit}' "$0")
  tail -n +"$SKIP" "$0" > "$ARCHIVE_PATH"
  tar -xz -f "$ARCHIVE_PATH" -C "$INSTALL_DIR" --strip-components=1
fi

# 5) Launch main.sh from install directory
exec bash "$INSTALL_DIR/main.sh" "$@"

__ARCHIVE_BELOW__