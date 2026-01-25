@echo off
echo ========================================
echo Google Calendar to CSV Export
echo DIAGNOSTIC VERSION (SSL Bypass)
echo ========================================
echo.
echo This version works around SSL issues on Windows.
echo SSL verification will be disabled (safe on home networks).
echo.
echo Press any key to start the app...
pause >nul

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the diagnostic app
streamlit run calendar_export_app_diagnostic.py

pause
