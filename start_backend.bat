@echo off
echo Starting LexAI Backend...
cd /d "%~dp0"
set PYTHONPATH=%CD%
set DATABASE_URL=postgresql://lexuser:lexpass@localhost:5432/lexai
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
pause
