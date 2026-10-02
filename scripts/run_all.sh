#!/bin/sh
# Tüm modelleri baştan üretir. Ön koşul: work/<figür>_600k.stl ve earbuds/*_dec.stl (bkz. README).
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
for m in airpods45 airpodspro3 airpodspro2 airpods2; do $PY scripts/build.py $m; done
$PY scripts/coupons.py
$PY scripts/check_thickness.py
$PY scripts/package.py
