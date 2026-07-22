#!/bin/bash

set -e

source .venv/bin/activate

rm -rf build
rm -rf dist
rm -f DesktopPet.spec

pyinstaller \
  --windowed \
  --name "DesktopPet" \
  --add-data "assets:assets" \
  --add-data "config:config" \
  main.py

echo "打包完成：dist/DesktopPet.app"