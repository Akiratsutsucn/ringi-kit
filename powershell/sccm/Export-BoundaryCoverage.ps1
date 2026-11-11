#Requires -Version 5.1
<#
.SYNOPSIS
  拠点网段清单与边界做差集（G-A-01：边界组覆盖目标全部网段）。只读。
.PARAMETER SubnetListPath
  拠点网段 CSV，须含列 Site, Cidr（形如 a.b.c.d/nn）。
.PARAMETER BoundaryListPath
  从控制台导出的边界 CSV，须含列 Type（IPSubnet/IPRange）, Value（CIDR 或 起始-结束）, BoundaryGroup。
.EXAMPLE
  .\Export-BoundaryCoverage.ps1 -SubnetListPath .\subnets.csv -BoundaryListPath .\boundaries.csv -OutputPath .\evidence\G-A-01-03.csv
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$SubnetListPath,
    [Parameter(Mandatory = $true)][string]$BoundaryListPath,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$GateId = 'G-A-01',
    [string]$LogPath
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\common\RingiKit.Common.psm1') -Force

function ConvertTo-UInt32([string]$Ip) {
    $b = ([System.Net.IPAddress]::Parse($Ip)).GetAddressBytes()
    [Array]::Reverse($b)
    return [BitConverter]::ToUInt32($b, 0)
}
function Get-CidrRange([string]$Cidr) {
    $parts = $Cidr.Split('/')
    $len = [int]$parts[1]
    $start = ConvertTo-UInt32 $parts[0]
    $size = [math]::Pow(2, 32 - $len)
    $first = [uint32]([math]::Floor($start / $size) * $size)
    return @($first, [uint32]($first + $size - 1))
}

$ranges = @()
foreach ($b in (Import-Csv -LiteralPath $BoundaryListPath)) {
    if ($b.Type -eq 'IPSubnet') { $r = Get-CidrRange $b.Value }
    elseif ($b.Type -eq 'IPRange') { $p = $b.Value.Split('-'); $r = @((ConvertTo-UInt32 $p[0].Trim()), (ConvertTo-UInt32 $p[1].Trim())) }
    else { continue }
    $ranges += [pscustomobject]@{ First = $r[0]; Last = $r[1]; Group = $b.BoundaryGroup }
}
$rows = @()
foreach ($s in (Import-Csv -LiteralPath $SubnetListPath)) {
    $r = Get-CidrRange $s.Cidr
    $hit = @($ranges | Where-Object { $_.First -le $r[0] -and $_.Last -ge $r[1] })
    $ok = $hit.Count -gt 0
    $detail = '拠点 {0} 网段 {1}：{2}' -f $s.Site, $s.Cidr, $(if ($ok) { '覆盖于边界组 ' + (($hit | ForEach-Object { $_.Group }) -join '/') } else { '未被任何边界覆盖' })
    $rows += New-EvidenceRow -Id "$GateId-03" -Requirement '边界组覆盖目标全部网段' -Content $detail `
        -Method '拠点网段清单与边界导出做差集' -Criteria '差集为空' -Result $(if ($ok) { '通过' } else { '不通过' })
    Write-StepLog -Message $detail -Level $(if ($ok) { 'INFO' } else { 'WARN' }) -StepId $GateId -LogPath $LogPath -WhatIf:$WhatIfPreference
}
Export-AuditCsv -InputObject $rows -Path $OutputPath -WhatIf:$WhatIfPreference
