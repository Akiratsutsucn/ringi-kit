param([string]$Kit, [string]$Out)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
Set-Content -LiteralPath (Join-Path $Out 'subnets.csv') -Encoding UTF8 -Value @('Site,Cidr', 'SiteA,10.1.0.0/24', 'SiteB,10.2.0.0/24')
Set-Content -LiteralPath (Join-Path $Out 'boundaries.csv') -Encoding UTF8 -Value @('Type,Value,BoundaryGroup', 'IPSubnet,10.1.0.0/16,BG-A')
$bc = Join-Path $Out 'boundary.csv'
& (Join-Path $Kit 'sccm\Export-BoundaryCoverage.ps1') -SubnetListPath (Join-Path $Out 'subnets.csv') -BoundaryListPath (Join-Path $Out 'boundaries.csv') -OutputPath $bc | Out-Null
$rows = @(Import-Csv -LiteralPath $bc -Encoding UTF8)
if ($rows.Count -ne 2) { throw "期望 2 行，实际 $($rows.Count)" }
if ($rows[0].'结果' -ne '通过' -or $rows[1].'结果' -ne '不通过') { throw '差集判定错误' }
$cols = ($rows[0].PSObject.Properties.Name) -join ','
if ($cols -ne '验收ID,对应需求,验收内容,验收方法,判定基准,证据形式,客户确认人,结果') { throw "列名不符：$cols" }
$w = Join-Path $Out 'whatif.csv'
& (Join-Path $Kit 'entraconnect\Test-DcConnectivity.ps1') -DomainController 'localhost' -Port 1 -TimeoutMs 300 -OutputPath $w -WhatIf | Out-Null
if (Test-Path -LiteralPath $w) { throw '-WhatIf 下不应写出文件' }
"SMOKE OK $($PSVersionTable.PSVersion)"
