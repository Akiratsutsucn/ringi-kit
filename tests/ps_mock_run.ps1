param([string]$Kit, [string]$Out)
# 用测试替身模块验证依赖 ActiveDirectory / ConfigurationManager / ADSync 的脚本逻辑。
# 这验证的是脚本自身的逻辑、参数与 CSV 输出，不等于在真实客户环境实测。
$ErrorActionPreference = 'Stop'
# 共享根路径含方括号，PowerShell 按名称导入模块时会把方括号当通配符；先把替身模块复制到不含方括号的临时目录。
$mockRoot = Join-Path ([IO.Path]::GetTempPath()) ("ringi-kit-ps-mock-" + $PID)
if (Test-Path -LiteralPath $mockRoot) { Remove-Item -LiteralPath $mockRoot -Recurse -Force }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ps_mock') -Destination $mockRoot -Recurse
$env:PSModulePath = $mockRoot + [IO.Path]::PathSeparator + $env:PSModulePath
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$script:fail = 0
$expectedCols = '验收ID,对应需求,验收内容,验收方法,判定基准,证据形式,客户确认人,结果'

function Get-Results($rows) { ($rows | ForEach-Object { $_.'结果' }) -join ',' }

function Invoke-Check([string]$Name, [scriptblock]$Run, [scriptblock]$Assert) {
    try {
        $csv = Join-Path $Out "$Name.csv"
        & $Run $csv | Out-Null
        $rows = @(Import-Csv -LiteralPath $csv -Encoding UTF8)
        $cols = ($rows[0].PSObject.Properties.Name) -join ','
        if ($cols -ne $expectedCols) { throw "列名不符：$cols" }
        $msg = & $Assert $rows
        if ($msg) { throw $msg }
        "OK   $Name（$($rows.Count) 行）"
    } catch {
        $script:fail++
        "FAIL $Name：$($_.Exception.Message)"
    }
}

Invoke-Check 'forest-inventory' { param($o) & "$Kit\ad\Get-ForestInventory.ps1" -Server src -OutputPath $o } {
    param($r) if ($r.Count -ne 2 -or $r[0].'验收内容' -notmatch '域控 2 台') { "期望 2 个域、各 2 台域控：$($r.'验收内容')" }
}
Invoke-Check 'account-mapping' {
    param($o) & "$Kit\ad\Export-AccountMapping.ps1" -SourceServer src -TargetServer tgt -SourceSearchBase 'OU=S' `
        -TargetSearchBase 'OU=T' -MatchAttribute employeeID -OutputPath $o
} {
    param($r) $v = Get-Results $r
    if ($v -ne '通过,不通过,不通过') { "期望 通过,不通过,不通过（u2 未携带历史 SID，u3 未映射），实际 $v" }
}
Invoke-Check 'sidhistory-audit' { param($o) & "$Kit\ad\Get-SIDHistoryAudit.ps1" -Server tgt -SearchBase 'OU=T' -OutputPath $o } {
    param($r) if ($r.Count -ne 2 -or $r[1].'验收内容' -notmatch '历史 SID 2 个') { "期望 2 个对象且 g1 携带 2 个：$($r.'验收内容')" }
}

$exp = Join-Path $Out 'expected.csv'
Set-Content -LiteralPath $exp -Encoding UTF8 -Value @('CollectionId,ExpectedCount,Wave', 'TST00001,300,W-01', 'TST00002,750,W-02')
Invoke-Check 'collection-members' {
    param($o) & "$Kit\sccm\Export-CollectionMembers.ps1" -SiteCode TST -ExpectedCountPath $exp -TolerancePercent 2 -OutputPath $o
} {
    param($r) $v = Get-Results $r
    if ($v -ne '通过,不通过') { "期望 通过,不通过（700/750 差 6.7%），实际 $v" }
}

$targets = Join-Path $Out 'targets.csv'
Set-Content -LiteralPath $targets -Encoding UTF8 -Value @('ComputerName', 'localhost')
Invoke-Check 'client-push-readiness' {
    param($o) & "$Kit\sccm\Get-ClientPushReadiness.ps1" -ComputerListPath $targets -Port 1 -OutputPath $o
} {
    param($r) $v = Get-Results $r
    if ($v -ne '不通过') { "端口 1 不可达，期望 不通过，实际 $v" }
}

Invoke-Check 'sync-status' { param($o) & "$Kit\entraconnect\Get-SyncStatus.ps1" -OutputPath $o -RecentRuns 3 } {
    param($r) $v = Get-Results $r
    if ($v -ne '通过,通过,不通过') { "期望 通过,通过,不通过（c2 有失败运行），实际 $v" }
}

$ep = Join-Path $Out 'outbound.csv'
Set-Content -LiteralPath $ep -Encoding UTF8 -Value @('域名,用途,是否经代理', 'localhost,本机（不可达示例）,否')
Invoke-Check 'outbound-endpoints' {
    param($o) & "$Kit\entraconnect\Test-OutboundEndpoints.ps1" -EndpointListPath $ep -TimeoutMs 2000 -OutputPath $o
} {
    param($r) $v = Get-Results $r
    if ($v -ne '不通过') { "本机 443 未监听，期望 不通过，实际 $v" }
}

Remove-Item -LiteralPath $mockRoot -Recurse -Force -ErrorAction SilentlyContinue
"MOCK PSVersion=$($PSVersionTable.PSVersion) failures=$script:fail"
exit $script:fail
