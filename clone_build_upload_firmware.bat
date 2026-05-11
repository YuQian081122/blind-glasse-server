@echo off
setlocal EnableExtensions
REM 切到本 bat 所在目錄；韌體 clone 到與 bat 同層的「firmware」資料夾（與整包 MyProject/server 並列時請用此名）
cd /d "%~dp0"

chcp 65001 >nul
title blind-glasses-firmware — clone / PlatformIO / build / upload

set "REPO_NAME=firmware"
set "REPO_URL=https://github.com/YuQian081122/blind-glasses-firmware.git"
REM 要固定分支可改成 main，或留空用預設分支
set "REPO_BRANCH=main"

echo.
echo === 0  檢查 Git ===
where git >nul 2>&1
if errorlevel 1 (
  echo 請先安裝 Git for Windows: https://git-scm.com/download/win
  echo 安裝時勾選「Add Git to PATH」。
  goto :fail
)

echo.
echo === 1  Clone 或更新 GitHub 專案 ===
if not exist "%REPO_NAME%\.git" (
  echo 正在 clone 到: "%CD%\%REPO_NAME%"
  git clone "%REPO_URL%" "%REPO_NAME%"
  if errorlevel 1 goto :fail
) else (
  echo 已存在專案，執行 git pull...
  pushd "%REPO_NAME%"
  git pull --ff-only
  if errorlevel 1 (
    echo git pull 失敗，請手動處理衝突後再執行本腳本。
    popd
    goto :fail
  )
  popd
)

if defined REPO_BRANCH (
  pushd "%REPO_NAME%"
  git fetch origin
  git checkout "%REPO_BRANCH%" 2>nul
  git pull --ff-only origin "%REPO_BRANCH%" 2>nul
  popd
)

cd /d "%~dp0%REPO_NAME%"
if not exist "platformio.ini" (
  echo 錯誤: 找不到 platformio.ini，請確認已 clone 成功且 REPO_NAME=%REPO_NAME% 正確。
  goto :fail
)

echo.
echo === 2  檢查 Python 3 ===
set "PY=py -3"
%PY% -c "import sys; assert sys.version_info>=(3,8)" >nul 2>&1
if errorlevel 1 set "PY=python"
%PY% -c "import sys; assert sys.version_info>=(3,8)" >nul 2>&1
if errorlevel 1 (
  echo 請安裝 Python 3.8 以上: https://www.python.org/downloads/windows/
  echo 安裝時勾選「Add python.exe to PATH」。
  goto :fail
)
echo 使用: %PY%

echo.
echo === 3  安裝／升級 PlatformIO Core（含各 board 套件，首次較久）===
%PY% -m pip install -U pip setuptools wheel
if errorlevel 1 goto :fail
%PY% -m pip install -U platformio
if errorlevel 1 goto :fail

echo.
echo === 4  編譯韌體（會自動下載 toolchain 與 lib_deps，可能數分鐘）===
%PY% -m platformio run
if errorlevel 1 goto :fail

echo.
echo === 5  燒錄到板子 ===
echo 請用 USB 接上板子；僅一個 COM 時會自動選。若失敗請改執行: pio run -t upload --upload-port COM3
%PY% -m platformio run -t upload
if errorlevel 1 goto :fail

echo.
echo 全部完成。
goto :end

:fail
echo.
echo 執行失敗（上列步驟有錯誤訊息）。請依訊息修正後再試。
exit /b 1

:end
pause
endlocal
exit /b 0
