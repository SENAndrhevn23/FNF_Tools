@echo off
title FNF TOOLBOX MENU
color 0a

:menu
cls
echo ===========================================
echo              FNF TOOLBOX MENU
echo ===========================================
echo 1: Run Chart Tool (mergeCharts.py)
echo 2: Exit
echo ===========================================
echo.
set /p choice=Select an option: 

:: -------------------------------
:: MENU LOGIC
:: -------------------------------
if "%choice%"=="8" goto charttools
if "%choice%"=="2" goto notetools
if "%choice%"=="3" goto compressiontools
if "%choice%"=="4" goto miditools
if "%choice%"=="5" goto utilities
if "%choice%"=="6" goto runall
if "%choice%"=="1" goto mergecharts
if "%choice%"=="0" exit
goto menu

:charttools
cls
echo Chart Editing Tools Coming Soon!
pause
goto menu

:notetools
cls
echo Note Tools Coming Soon!
pause
goto menu

:compressiontools
cls
echo Compression Tools Coming Soon!
pause
goto menu

:miditools
cls
echo MIDI Tools Coming Soon!
pause
goto menu

:utilities
cls
echo Utility Tools Coming Soon!
pause
goto menu

:runall
cls
echo Running ALL tools...
REM put every script you want here
REM python script1.py
REM python script2.py
pause
goto menu

:mergecharts
cls
echo ===========================================
echo   FNF CHART MERGING TOOL INTO 1 JSON
echo   Warning: Some charts may be unreadable...
echo   YOU BEEN WARNED!
echo ===========================================
echo.
python mergeCharts.py
pause
goto menu
