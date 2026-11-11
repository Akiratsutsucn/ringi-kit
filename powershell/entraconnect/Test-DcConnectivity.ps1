#Requires -Version 5.1
<#
.SYNOPSIS
  从同步服务器向每台域控做端口端到端探测（G-C-01：云主机到域控的目录服务连通正常）。只读。
.PARAMETER DomainController
  域控名称清单（由调用方传入）。
.PARAMETER Port
  需探测的端口清单。按官方端口清单核对后传入，不止 443。
.EXAMPLE
  .\Test-DcConnectivity.ps1 -DomainController <域控1>,<域控2> -Port 53,88,135,389,445,636 -OutputPath .\evidence\G-C-01-01.csv
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string[]]$DomainController,
    [Parameter(Mandatory = $true)][int[]]$Port,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [int]$TimeoutMs = 3000,
    [string]$GateId = 'G-C-01',
    [string]$LogPath
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\common\RingiKit.Common.psm1') -Force

$rows = @()
foreach ($dc in $DomainController) {
    foreach ($p in $Port) {
        $ok = Test-TcpPort -HostName $dc -Port $p -TimeoutMs $TimeoutMs
        $detail = '{0}:{1} {2}' -f $dc, $p, $(if ($ok) { '可达' } else { '不可达' })
        $rows += New-EvidenceRow -Id "$GateId-01" -Requirement '云主机到域控的目录服务连通正常' -Content $detail `
            -Method ('TCP 端到端探测，超时 {0} 毫秒' -f $TimeoutMs) -Criteria '全部指定端口可达' -Result $(if ($ok) { '通过' } else { '不通过' })
        Write-StepLog -Message $detail -Level $(if ($ok) { 'INFO' } else { 'WARN' }) -StepId $GateId -LogPath $LogPath -WhatIf:$WhatIfPreference
    }
}
Export-AuditCsv -InputObject $rows -Path $OutputPath -WhatIf:$WhatIfPreference
