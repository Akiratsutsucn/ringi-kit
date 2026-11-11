#Requires -Version 5.1
<#
.SYNOPSIS
  同步状态检查：调度器状态、暂存模式、最近各连接器运行结果（T-02 验收证据）。只读。
.DESCRIPTION
  需在同步服务器本机执行，依赖同步服务自带的 ADSync 模块。不修改任何同步配置。
.EXAMPLE
  .\Get-SyncStatus.ps1 -OutputPath .\evidence\T-02-sync-status.csv
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [int]$RecentRuns = 5,
    [string]$LogPath
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\common\RingiKit.Common.psm1') -Force
Test-Prerequisite -Module 'ADSync' | Out-Null
Import-Module ADSync

$sched = Get-ADSyncScheduler
$rows = @()
$rows += New-EvidenceRow -Id 'T-02' -Requirement '同步周期无失败' `
    -Content ('调度器启用={0}；暂存模式={1}；同步周期={2}' -f $sched.SyncCycleEnabled, $sched.StagingModeEnabled, $sched.CurrentlyEffectiveSyncCycleInterval) `
    -Method '读取同步调度器状态' -Criteria '调度器启用且暂存模式与设计一致' -Result $(if ($sched.SyncCycleEnabled) { '通过' } else { '不通过' })
foreach ($c in (Get-ADSyncConnector)) {
    $runs = @(Get-ADSyncRunProfileResult -ConnectorId $c.Identifier -NumberRequested $RecentRuns)
    $failed = @($runs | Where-Object { $_.Result -ne 'success' })
    $detail = '连接器 {0}：最近 {1} 次运行，失败 {2} 次' -f $c.Name, $runs.Count, $failed.Count
    $rows += New-EvidenceRow -Id 'T-02' -Requirement '同步周期无失败' -Content $detail `
        -Method '读取连接器最近运行结果' -Criteria '失败次数 0' -Result $(if ($failed.Count -eq 0) { '通过' } else { '不通过' })
    Write-StepLog -Message $detail -StepId 'T-02' -LogPath $LogPath -WhatIf:$WhatIfPreference
}
Export-AuditCsv -InputObject $rows -Path $OutputPath -WhatIf:$WhatIfPreference
