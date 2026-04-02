@echo off
setlocal
cd /d "%~dp0"

if not exist "config.json" (
  echo Missing config.json
  echo Copy config.example.json to config.json first, then fill your WPS credentials and webhooks.
  pause
  exit /b 1
)

call :run_python -m wps_archive --config "%CD%\config.json" finalize-confirmed
set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% neq 0 (
  echo finalize-confirmed failed with exit code %EXIT_CODE%.
) else (
  echo finalize-confirmed finished.
)
pause
exit /b %EXIT_CODE%

:run_python
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python %*
  exit /b %ERRORLEVEL%
)

echo Python was not found.
echo Install Python or add py/python to PATH, then try again.
exit /b 9009
