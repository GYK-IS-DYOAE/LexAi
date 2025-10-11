@echo off
echo =====================================================
echo  LexAI Main Full-Stack Application Starter
echo  PostgreSQL ile Entegre
echo =====================================================
echo.
echo [1/2] Starting Backend API (Port 8000)...
start "LexAI Main Backend" cmd /k "cd LexAi-main && python run_main.py"
timeout /t 5

echo.
echo [2/2] Starting Frontend React App (Port 3001)...
cd LexAi-main\frontend
start "LexAI Main Frontend" cmd /k "npm run dev"

echo.
echo =====================================================
echo  READY!
echo =====================================================
echo  Backend API:  http://localhost:8000
echo  Frontend App: http://localhost:3001
echo  API Docs:     http://localhost:8000/docs
echo  Health Check: http://localhost:8000/api/health
echo =====================================================
echo.
echo [NOTES]
echo  - PostgreSQL must be running on localhost:5432
echo  - Database: lexai_main
echo  - Default admin: admin@lexai.com / admin123
echo =====================================================
pause

