@echo off
cd /d "%~dp0\.."
call venv\Scripts\activate
python -m scripts.local_scraper --api-url https://mi-app.onrender.com
pause
