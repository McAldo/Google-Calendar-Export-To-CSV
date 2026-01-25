@echo off
echo ========================================
echo Google Calendar to CSV Export
echo ========================================
echo.
echo Starting the app...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the app
streamlit run calendar_export_app.py

pause
