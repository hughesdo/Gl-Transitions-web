@echo off
call venv\Scripts\activate.bat
start "" "http://127.0.0.1:8000"
python -m uvicorn main:app --reload
pause
