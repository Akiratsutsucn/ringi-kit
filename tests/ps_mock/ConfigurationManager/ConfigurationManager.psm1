# 测试替身：站点驱动器 TST: 映射到临时目录；集合成员数固定。
if (-not (Get-PSDrive -Name TST -ErrorAction SilentlyContinue)) {
    New-PSDrive -Name TST -PSProvider FileSystem -Root ([System.IO.Path]::GetTempPath()) -Scope Global | Out-Null
}

function Get-CMCollectionMember {
    param([string]$CollectionId)
    $counts = @{ 'TST00001' = 300; 'TST00002' = 700 }
    $n = if ($counts.ContainsKey($CollectionId)) { $counts[$CollectionId] } else { 0 }
    if ($n -eq 0) { return @() }
    1..$n | ForEach-Object { [pscustomobject]@{ Name = "PC$_" } }
}

Export-ModuleMember -Function Get-CMCollectionMember
