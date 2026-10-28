@echo off
setlocal
set "PYTHONUTF8=1"
set "UV_PYTHON=3.12"
"%~dp0tools\uv\uv.exe" run --locked --project "%~dp0launcher\core" python "%~dp0scripts\windows\game_profile.py" --set-config %*
exit /b %ERRORLEVEL%
