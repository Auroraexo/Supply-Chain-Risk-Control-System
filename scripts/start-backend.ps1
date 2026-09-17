# =============================================================================
# 供应链智能决策系统 - 后端自动重启启动脚本
#
# 用法（任选其一）:
#   1. 双击运行 start-backend.bat
#   2. PowerShell: .\scripts\start-backend.ps1
#
# 功能:
#   - 启动 uvicorn 后端（端口 8000）
#   - 进程退出后自动重新拉起（无限重试，间隔 5 秒）
#   - Ctrl+C 可整体退出
#   - 日志同时输出到控制台和 logs\backend_YYYYMMDD_HHMMSS.log
# =============================================================================

$ErrorActionPreference = "Continue"

# 切到项目根目录（脚本位于 scripts\ 下）
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Port = 8000
$Uvicorn = Join-Path $ProjectRoot ".venv\Scripts\uvicorn.exe"
$LogDir = Join-Path $ProjectRoot "logs"
$RestartDelaySeconds = 5

if (-not (Test-Path $Uvicorn)) {
    Write-Host "[错误] 未找到虚拟环境: $Uvicorn" -ForegroundColor Red
    Write-Host "       请先在项目根目录执行: uv sync --all-extras" -ForegroundColor Yellow
    Read-Host "按回车退出"
    exit 1
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "backend_$Timestamp.log"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 供应链智能决策系统 - 后端守护启动" -ForegroundColor Cyan
Write-Host " 项目: $ProjectRoot" -ForegroundColor Gray
Write-Host " 端口: $Port" -ForegroundColor Gray
Write-Host " 日志: $LogFile" -ForegroundColor Gray
Write-Host " Ctrl+C 退出守护（后端进程会一并终止）" -ForegroundColor Gray
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
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 第 $Round 次启动后端..." -ForegroundColor Green

    # 启动后端：输出同时进日志文件和控制台
    & $Uvicorn app.main:app --host 0.0.0.0 --port $Port 2>&1 | ForEach-Object {
        $_.ToString()
    } | Tee-Object -FilePath $LogFile -Append

    $ExitCode = $LASTEXITCODE
    $RunSeconds = [int]((Get-Date) - $StartTime).TotalSeconds

    # Ctrl+C 触发管道中断时会走到这里，给用户 3 秒决定是否真的退出
    Write-Host ""
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 后端已退出（运行 ${RunSeconds}s, exit=$ExitCode）" -ForegroundColor Yellow

    if ($RunSeconds -lt 5) {
        # 启动即崩：可能是端口占用、代码错误等，稍等更久避免死循环刷屏
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 启动后 5 秒内即退出，${RestartDelaySeconds} 秒后重试（若是代码错误请按 Ctrl+C 退出后检查日志）" -ForegroundColor Red
    } else {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ${RestartDelaySeconds} 秒后自动重启..." -ForegroundColor Yellow
    }
    Start-Sleep -Seconds $RestartDelaySeconds
}
