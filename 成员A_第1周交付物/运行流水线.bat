@echo off
chcp 65001 >nul
cd /d %~dp0backend
python run_pipeline.py
echo.
pause
