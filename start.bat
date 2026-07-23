
@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0.deps"
set "PYTHON_EXE=C:\Users\jbzhou2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist ".env" (
  echo Missing .env configuration file.
  exit /b 1
)

if not exist ".deps\discord" (
  echo Installing dependencies...
  "%PYTHON_EXE%" -m pip install --target ".deps" -r requirements.txt
  if errorlevel 1 exit /b 1
)

echo Starting Dungeon Explorer Bot...
"%PYTHON_EXE%" -u bot.py
