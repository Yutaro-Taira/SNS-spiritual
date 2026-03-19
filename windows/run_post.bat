@echo off
setlocal

:: =============================================================
::  run_post.bat  ─  タスクスケジューラから呼ばれる実行ラッパー
::  ここを直接ダブルクリックしてテスト実行もできます
:: =============================================================

:: このファイル (windows\) の一つ上 = リポジトリルート
pushd "%~dp0.."
set "REPO_DIR=%CD%"
popd

:: ログ出力先
set "LOG_DIR=%REPO_DIR%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOGFILE=%LOG_DIR%\post.log"

:: ---- Python 検索（仮想環境優先 → システム Python）-----------
set "PYTHON=python"
if exist "%REPO_DIR%\venv\Scripts\python.exe"  set "PYTHON=%REPO_DIR%\venv\Scripts\python.exe"
if exist "%REPO_DIR%\.venv\Scripts\python.exe" set "PYTHON=%REPO_DIR%\.venv\Scripts\python.exe"

:: ---- 実行 ---------------------------------------------------
echo [%DATE% %TIME%] === post.py 開始 === >> "%LOGFILE%"

cd /d "%REPO_DIR%"
"%PYTHON%" poster\post.py >> "%LOGFILE%" 2>&1
set EXIT_CODE=%errorlevel%

echo [%DATE% %TIME%] 終了コード: %EXIT_CODE% >> "%LOGFILE%"
echo. >> "%LOGFILE%"

exit /b %EXIT_CODE%
