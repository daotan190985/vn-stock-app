@echo off
chcp 65001 >nul
title VN Stock Analyst Desk
cd /d "%~dp0"

echo ============================================
echo   VN STOCK ANALYST DESK
echo ============================================
echo.

REM --- Uu tien Python 3.12 (vnstock chua chay tot tren 3.13/3.14) ---
set "PY="
py -3.12 --version >nul 2>&1 && set "PY=py -3.12"
if "%PY%"=="" ( py -3.11 --version >nul 2>&1 && set "PY=py -3.11" )
if "%PY%"=="" ( py -3.10 --version >nul 2>&1 && set "PY=py -3.10" )

if "%PY%"=="" (
    echo [LOI] Khong tim thay Python 3.10/3.11/3.12.
    echo vnstock chua chay duoc tren Python 3.13/3.14.
    echo Hay cai Python 3.12 tai: https://www.python.org/downloads/release/python-3128/
    echo Nho tich "Add python.exe to PATH" khi cai.
    pause
    exit /b
)

echo [OK] Dung: %PY%
for /f "delims=" %%v in ('%PY% --version') do echo      %%v
echo.

echo [SETUP] Kiem tra thu vien...
%PY% -c "import streamlit" 2>nul || %PY% -m pip install streamlit
%PY% -c "import vnstock"   2>nul || %PY% -m pip install vnstock
%PY% -c "import pandas"    2>nul || %PY% -m pip install pandas
%PY% -c "import numpy"     2>nul || %PY% -m pip install numpy
echo [OK] Du thu vien.
echo.

echo Dang mo app... Dong cua so nay de tat app.
echo.
%PY% -m streamlit run app.py

pause
