@echo off
REM Set SSL certificate path
set SSL_CERT_FILE=C:\Android_Projects\GoogleCalendar_toExcel\venv\Lib\site-packages\certifi\cacert.pem
set REQUESTS_CA_BUNDLE=C:\Android_Projects\GoogleCalendar_toExcel\venv\Lib\site-packages\certifi\cacert.pem

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the app
streamlit run calendar_export_app.py

pause
