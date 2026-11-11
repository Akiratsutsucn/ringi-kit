#Requires -Version 5.1
<#
.SYNOPSIS
  历史 SID 审计：列出携带历史 SID 的对象，用于回收计划与依赖清单（G-B-01）。只读。
.EXAMPLE
  .\Get-SIDHistoryAudit.ps1 -Server <目标域控> -SearchBase <目标OU> -OutputPath .\evidence\G-B-01-02.csv
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [Parameter(Mandatory = $true)][string]$SearchBase,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$GateId = 'G-B-01',
    [string]$LogPath
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\common\RingiKit.Common.psm1') -Force
Test-Prerequisite -Module 'ActiveDirectory' | Out-Null
Import-Module ActiveDirectory

$objects = @(Get-ADObject -LDAPFilter '(sIDHistory=*)' -SearchBase $SearchBase -Server $Server -Properties sIDHistory, objectClass)
$rows = @()
foreach ($o in $objects) {
    $detail = '{0}（{1}）：历史 SID {2} 个' -f $o.Name, $o.ObjectClass, @($o.sIDHistory).Count
    $rows += New-EvidenceRow -Id "$GateId-02" -Requirement '历史 SID 存活期限与回收日已书面确定' -Content $detail `
        -Method '只读查询携带历史 SID 的对象' -Criteria '每个对象已列入回收计划或依赖清单' -Result '无法判定'
}
if ($rows.Count -eq 0) {
    $rows += New-EvidenceRow -Id "$GateId-02" -Requirement '历史 SID 存活期限与回收日已书面确定' -Content '搜索根下没有携带历史 SID 的对象' `
        -Method '只读查询携带历史 SID 的对象' -Criteria '与迁移批次计划一致' -Result '无法判定'
}
Write-StepLog -Message ('携带历史 SID 的对象 {0} 个；结果栏需与回收计划人工核对后改为通过/不通过' -f $objects.Count) -StepId $GateId -LogPath $LogPath -WhatIf:$WhatIfPreference
Export-AuditCsv -InputObject $rows -Path $OutputPath -WhatIf:$WhatIfPreference
