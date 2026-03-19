<#
.SYNOPSIS
  SNS-spiritual Windows タスクスケジューラ設定スクリプト

.DESCRIPTION
  LunaVeil_7th アカウントの自動投稿タスクを Windows タスクスケジューラに登録します。
  登録するタスク:
    - 毎日       07:00 JST
    - 毎日       12:00 JST
    - 毎日       21:00 JST
    - 水・土のみ 15:00 JST

  スリープ中のPCを自動で起動して実行する「WakeToRun」設定を有効にします。

.NOTES
  setup_tasks.bat 経由で管理者として実行してください。
#>

$ErrorActionPreference = 'Stop'

# ---- パス設定 ------------------------------------------------
$ScriptDir = $PSScriptRoot                     # windows\ フォルダ
$RepoDir   = Split-Path -Parent $ScriptDir     # リポジトリルート
$RunBat    = Join-Path $ScriptDir 'run_post.bat'

Write-Host ''
Write-Host '=== SNS-spiritual タスクスケジューラ設定 ===' -ForegroundColor Cyan
Write-Host "リポジトリ : $RepoDir"
Write-Host "実行ファイル: $RunBat"
Write-Host ''

# run_post.bat の存在確認
if (-not (Test-Path $RunBat)) {
    Write-Host "[ERROR] run_post.bat が見つかりません: $RunBat" -ForegroundColor Red
    exit 1
}

# ---- タスク共通設定 ------------------------------------------

# アクション: cmd.exe 経由で run_post.bat を実行
$action = New-ScheduledTaskAction `
    -Execute          'cmd.exe' `
    -Argument         "/c `"$RunBat`"" `
    -WorkingDirectory $RepoDir

# 設定:
#   WakeToRun        … S3スリープから自動起動して実行
#   StartWhenAvailable … 予定時刻を過ぎても次回起動時に実行
#   MultipleInstances … 多重起動しない
$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

# プリンシパル: 現在のユーザーとして実行（ログイン中に限る）
$principal = New-ScheduledTaskPrincipal `
    -UserId   ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Highest

# ---- タスク定義 ----------------------------------------------
$taskDefs = @(
    @{
        Name    = 'LunaVeil_Post_07'
        Trigger = New-ScheduledTaskTrigger -Daily -At '07:00'
        Desc    = '毎日 07:00 JST 投稿'
    },
    @{
        Name    = 'LunaVeil_Post_12'
        Trigger = New-ScheduledTaskTrigger -Daily -At '12:00'
        Desc    = '毎日 12:00 JST 投稿'
    },
    @{
        Name    = 'LunaVeil_Post_21'
        Trigger = New-ScheduledTaskTrigger -Daily -At '21:00'
        Desc    = '毎日 21:00 JST 投稿'
    },
    @{
        Name    = 'LunaVeil_Post_WedSat_15'
        Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday, Saturday -At '15:00'
        Desc    = '水・土 15:00 JST 投稿'
    }
)

# ---- タスク登録 ----------------------------------------------
Write-Host 'タスクを登録しています...' -ForegroundColor White

foreach ($td in $taskDefs) {
    $existing = Get-ScheduledTask -TaskName $td.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $td.Name -Confirm:$false
        Write-Host "  [削除] $($td.Name)  (既存を再登録)" -ForegroundColor Yellow
    }

    Register-ScheduledTask `
        -TaskName    $td.Name `
        -Description "LunaVeil_7th: $($td.Desc)" `
        -Action      $action `
        -Trigger     $td.Trigger `
        -Settings    $settings `
        -Principal   $principal | Out-Null

    Write-Host "  [OK]   $($td.Name)" -ForegroundColor Green
}

# ---- 結果表示 ------------------------------------------------
Write-Host ''
Write-Host '=== 登録完了 ===' -ForegroundColor Cyan
Write-Host ''
Write-Host '登録されたタスク:' -ForegroundColor White

Get-ScheduledTask | Where-Object { $_.TaskName -like 'LunaVeil_*' } | ForEach-Object {
    $info = Get-ScheduledTaskInfo -TaskName $_.TaskName -ErrorAction SilentlyContinue
    $nextRun = if ($info.NextRunTime) { $info.NextRunTime.ToString('yyyy-MM-dd HH:mm') } else { '不明' }
    Write-Host ("  {0,-30} 次回実行: {1}" -f $_.TaskName, $nextRun)
}

# ---- 注意事項 ------------------------------------------------
Write-Host ''
Write-Host '================================================================' -ForegroundColor Yellow
Write-Host '【重要】スリープ解除を正しく動作させるための確認事項' -ForegroundColor Yellow
Write-Host '================================================================' -ForegroundColor Yellow
Write-Host ''
Write-Host '(1) Windowsの電源プランで「スリープ解除タイマー」を有効にする'
Write-Host '    コントロールパネル → 電源オプション → プラン設定の変更'
Write-Host '    → 詳細な電源設定の変更 → スリープ'
Write-Host '    → 「スリープ解除タイマーの許可」を「有効」に設定'
Write-Host ''
Write-Host '(2) BIOS/UEFI で「Wake on RTC (RTC Alarm)」が有効になっていること'
Write-Host '    ※ S3スリープ対応済みとのことなので通常は問題なし'
Write-Host ''
Write-Host '(3) タスクスケジューラの確認: [Win+R] → taskschd.msc'
Write-Host '    「タスクスケジューラ ライブラリ」に LunaVeil_Post_* が表示されます'
Write-Host ''
Write-Host '(4) 動作テスト（手動実行）:'
Write-Host '    タスクを右クリック → 「実行」で即時テストできます'
Write-Host '    ログは logs\post.log で確認してください'
Write-Host ''
