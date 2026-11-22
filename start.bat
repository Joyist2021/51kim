@echo off
cd /d "%~dp0"
echo Starting 51kim local mirror at http://127.0.0.1:8080/
python server.py 8080
pause
