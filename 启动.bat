@echo off
cd /d %~dp0

REM self-redirect all output to a log file for easy debugging
if not defined LOGGED (
  set LOGGED=1
  cmd /c "%~f0" >> "%~dp0startup_log.txt" 2>&1
  exit /b
)

echo ============================================================
echo   Food Category Classifier - Startup  (%date% %time%)
echo ============================================================

REM ---- 0. resolve uv (install if missing) ----
set "UV="
if exist "C:\Users\dongxiaotong\.local\bin\uv.exe" set "UV=C:\Users\dongxiaotong\.local\bin\uv.exe"
where uv >nul 2>&1 && set "UV=uv"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%LOCALAPPDATA%\uv\uv.exe" set "UV=%LOCALAPPDATA%\uv\uv.exe"
if not defined UV (
  echo uv not found. Installing uv (official installer)...
  powershell -NoProfile -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
  if exist "%LOCALAPPDATA%\uv\uv.exe" set "UV=%LOCALAPPDATA%\uv\uv.exe"
  where uv >nul 2>&1 && set "UV=uv"
)
if not defined UV ( echo Cannot find or install uv. See https://docs.astral.sh/uv/ ; pause; exit /b )
echo Using uv: %UV%

REM ---- 1. resolve venv python (scan C:\Users\*, no hardcoded name) ----
set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if defined MYVENV if exist "%MYVENV%" set "PY=%MYVENV%"
if not defined PY (
  for /d %%d in ("%USERPROFILE%" "C:\Users\*") do (
    if exist "%%d\.venv\Scripts\python.exe" if not defined PY set "PY=%%d\.venv\Scripts\python.exe"
  )
)
if not defined PY (
  echo venv not found, creating one in the project ...
  "%UV%" venv "%~dp0.venv"
  if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
)
if not defined PY ( echo Cannot find or create a venv. Set MYVENV to your python.exe path and re-run. ; pause; exit /b )
echo Using python: %PY%
"%PY%" --version

REM ---- 2. install deps with uv + Tsinghua mirror ----
echo [1/3] Installing dependencies via uv (Tsinghua mirror)...
"%UV%" pip install --python "%PY%" -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 ( echo Dependency install failed. ; pause; exit /b )

REM ---- 3. sanity check ----
"%PY%" -c "import django, sklearn, ultralytics, PIL; print('Dependencies OK')" 2>nul
if errorlevel 1 ( echo Django/sklearn/ultralytics/Pillow not importable from this venv. ; pause; exit /b )

REM ---- 4. init db + data ----
echo [2/3] Initializing database and data...
"%PY%" manage.py migrate
"%PY%" manage.py load_data

REM ---- 5. run ----
echo [3/3] Starting web server...
echo Open browser: http://127.0.0.1:8000/
echo Student: student / student123    Admin: admin / admin123
echo Close this window to stop the server.
"%PY%" manage.py runserver 0.0.0.0:8000
pause
