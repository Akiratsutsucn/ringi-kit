#Requires -Version 5.1
<#
.SYNOPSIS
  导出集合成员数并与波次表预期比对（G-A-01：集合成员规则已复核）。只读。
.PARAMETER SiteCode
  站点代码（由调用方传入，不在脚本内写死）。
.PARAMETER ExpectedCountPath
  预期值 CSV，须含列 CollectionId, ExpectedCount, Wave。
.PARAMETER TolerancePercent
  允许的差异百分比，超过即判定不通过。
.EXAMPLE
  .\Export-CollectionMembers.ps1 -SiteCode ABC -ExpectedCountPath .\expected.csv -TolerancePercent 2 -OutputPath .\evidence\G-A-01-06.csv
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$SiteCode,
    [Parameter(Mandatory = $true)][string]$ExpectedCountPath,
    [Parameter(Mandatory = $true)][double]$TolerancePercent,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$GateId = 'G-A-01',
    [string]$LogPath
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\common\RingiKit.Common.psm1') -Force
Test-Prerequisite -Module 'ConfigurationManager' | Out-Null
Import-Module ConfigurationManager
$location = Get-Location
try {
    Set-Location ('{0}:' -f $SiteCode)
    $rows = @()
    foreach ($e in (Import-Csv -LiteralPath $ExpectedCountPath)) {
        $actual = @(Get-CMCollectionMember -CollectionId $e.CollectionId).Count
        $expected = [int]$e.ExpectedCount
        $diff = if ($expected -gt 0) { [math]::Abs($actual - $expected) * 100.0 / $expected } else { [double]$actual * 100 }
        $ok = $diff -le $TolerancePercent
        $detail = '集合 {0}（波次 {1}）：实际 {2} / 预期 {3}，差异 {4:N1}%' -f $e.CollectionId, $e.Wave, $actual, $expected, $diff
        $rows += New-EvidenceRow -Id "$GateId-06" -Requirement '集合成员规则已复核（含排除项）' -Content $detail `
            -Method '导出集合成员数与波次表比对' -Criteria ('差异 ≤{0}%' -f $TolerancePercent) -Result $(if ($ok) { '通过' } else { '不通过' })
        Write-StepLog -Message $detail -StepId $GateId -LogPath $LogPath -WhatIf:$WhatIfPreference
    }
} finally {
    Set-Location $location
}
Export-AuditCsv -InputObject $rows -Path $OutputPath -WhatIf:$WhatIfPreference
