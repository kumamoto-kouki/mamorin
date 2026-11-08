#!/bin/bash
# まもりんDM をWSL(Ubuntu)で起動します。画面はビルド済みなので Node.js は不要です。
cd "$(dirname "$0")/backend" || exit 1
if [ ! -x .venv/bin/uvicorn ]; then
  python3 -m venv .venv 2>/dev/null || { sudo apt update && sudo apt install -y python3-venv && python3 -m venv .venv; } || exit 1
  .venv/bin/pip install -q -r requirements.txt || exit 1
fi
echo ""
echo "  Windowsのブラウザで開いてください"
echo "  保護者の画面    : http://localhost:8000/parent"
echo "  子どもの画面    : http://localhost:8000/kid"
echo "  あやしい大人役  : http://localhost:8000/stranger"
echo "  終了は Ctrl+C"
echo ""
exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
