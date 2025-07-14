#!/bin/bash
# Build the ClaudeBox self-extracting installer script
# Packages entire repo for extraction to ~/.claudebox/

set -euo pipefail

TEMPLATE=".builder/script_template_root.sh"
OUTPUT="claudebox"  # Changed from claudebox.run.sh
ARCHIVE="archive.tar.gz"

# Create archive in temp location to avoid "file changed as we read it" error
TEMP_ARCHIVE="/tmp/claudebox_archive_$$.tar.gz"

# Create archive of entire repo (excluding hidden files and build output)
echo "📦 Creating archive..."
tar -czf "$TEMP_ARCHIVE" \
  --exclude='.git' \
  --exclude='.gitignore' \
  --exclude='.github' \
  --exclude='.builder' \
  --exclude='.bmad-core' \
  --exclude='.bmad_core' \
  --exclude='.claude' \
  --exclude='.vscode' \
  --exclude='.idea' \
  --exclude='.mcp.json' \
  --exclude='claudebox' \
  --exclude='test_project' \
  --exclude='test_new_project' \
  --exclude='test-project' \
  --exclude='*.swp' \
  --exclude='*~' \
  --exclude='archive.tar.gz' \
  --exclude='*.tar.gz' \
  .

# Move to final location
mv "$TEMP_ARCHIVE" "$ARCHIVE"

# Calculate SHA256
if command -v sha256sum >/dev/null 2>&1; then
  SHA256=$(sha256sum "$ARCHIVE" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  SHA256=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')
else
  echo "❌ sha256sum or shasum required" >&2
  exit 1
fi

# Create final script with SHA256 embedded
echo "🔧 Assembling $OUTPUT..."
sed "s/__ARCHIVE_SHA256__/$SHA256/g" "$TEMPLATE" > "$OUTPUT"
cat "$ARCHIVE" >> "$OUTPUT"
chmod +x "$OUTPUT"

# Cleanup
rm -f "$ARCHIVE"

echo "✅ $OUTPUT created (SHA256: $SHA256)"
echo "📏 Size: $(ls -lh "$OUTPUT" | awk '{print $5}')"