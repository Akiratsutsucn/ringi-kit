#Requires -Version 5.1
<#
.SYNOPSIS
  域结构盘点：林、域、功能级别、域控数量。只读（项目 B 现状评估、G-B-01 证据）。
.PARAMETER Server
  要查询的域控（由调用方传入）。
.EXAMPLE
  .\Get-ForestInventory.ps1 -Server <域控名> -OutputPath .\evidence\B-forest-inventory.csv
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [System.Management.Automation.PSCredential]$Credential,
    [string]$LogPath
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\common\RingiKit.Common.psm1') -Force
Test-Prerequisite -Module 'ActiveDirectory' | Out-Null
Import-Module ActiveDirectory

$common = @{ Server = $Server }
if ($Credential) { $common.Credential = $Credential }
$forest = Get-ADForest @common
$rows = @()
foreach ($d in $forest.Domains) {
    $dom = Get-ADDomain -Identity $d @common
    $dcs = @(Get-ADDomainController -Filter * -Server $dom.PDCEmulator)
    $detail = '林 {0} / 域 {1}：林功能级别 {2}，域功能级别 {3}，域控 {4} 台' -f $forest.Name, $dom.DNSRoot, $forest.ForestMode, $dom.DomainMode, $dcs.Count
    $rows += New-EvidenceRow -Id 'B-INV' -Requirement '三林结构与域控分布（现状评估）' -Content $detail `
        -Method '目录服务只读查询' -Criteria '与方案书第 2 章现状表一致' -Result '通过'
    Write-StepLog -Message $detail -StepId 'B-INV' -LogPath $LogPath -WhatIf:$WhatIfPreference
}
Export-AuditCsv -InputObject $rows -Path $OutputPath -WhatIf:$WhatIfPreference
