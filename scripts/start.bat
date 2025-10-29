@echo off
REM Run makemigrations, migrate, then start Django dev server (Windows)
REM Usage:
REM   scripts\start.bat

setlocal enabledelayedexpansion

set PYTHON=%PYTHON%
if "%PYTHON%"=="" set PYTHON=python

set HOST=%HOST%
if "%HOST%"=="" set HOST=0.0.0.0

set PORT=%PORT%
if "%PORT%"=="" set PORT=8000

echo [start.bat] Applying model changes (makemigrations)...
%PYTHON% manage.py makemigrations --noinput

echo [start.bat] Migrating database...
%PYTHON% manage.py migrate --noinput

echo [start.bat] Starting development server on %HOST%:%PORT% ...
%PYTHON% manage.py runserver %HOST%:%PORT%

endlocal

