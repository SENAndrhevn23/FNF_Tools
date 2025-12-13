@echo off
setlocal ENABLEDELAYEDEXPANSION
title FNF Multitask Tool - Full Installer (Windows)
color 0a

:: ====== CONFIG ======
set ROOT_FOLDER=%USERPROFILE%\Documents\CHARTS
set SCRIPT_NAME=fnf_multitask_tool.py
set LOGFILE=install_log.txt
set SHORTCUT_NAME=FNF Multitask Tool.lnk

echo -------------------------------------------------------
echo         FNF MULTITASK TOOL - FULL INSTALLER
echo -------------------------------------------------------
echo Log file: %LOGFILE%
echo.

echo INSTALL STARTED > %LOGFILE%

:: ===============================
:: CHECK PYTHON
:: ===============================
echo Checking Python...
python --version >> %LOGFILE% 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found!
    echo Download Python here: https://www.python.org/
    pause
    exit /b
)
echo ✔ Python found!
echo.

:: ===============================
:: UPDATE PIP
:: ===============================
echo Updating pip...
python -m pip install --upgrade pip >> %LOGFILE% 2>&1
echo ✔ pip updated!
echo.

:: ===============================
:: INSTALL PYTHON MODULES
:: ===============================
echo Installing required modules...
echo -------------------------------

echo Installing pydub...
python -m pip install pydub >> %LOGFILE% 2>&1

echo Installing numpy...
python -m pip install numpy >> %LOGFILE% 2>&1

echo Installing orjson (for faster JSON serialization)...
python -m pip install orjson >> %LOGFILE% 2>&1

echo ✔ Modules installed!
echo.

:: ===============================
:: CHECK FFmpeg
:: ===============================
echo Checking FFmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo FFmpeg not found!
    echo Opening FFmpeg GitHub page for manual download...
    start https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    echo Please download and extract FFmpeg, then add it to your PATH.
) else (
    echo ✔ FFmpeg already installed!
)
echo.

:: ===============================
:: CREATE ROOT FOLDER
:: ===============================
echo Creating chart folder:
echo %ROOT_FOLDER%
mkdir "%ROOT_FOLDER%" >nul 2>&1
echo ✔ Folder ready!
echo.

:: ===============================
:: CREATE DESKTOP SHORTCUT
:: ===============================
echo Creating desktop shortcut...

set DESKTOP_PATH=%USERPROFILE%\Desktop
set SCRIPT_PATH=%CD%\%SCRIPT_NAME%

powershell -command ^
 "$ws = New-Object -ComObject WScript.Shell; ^
  $s = $ws.CreateShortcut('$DESKTOP_PATH\%SHORTCUT_NAME%'); ^
  $s.TargetPath = 'python'; ^
  $s.Arguments = '\"%SCRIPT_PATH%\"'; ^
  $s.WorkingDirectory = '%CD%'; ^
  $s.Save()"

echo ✔ Shortcut created on Desktop!
echo.

:: ===============================
:: RUN SCRIPT
:: ===============================
echo Launching tool...
python "%SCRIPT_NAME%"
echo.

echo -------------------------------------------------------
echo ✔ INSTALL COMPLETE!
echo Your FNF Multitask Tool is now ready.
echo A shortcut was added to your Desktop.
echo -------------------------------------------------------
pause
exit /b
