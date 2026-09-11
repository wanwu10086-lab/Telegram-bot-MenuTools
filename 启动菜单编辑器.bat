@echo off
cd /d "%~dp0"
echo Starting Menu Editor (port 1002)...
echo Keep this window open while using the editor.
echo Browser will open automatically in a few seconds.
echo.
.venv\Scripts\python.exe menu_server.py
echo.
echo Server stopped. Press any key to close.
pause >nul