# 测试替身：两个连接器，其中 c2 最近运行有一次失败。
function Get-ADSyncScheduler {
    [pscustomobject]@{ SyncCycleEnabled = $true; StagingModeEnabled = $false; CurrentlyEffectiveSyncCycleInterval = '00:30:00' }
}

function Get-ADSyncConnector {
    @([pscustomobject]@{ Name = 'corp.mock'; Identifier = 'c1' }, [pscustomobject]@{ Name = 'tenant.mock - AAD'; Identifier = 'c2' })
}

function Get-ADSyncRunProfileResult {
    param([string]$ConnectorId, [int]$NumberRequested)
    if ($ConnectorId -eq 'c1') {
        1..$NumberRequested | ForEach-Object { [pscustomobject]@{ Result = 'success' } }
    } else {
        @([pscustomobject]@{ Result = 'success' }, [pscustomobject]@{ Result = 'stopped-extension-dll-exception' })
    }
}

Export-ModuleMember -Function Get-ADSyncScheduler, Get-ADSyncConnector, Get-ADSyncRunProfileResult
