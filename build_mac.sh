#!/bin/bash

set -e

source .venv/bin/activate

SOURCE_ICON="assets/floating_ball/image.png"
ICONSET_DIR="build/icon.iconset"
SQUARE_ICON="build/icon_square.png"
APP_ICON="assets/AppIcon.icns"

rm -rf build
rm -rf dist
rm -f ruru.spec

mkdir -p "$ICONSET_DIR"

# Crop to a centered square for macOS icon sizes.
sips -c 1024 1024 "$SOURCE_ICON" --out "$SQUARE_ICON" >/dev/null

for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$SQUARE_ICON" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" "$SQUARE_ICON" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
done

iconutil -c icns "$ICONSET_DIR" -o "$APP_ICON"

pyinstaller \
  --windowed \
  --name "ruru" \
  --icon "$APP_ICON" \
  --add-data "assets:assets" \
  --add-data "config:config" \
  main.py

echo "打包完成：dist/ruru.app"
