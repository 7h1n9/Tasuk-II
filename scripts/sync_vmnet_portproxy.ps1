param(
    [string]$ListenAddress = "192.168.236.1",
    [string]$ConnectAddress = "127.0.0.1",
    [int]$ExternalPortOffset = 10000,
    [int]$PortMin = 18000,
    [int]$PortMax = 18999,
    [int]$IntervalSeconds = 2,
    [switch]$Watch
)

$ErrorActionPreference = "Stop"
$proxyScript = Join-Path $PSScriptRoot "vmnet_tcp_proxy.py"
$firewallRuleName = "CTF-Agent-Range VMnet Portproxy"
$legacyListenAddresses = @("0.0.0.0", "192.168.236.1")

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if ($ExternalPortOffset -le 0) {
    throw "ExternalPortOffset must be greater than zero."
}

if (-not (Test-IsAdministrator)) {
    throw "Run sync_vmnet_portproxy.ps1 from an elevated PowerShell."
}
if (-not (Test-Path -LiteralPath $proxyScript)) {
    throw "Proxy script not found: $proxyScript"
}

$pythonCandidates = @(
    (Get-Command python.exe -ErrorAction SilentlyContinue).Source,
    (Get-ChildItem (Join-Path $env:LOCALAPPDATA "Programs\Python") -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName)
)
$pythonPath = $pythonCandidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($pythonPath)) {
    throw "Python executable was not found."
}

$dockerCandidates = @(
    (Get-Command docker.exe -ErrorAction SilentlyContinue).Source,
    (Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe")
)
$dockerPath = $dockerCandidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($dockerPath)) {
    throw "Docker executable was not found."
}
$logPath = Join-Path $env:TEMP "ctf-agent-range-vmnet-proxy.log"
function Write-ProxyLog([string]$message) {
    Add-Content -LiteralPath $logPath -Value "$(Get-Date -Format o) $message"
}
Write-ProxyLog "Watcher starting. Python=$pythonPath Docker=$dockerPath Listen=$ListenAddress Target=$ConnectAddress"
$mutex = [Threading.Mutex]::new($false, "Global\CtfAgentRangeVmnetPortProxySync")
$ownsMutex = $false
$proxyProcesses = @{}

try {
    try {
        $ownsMutex = $mutex.WaitOne(0)
    } catch [Threading.AbandonedMutexException] {
        $ownsMutex = $true
    }
    if (-not $ownsMutex) {
        exit 0
    }

    function Get-RunningChallengePorts {
        $ports = @{}
        $containerIds = @(& $dockerPath ps --filter "name=cfr-" --format "{{.ID}}")
        foreach ($containerId in $containerIds) {
            if ([string]::IsNullOrWhiteSpace($containerId)) {
                continue
            }

            try {
                $container = @(& $dockerPath inspect $containerId | ConvertFrom-Json)[0]
                $publishedPorts = $container.NetworkSettings.Ports
                if ($null -eq $publishedPorts) {
                    continue
                }

                foreach ($portProperty in $publishedPorts.PSObject.Properties) {
                    foreach ($binding in @($portProperty.Value)) {
                        if ($null -eq $binding -or [string]::IsNullOrWhiteSpace($binding.HostPort)) {
                            continue
                        }
                        $hostPort = 0
                        if ([int]::TryParse([string]$binding.HostPort, [ref]$hostPort) -and
                            $hostPort -ge $PortMin -and $hostPort -le $PortMax) {
                            $ports[$hostPort] = $true
                        }
                    }
                }
            } catch {
                # A container can disappear while it is being inspected.
            }
        }
        return $ports
    }

    function Remove-LegacyPortProxyRules {
        $output = @(netsh interface portproxy show v4tov4 2>$null)
        foreach ($line in $output) {
            if ($line -match '^\s*(?<listen>\d{1,3}(?:\.\d{1,3}){3})\s+(?<listenPort>\d+)\s+(?<connect>\d{1,3}(?:\.\d{1,3}){3})\s+(?<connectPort>\d+)\s*$') {
                $listenPort = [int]$matches.listenPort
                if (($legacyListenAddresses -contains $matches.listen) -and
                    $listenPort -ge $PortMin -and $listenPort -le $PortMax) {
                    & netsh interface portproxy delete v4tov4 listenaddress=$($matches.listen) listenport=$listenPort | Out-Null
                }
            }
        }
    }

    function Stop-ProxyProcess([int]$port) {
        if ($proxyProcesses.ContainsKey($port)) {
            $process = $proxyProcesses[$port]
            if ($null -ne $process -and -not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
            $proxyProcesses.Remove($port)
        }
    }

    function Start-ProxyProcess([int]$port) {
        $arguments = @(
            "-u",
            $proxyScript,
            "--listen-address", $ListenAddress,
            "--listen-port", ($port + $ExternalPortOffset),
            "--target-address", $ConnectAddress,
            "--target-port", $port
        )
        $proxyProcesses[$port] = Start-Process `
            -FilePath $pythonPath `
            -ArgumentList $arguments `
            -WindowStyle Hidden `
            -PassThru
        Write-ProxyLog "Started proxy listenPort=$($port + $ExternalPortOffset) targetPort=$port pid=$($proxyProcesses[$port].Id)"
        Write-Host "Started VMnet proxy: $ListenAddress`:$($port + $ExternalPortOffset) -> $ConnectAddress`:$port"
    }

    function Sync-Proxies {
        $desired = Get-RunningChallengePorts

        foreach ($port in @($proxyProcesses.Keys)) {
            $process = $proxyProcesses[$port]
            if (-not $desired.ContainsKey($port) -or $process.HasExited) {
                Stop-ProxyProcess $port
                Write-Host "Stopped VMnet proxy: $ListenAddress`:$port"
            }
        }

        foreach ($port in @($desired.Keys)) {
            if (-not $proxyProcesses.ContainsKey($port) -or $proxyProcesses[$port].HasExited) {
                Start-ProxyProcess $port
            }
        }
    }

    Remove-LegacyPortProxyRules
    if (-not (Get-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule `
            -DisplayName $firewallRuleName `
            -Direction Inbound `
            -Action Allow `
            -Protocol TCP `
            -LocalAddress $ListenAddress `
            -LocalPort "$(($PortMin + $ExternalPortOffset))-$(($PortMax + $ExternalPortOffset))" `
            -Profile Any | Out-Null
    }

    do {
        try {
            Sync-Proxies
        } catch {
            if (-not $Watch) {
                throw
            }
            Write-Warning $_.Exception.Message
        }
        if ($Watch) {
            Start-Sleep -Seconds $IntervalSeconds
        }
    } while ($Watch)
} catch {
    Write-ProxyLog "ERROR: $($_.Exception.Message)"
    throw
} finally {
    foreach ($port in @($proxyProcesses.Keys)) {
        Stop-ProxyProcess $port
    }
    if ($ownsMutex) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
