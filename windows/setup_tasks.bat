@echo off
:: =============================================================
::  setup_tasks.bat  ─  タスクスケジューラ設定ランチャー
::
::  【使い方】このファイルをダブルクリックするだけ
::  管理者権限が必要な場合は自動でUAC画面が表示されます
:: =============================================================

:: PowerShell に処理を委譲（管理者チェックと昇格はPS1側で行う）
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_tasks.ps1"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 設定に失敗しました。上記のエラーメッセージを確認してください。
    pause
    exit /b 1
)

echo.
pause
