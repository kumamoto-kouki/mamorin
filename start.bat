@echo off
chcp 65001 > nul
rem まもりんDM を起動します（Windows）。必要なのは Python 3.10 以上だけです。
cd /d "%~dp0backend"
python -m pip install -q -r requirements.txt || exit /b 1
for /f %%i in ('python -c "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('8.8.8.8',80));print(s.getsockname()[0])"') do set IP=%%i
echo.
echo   保護者の画面（スクリーンに映す）: http://%IP%:8000/parent
echo   子どもの画面（手元で操作）      : http://%IP%:8000/kid
echo   終了するときは Ctrl+C
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000
