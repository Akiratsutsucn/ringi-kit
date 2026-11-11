#Requires -Version 5.1
<#
.SYNOPSIS
  按出站清单逐项验证 443 连通（G-C-01：出站 443 目标域名清单已出具）。只读。
.PARAMETER EndpointListPath
  出站清单 CSV，须含列 域名, 用途, 是否经代理（与方案书 1.3 节表格一致，域名按核查锚点 AN-06 核实）。
.PARAMETER ProxyUri
  代理地址（由调用方传入）；清单中「是否经代理=是」的行经此代理访问。
.EXAMPLE
  .\Test-OutboundEndpoints.ps1 -EndpointListPath .\outbound.csv -ProxyUri <代理地址> -OutputPath .\evidence\G-C-01-02.csv
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$EndpointListPath,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$ProxyUri,
    [int]$TimeoutMs = 10000,
    [string]$GateId = 'G-C-01',
    [string]$LogPath
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\common\RingiKit.Common.psm1') -Force

$list = @(Import-Csv -LiteralPath $EndpointListPath -Encoding UTF8)
foreach ($col in @('域名', '用途', '是否经代理')) {
    if (-not ($list | Get-Member -Name $col)) { throw "出站清单缺少列：$col" }
}
$rows = @()
foreach ($e in $list) {
    $hostName = $e.'域名'.TrimStart('*', '.')
    $status = '失败'
    try {
        $req = [System.Net.HttpWebRequest]::Create("https://$hostName/")
        $req.Method = 'HEAD'
        $req.Timeout = $TimeoutMs
        if ($e.'是否经代理' -eq '是') {
            if (-not $ProxyUri) { throw '清单要求经代理，但未传入 -ProxyUri' }
            $req.Proxy = New-Object System.Net.WebProxy($ProxyUri)
        }
        $resp = $req.GetResponse(); $status = '可达'; $resp.Close()
    } catch [System.Net.WebException] {
        if ($_.Exception.Response) { $status = '可达（HTTP 错误码视为连通）' } else { $status = '失败：' + $_.Exception.Status }
    }
    $ok = $status.StartsWith('可达')
    $detail = '{0}（{1}，经代理={2}）：{3}' -f $e.'域名', $e.'用途', $e.'是否经代理', $status
    $rows += New-EvidenceRow -Id "$GateId-02" -Requirement '出站 443 目标域名清单已出具（域名+用途+是否经代理）' -Content $detail `
        -Method 'HTTPS HEAD 请求，按清单决定是否经代理' -Criteria '清单内全部端点可达' -Result $(if ($ok) { '通过' } else { '不通过' })
    Write-StepLog -Message $detail -Level $(if ($ok) { 'INFO' } else { 'WARN' }) -StepId $GateId -LogPath $LogPath -WhatIf:$WhatIfPreference
}
Export-AuditCsv -InputObject $rows -Path $OutputPath -WhatIf:$WhatIfPreference
