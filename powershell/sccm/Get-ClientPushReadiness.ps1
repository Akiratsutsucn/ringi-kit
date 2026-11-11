#Requires -Version 5.1
<#
.SYNOPSIS
  客户端推送前置检查（G-A-01：管理共享可访问；RPC 与共享通道已放通）。只读。
.PARAMETER ComputerListPath
  目标终端清单 CSV，须含列 ComputerName。
.PARAMETER Port
  需探测的端口清单（按官方端口清单核对后传入）。
.PARAMETER OutputPath
  证据 CSV 输出路径（建议 evidence/G-A-01-01.csv）。
.EXAMPLE
  .\Get-ClientPushReadiness.ps1 -ComputerListPath .\targets.csv -Port 135,445 -OutputPath .\evidence\G-A-01-01.csv -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ComputerListPath,
    [Parameter(Mandatory = $true)][int[]]$Port,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$GateId = 'G-A-01',
    [string]$LogPath
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\common\RingiKit.Common.psm1') -Force

if (-not (Test-Path -LiteralPath $ComputerListPath)) { throw "目标清单不存在：$ComputerListPath" }
$targets = Import-Csv -LiteralPath $ComputerListPath
if (-not ($targets | Get-Member -Name ComputerName)) { throw '目标清单缺少 ComputerName 列' }

$rows = @()
foreach ($t in $targets) {
    $name = $t.ComputerName
    $share = Test-Path -LiteralPath ('\{0}\ADMIN$' -f $name) -ErrorAction SilentlyContinue
    $closed = @($Port | Where-Object { -not (Test-TcpPort -HostName $name -Port $_) })
    $ok = $share -and ($closed.Count -eq 0)
    $detail = '{0}：管理共享={1}；未通端口={2}' -f $name, $(if ($share) { '可访问' } else { '不可访问' }), $(if ($closed.Count) { $closed -join '/' } else { '无' })
    $rows += New-EvidenceRow -Id "$GateId-01" -Requirement '管理共享可访问；RPC 与共享通道已放通' -Content $detail `
        -Method '从执行端访问管理共享并探测指定端口' -Criteria '管理共享可访问且全部指定端口可达' -Result $(if ($ok) { '通过' } else { '不通过' })
    Write-StepLog -Message $detail -Level $(if ($ok) { 'INFO' } else { 'WARN' }) -StepId $GateId -LogPath $LogPath -WhatIf:$WhatIfPreference
}
if ($rows.Count -eq 0) { throw '目标清单为空' }
Export-AuditCsv -InputObject $rows -Path $OutputPath -WhatIf:$WhatIfPreference
