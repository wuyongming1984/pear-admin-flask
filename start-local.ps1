$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vite = Join-Path $projectRoot 'frontend-desktop\node_modules\vite\bin\vite.js'
$logRoot = Join-Path $projectRoot 'instance'
if (!(Test-Path -LiteralPath $python)) { throw 'Missing .venv Python.' }
if (!(Test-Path -LiteralPath $vite)) { throw 'Run pnpm install --frozen-lockfile in frontend-desktop first.' }
$node = (Get-Command node.exe -ErrorAction Stop).Source

function Start-LocalService($name, $port, $executable, $arguments, $directory, $marker) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        $running = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
        if ($running.CommandLine -notlike "*$marker*") {
            throw "Port $port is occupied by another process."
        }
        Write-Host "$name already running on port $port."
        return
    }
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $directory -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot "local-$name.stdout.log") -RedirectStandardError (Join-Path $logRoot "local-$name.stderr.log") -PassThru
    $process.Id | Set-Content -LiteralPath (Join-Path $logRoot "local-$name.pid")
    $deadline = (Get-Date).AddSeconds(40)
    do {
        Start-Sleep -Milliseconds 500
        if ($process.HasExited) { throw "$name exited. See instance/local-$name.stderr.log" }
        $ready = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    } until ($ready -or (Get-Date) -gt $deadline)
    if (!$ready) { throw "$name did not start within 40 seconds. See instance logs." }
}

Start-LocalService 'backend' 5050 $python 'scripts/run_local.py' $projectRoot 'run_local.py'
Start-LocalService 'desktop' 5174 $node 'node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174 --strictPort' (Join-Path $projectRoot 'frontend-desktop') 'vite/bin/vite.js'
Write-Host 'Development: http://127.0.0.1:5174/static/desktop/'
Write-Host 'Built desktop: http://127.0.0.1:5050/pc/'
Write-Host 'Legacy: http://127.0.0.1:5050/legacy/'
Write-Host 'Mobile: http://127.0.0.1:5050/m/'
