@echo off
:: =============================================================
::  setup_tasks.bat  ─  タスクスケジューラ設定ランチャー
::
::  【使い方】このファイルをダブルクリックするだけ
::  管理者権限が必要なため、UAC確認画面が表示されます
:: =============================================================

:: ---- 管理者権限チェック・自動昇格 ---------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 管理者権限が必要です。UAC確認画面を承認してください...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: ---- PowerShell スクリプトを実行 ----------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_tasks.ps1"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 設定に失敗しました。上記のエラーメッセージを確認してください。
    pause
    exit /b 1
)

echo.
pause
