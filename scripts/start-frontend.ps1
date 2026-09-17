# =============================================================================
# 供应链智能决策系统 - 前端自动重启启动脚本
#
# 用法（任选其一）:
#   1. 双击运行 start-frontend.bat
#   2. PowerShell: .\scripts\start-frontend.ps1
#
# 功能:
#   - 启动 Vite 开发服务器（端口 5173）
#   - 进程退出后自动重新拉起（无限重试，间隔 5 秒）
#   - Ctrl+C 可整体退出
#   - 日志同时输出到控制台和 logs\frontend_YYYYMMDD_HHMMSS.log
# =============================================================================

$ErrorActionPreference = "Continue"

# 切到项目根目录，前端代码在 frontend\ 下
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"
Set-Location $FrontendDir

$Port = 5173
$LogDir = Join-Path $ProjectRoot "logs"
$RestartDelaySeconds = 5

$NodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
# 直接以 node 跑 vite 入口，绕开 npm.ps1 执行策略与全局/本地 npm 差异
$ViteEntry = Join-Path $FrontendDir "node_modules\vite\bin\vite.js"

if (-not $NodeExe) {
    Write-Host "[错误] 未找到 node，请先安装 Node.js" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

if (-not (Test-Path $ViteEntry)) {
    Write-Host "[错误] 未找到 vite（$ViteEntry），请先安装依赖:" -ForegroundColor Red
    Write-Host "       cd frontend && npm install" -ForegroundColor Yellow
    Read-Host "按回车退出"
    exit 1
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "frontend_$Timestamp.log"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 供应链智能决策系统 - 前端守护启动" -ForegroundColor Cyan
Write-Host " 目录: $FrontendDir" -ForegroundColor Gray
Write-Host " 端口: $Port" -ForegroundColor Gray
Write-Host " 日志: $LogFile" -ForegroundColor Gray
Write-Host " Ctrl+C 退出守护（Vite 进程会一并终止）" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan

# 停掉可能残留的旧进程（占用目标端口的）
try {
    $stale = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $stale) {
        Write-Host "[预检] 端口 $Port 被进程 $($conn.OwningProcess) 占用，尝试结束..." -ForegroundColor Yellow
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
} catch { }

$Round = 0
while ($true) {
    $Round++
    $StartTime = Get-Date
    Write-Host ""
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 第 $Round 次启动前端..." -ForegroundColor Green

    # 用 node 直接跑 vite 入口；--strictPort 保证端口被占时报错而非换端口
    & $NodeExe $ViteEntry --port $Port --strictPort 2>&1 | ForEach-Object {
        $_.ToString()
    } | Tee-Object -FilePath $LogFile -Append

    $ExitCode = $LASTEXITCODE
    $RunSeconds = [int]((Get-Date) - $StartTime).TotalSeconds

    Write-Host ""
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 前端已退出（运行 ${RunSeconds}s, exit=$ExitCode）" -ForegroundColor Yellow

    if ($RunSeconds -lt 5) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 启动后 5 秒内即退出，${RestartDelaySeconds} 秒后重试（若是代码/依赖错误请按 Ctrl+C 退出后检查日志）" -ForegroundColor Red
    } else {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ${RestartDelaySeconds} 秒后自动重启..." -ForegroundColor Yellow
    }
    Start-Sleep -Seconds $RestartDelaySeconds
}
