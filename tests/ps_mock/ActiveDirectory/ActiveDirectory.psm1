# 测试替身：只模拟 ringi-kit 脚本用到的 cmdlet 与属性，不连接任何目录服务。
function New-MockSid([string]$v) { [pscustomobject]@{ Value = $v } }

function Get-ADForest {
    param([string]$Server, $Credential)
    [pscustomobject]@{ Name = 'mock-forest'; Domains = @('a.mock', 'b.mock'); ForestMode = 'Windows2016Forest' }
}

function Get-ADDomain {
    param([string]$Identity, [string]$Server, $Credential)
    [pscustomobject]@{ DNSRoot = $Identity; DomainMode = 'Windows2016Domain'; PDCEmulator = "dc1.$Identity" }
}

function Get-ADDomainController {
    param($Filter, [string]$Server)
    @([pscustomobject]@{ Name = 'dc1' }, [pscustomobject]@{ Name = 'dc2' })
}

function Get-ADUser {
    param($Filter, [string]$SearchBase, [string]$Server, [string[]]$Properties)
    if ($Server -eq 'src') {
        @(
            [pscustomobject]@{ SamAccountName = 'u1'; SID = (New-MockSid 'S-1-5-21-9-1001'); employeeID = 'E1'; sIDHistory = @(); userPrincipalName = 'u1@src' },
            [pscustomobject]@{ SamAccountName = 'u2'; SID = (New-MockSid 'S-1-5-21-9-1002'); employeeID = 'E2'; sIDHistory = @(); userPrincipalName = 'u2@src' },
            [pscustomobject]@{ SamAccountName = 'u3'; SID = (New-MockSid 'S-1-5-21-9-1003'); employeeID = 'E3'; sIDHistory = @(); userPrincipalName = 'u3@src' }
        )
    } else {
        @(
            [pscustomobject]@{ SamAccountName = 'n1'; SID = (New-MockSid 'S-1-5-21-8-2001'); employeeID = 'E1'; sIDHistory = @(New-MockSid 'S-1-5-21-9-1001'); userPrincipalName = 'n1@tgt' },
            [pscustomobject]@{ SamAccountName = 'n2'; SID = (New-MockSid 'S-1-5-21-8-2002'); employeeID = 'E2'; sIDHistory = @(); userPrincipalName = 'n2@tgt' }
        )
    }
}

function Get-ADObject {
    param([string]$LDAPFilter, [string]$SearchBase, [string]$Server, [string[]]$Properties)
    @(
        [pscustomobject]@{ Name = 'n1'; ObjectClass = 'user'; sIDHistory = @(New-MockSid 'S-1-5-21-9-1001') },
        [pscustomobject]@{ Name = 'g1'; ObjectClass = 'group'; sIDHistory = @((New-MockSid 'S-1-5-21-9-3001'), (New-MockSid 'S-1-5-21-9-3002')) }
    )
}

Export-ModuleMember -Function Get-ADForest, Get-ADDomain, Get-ADDomainController, Get-ADUser, Get-ADObject
