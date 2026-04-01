@echo off
setlocal
cd /d "%~dp0"

if not exist "config.json" (
  echo Missing config.json
  echo Copy config.example.json to config.json first, then fill your WPS credentials and webhooks.
  pause
  exit /b 1
)

py -m wps_archive --config "%CD%\config.json" finalize-confirmed
set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% neq 0 (
  echo finalize-confirmed failed with exit code %EXIT_CODE%.
) else (
  echo finalize-confirmed finished.
)
pause
exit /b %EXIT_CODE%
