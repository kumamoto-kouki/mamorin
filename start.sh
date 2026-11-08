#!/bin/sh
# まもりんDM を起動します（Mac / Linux）。必要なのは Python 3.10 以上だけです。
cd "$(dirname "$0")/backend" || exit 1
python3 -m pip install -q -r requirements.txt || exit 1
IP=$(python3 -c "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('8.8.8.8',80));print(s.getsockname()[0])" 2>/dev/null || echo localhost)
echo ""
echo "  保護者の画面（スクリーンに映す）: http://$IP:8000/parent"
echo "  子どもの画面（手元で操作）      : http://$IP:8000/kid"
echo "  終了するときは Ctrl+C"
echo ""
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
