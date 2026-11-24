param(
    [string]$GrafanaHome = (Join-Path $env:ProgramFiles 'GrafanaLabs\grafana'),
    [ValidateRange(1024, 65535)]
    [int]$Port = 3300
)

$ErrorActionPreference = 'Stop'
$grafanaExe = Join-Path $GrafanaHome 'bin\grafana.exe'
if (-not (Test-Path -LiteralPath $grafanaExe -PathType Leaf)) {
    throw "Grafana executable not found: $grafanaExe. Set -GrafanaHome to the installation directory."
}
$GrafanaHome = (Resolve-Path -LiteralPath $GrafanaHome).Path
$runtimePath = Join-Path $PSScriptRoot '.local'
$logPath = Join-Path $runtimePath 'logs'
$settings = @{
    GF_PATHS_DATA = $runtimePath
    GF_PATHS_LOGS = $logPath
    GF_PATHS_PLUGINS = Join-Path $runtimePath 'plugins'
    GF_PATHS_PROVISIONING = Join-Path $PSScriptRoot 'provisioning'
    GF_SERVER_HTTP_ADDR = '127.0.0.1'
    GF_SERVER_HTTP_PORT = [string]$Port
    SCADA_GRAFANA_DASHBOARDS = Join-Path $PSScriptRoot 'dashboards'
}
$originalSettings = @{}

try {
    foreach ($key in $settings.Keys) {
        $originalSettings[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $settings[$key], 'Process')
    }

    Write-Host "Cellect SCADA: http://127.0.0.1:$Port/d/cellect-scada-demo"
    & $grafanaExe server --homepath $GrafanaHome --config (Join-Path $PSScriptRoot 'grafana.ini') "cfg:default.paths.logs=$logPath"
    if ($LASTEXITCODE -ne 0) {
        throw "Grafana exited with code $LASTEXITCODE. Check the console and $logPath."
    }
} finally {
    foreach ($key in $originalSettings.Keys) {
        [Environment]::SetEnvironmentVariable($key, $originalSettings[$key], 'Process')
    }
}
