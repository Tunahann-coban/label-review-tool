#!/usr/bin/env bash
# Etiket Inceleme Araci: tek tikla baslat (Mac / Linux).
#   ./baslat.sh                    araci acar
#   ./baslat.sh --reviewer ayse    ilk acista kendi adini ver
#   ./baslat.sh yenile             arayuzu yeniden derler (kod degistiyse)
# Ilk calistirmada Python paketlerini ve arayuzu kurar. Gerekenler: Python 3.11/3.12, Node.js 20+.
set -e
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "python3 bulunamadi"; exit 1; }

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/3] Python ortami kuruluyor..."
  python3 -m venv .venv
  .venv/bin/python -m pip install -q -r server/requirements.txt
fi

rebuild=""
if [ "$1" = "yenile" ]; then rebuild=1; shift; fi
[ -f web/dist/index.html ] || rebuild=1
if [ -n "$rebuild" ]; then
  command -v npm >/dev/null || { echo "Node.js bulunamadi, arayuz derlenemiyor: https://nodejs.org"; exit 1; }
  echo "[2/3] Arayuz derleniyor..."
  (cd web && { [ -d node_modules ] || npm install --no-audit --no-fund; } && npm run build)
fi

echo "[3/3] Arac aciliyor. Kapatmak icin Ctrl+C."
exec .venv/bin/python server/server.py --open "$@"
