#Requires -Version 5.1
<#
.SYNOPSIS
  导出账户映射表并逐条回查（G-B-01：账户映射表逐条可追溯）。只读。
.PARAMETER MatchAttribute
  源与目标对象之间的匹配属性（例如员工编号属性），由调用方按要件定义结果传入。
.PARAMETER SourceSearchBase / TargetSearchBase
  源与目标的搜索根（识别名），由调用方传入。
.EXAMPLE
  .\Export-AccountMapping.ps1 -SourceServer <源域控> -TargetServer <目标域控> -SourceSearchBase <源OU> -TargetSearchBase <目标OU> -MatchAttribute employeeID -OutputPath .\evidence\G-B-01-01.csv
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$SourceServer,
    [Parameter(Mandatory = $true)][string]$TargetServer,
    [Parameter(Mandatory = $true)][string]$SourceSearchBase,
    [Parameter(Mandatory = $true)][string]$TargetSearchBase,
    [Parameter(Mandatory = $true)][string]$MatchAttribute,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$GateId = 'G-B-01',
    [string]$LogPath
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\common\RingiKit.Common.psm1') -Force
Test-Prerequisite -Module 'ActiveDirectory' | Out-Null
Import-Module ActiveDirectory

$props = @($MatchAttribute, 'sIDHistory', 'userPrincipalName')
$target = @{}
foreach ($u in (Get-ADUser -Filter * -SearchBase $TargetSearchBase -Server $TargetServer -Properties $props)) {
    $key = [string]$u.$MatchAttribute
    if ($key) { $target[$key] = $u }
}
$rows = @()
foreach ($s in (Get-ADUser -Filter * -SearchBase $SourceSearchBase -Server $SourceServer -Properties $props)) {
    $key = [string]$s.$MatchAttribute
    $t = if ($key -and $target.ContainsKey($key)) { $target[$key] } else { $null }
    $carried = $t -and (@($t.sIDHistory | ForEach-Object { $_.Value }) -contains $s.SID.Value)
    $detail = '源 {0} → 目标 {1}；历史 SID 携带={2}' -f $s.SamAccountName, $(if ($t) { $t.SamAccountName } else { '未映射' }), $(if ($carried) { '是' } else { '否' })
    $rows += New-EvidenceRow -Id "$GateId-01" -Requirement '账户映射表逐条可追溯' -Content $detail `
        -Method "按属性 $MatchAttribute 比对源与目标对象" -Criteria '每个源对象有唯一目标对象且携带历史 SID' -Result $(if ($t -and $carried) { '通过' } else { '不通过' })
}
if ($rows.Count -eq 0) { throw '源搜索根下没有用户对象' }
Write-StepLog -Message ('映射行数 {0}，不通过 {1}' -f $rows.Count, @($rows | Where-Object { $_.'结果' -ne '通过' }).Count) -StepId $GateId -LogPath $LogPath -WhatIf:$WhatIfPreference
Export-AuditCsv -InputObject $rows -Path $OutputPath -WhatIf:$WhatIfPreference
