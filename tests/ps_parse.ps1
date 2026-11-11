param([string]$Root)
$fail = 0
Get-ChildItem -LiteralPath $Root -Recurse -File -Include *.ps1,*.psm1 | ForEach-Object {
    $tokens = $null; $errs = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errs) | Out-Null
    $req = (Get-Content -LiteralPath $_.FullName -TotalCount 1 -Encoding UTF8) -match '^#Requires -Version 5\.1'
    if ($errs.Count -gt 0 -or -not $req) { $fail++; "FAIL $($_.Name) errors=$($errs.Count) requires=$req"; $errs | ForEach-Object { "  $($_.Message) @ $($_.Extent.StartLineNumber)" } }
    else { "OK   $($_.Name)" }
}
"PSVersion=$($PSVersionTable.PSVersion) failures=$fail"
exit $fail
