#Requires -Version 5.1
<#
.SYNOPSIS
  ringi-kit 公共函数：日志、前置检查、证据 CSV 导出、TCP 端口探测。
.DESCRIPTION
  兼容 Windows PowerShell 5.1 与 PowerShell 7。所有函数只读目标环境；
  唯一的写操作是把日志与证据 CSV 写到调用方指定的本地路径（支持 -WhatIf）。
  证据 CSV 列名与验收矩阵（02 第 4.5 节 test-matrix）一致。
#>
Set-StrictMode -Version 2.0

$script:EvidenceColumns = @('验收ID', '对应需求', '验收内容', '验收方法', '判定基准', '证据形式', '客户确认人', '结果')

function Write-StepLog {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet('INFO', 'WARN', 'ERROR')][string]$Level = 'INFO',
        [string]$StepId = '-',
        [string]$LogPath
    )
    $line = '{0} [{1}] [{2}] {3}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'), $Level, $StepId, $Message
    Write-Host $line
    if ($LogPath -and $PSCmdlet.ShouldProcess($LogPath, '追加日志')) {
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    }
}

function Test-Prerequisite {
    [CmdletBinding()]
    param(
        [string[]]$Module = @(),
        [string[]]$Command = @()
    )
    $missing = @()
    foreach ($m in $Module) {
        if (-not (Get-Module -ListAvailable -Name $m)) { $missing += "模块 $m" }
    }
    foreach ($c in $Command) {
        if (-not (Get-Command -Name $c -ErrorAction SilentlyContinue)) { $missing += "命令 $c" }
    }
    if ($missing.Count -gt 0) {
        throw ('前置条件不满足：缺少 {0}。请在具备该模块的管理终端上执行。' -f ($missing -join '、'))
    }
    return $true
}

function New-EvidenceRow {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Requirement,
        [Parameter(Mandatory = $true)][string]$Content,
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Criteria,
        [string]$EvidenceForm = 'CSV',
        [string]$Confirmer = '',
        [Parameter(Mandatory = $true)][ValidateSet('通过', '不通过', '无法判定')][string]$Result
    )
    $values = @($Id, $Requirement, $Content, $Method, $Criteria, $EvidenceForm, $Confirmer, $Result)
    $row = [ordered]@{}
    for ($i = 0; $i -lt $script:EvidenceColumns.Count; $i++) { $row[$script:EvidenceColumns[$i]] = $values[$i] }
    return [pscustomobject]$row
}

function Export-AuditCsv {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory = $true)][object[]]$InputObject,
        [Parameter(Mandatory = $true)][string]$Path
    )
    foreach ($col in $script:EvidenceColumns) {
        if (-not ($InputObject[0].PSObject.Properties.Name -contains $col)) {
            throw "证据 CSV 缺少规定列：$col"
        }
    }
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        if ($PSCmdlet.ShouldProcess($dir, '创建证据目录')) { New-Item -ItemType Directory -Path $dir | Out-Null }
    }
    if ($PSCmdlet.ShouldProcess($Path, '写出证据 CSV')) {
        $InputObject | Select-Object -Property $script:EvidenceColumns |
            Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding UTF8
    }
}

function Test-TcpPort {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$HostName,
        [Parameter(Mandatory = $true)][int]$Port,
        [int]$TimeoutMs = 3000
    )
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        $ok = $task.Wait($TimeoutMs) -and $client.Connected
        return [bool]$ok
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

Export-ModuleMember -Function Write-StepLog, Test-Prerequisite, New-EvidenceRow, Export-AuditCsv, Test-TcpPort
