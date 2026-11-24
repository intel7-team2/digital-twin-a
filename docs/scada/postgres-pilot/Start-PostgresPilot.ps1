param(
    [string]$GrafanaHome = (Join-Path $env:ProgramFiles 'GrafanaLabs\grafana')
)

$ErrorActionPreference = 'Stop'
$grafanaExe = Join-Path $GrafanaHome 'bin\grafana.exe'
if (-not (Test-Path -LiteralPath $grafanaExe -PathType Leaf)) {
    throw 'Set -GrafanaHome to the installation directory of Grafana OSS 13.3.1.'
}
$GrafanaHome = (Resolve-Path -LiteralPath $GrafanaHome).Path
$runtimePath = Join-Path ([IO.Path]::GetTempPath()) 'Cellect-2A-Grafana-Postgres'
$logPath = Join-Path $runtimePath 'logs'
$settings = @{
    GF_PATHS_DATA = $runtimePath
    GF_PATHS_LOGS = $logPath
    GF_PATHS_PLUGINS = Join-Path $runtimePath 'plugins'
    GF_PATHS_PROVISIONING = Join-Path $PSScriptRoot 'provisioning'
    GF_SERVER_HTTP_ADDR = '127.0.0.1'
    GF_SERVER_HTTP_PORT = '3301'
    GF_AUTH_LOGIN_COOKIE_NAME = 'cellect_pg_pilot_session'
    CELLECT_PG_DASHBOARDS = Join-Path $PSScriptRoot 'dashboards'
}
$originalSettings = @{}
$originalPassword = [Environment]::GetEnvironmentVariable('CELLECT_PG_PASSWORD', 'Process')

try {
    if ([string]::IsNullOrEmpty($originalPassword)) {
        $password = Read-Host 'Team DB grafana password' -AsSecureString
        if ($password.Length -eq 0) {
            throw 'A database password is required.'
        }
        $env:CELLECT_PG_PASSWORD = [Net.NetworkCredential]::new('', $password).Password
        $password.Dispose()
    }
    foreach ($key in $settings.Keys) {
        $originalSettings[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $settings[$key], 'Process')
    }

    $configPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'grafana.ini'
    Write-Host 'Cellect 2A PostgreSQL pilot: http://127.0.0.1:3301/d/cellect-scada-postgres'
    & $grafanaExe server --homepath $GrafanaHome --config $configPath "cfg:default.paths.logs=$logPath"
    if ($LASTEXITCODE -ne 0) {
        throw "Grafana exited with code $LASTEXITCODE. Check $logPath."
    }
} finally {
    foreach ($key in $originalSettings.Keys) {
        [Environment]::SetEnvironmentVariable($key, $originalSettings[$key], 'Process')
    }
    [Environment]::SetEnvironmentVariable('CELLECT_PG_PASSWORD', $originalPassword, 'Process')
}
