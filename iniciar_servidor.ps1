# Script para iniciar o servidor de forma visivel
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Iniciando Servidor de Comparacao" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Atualiza PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Define caminho do Python
$pythonPath = "C:\Users\pc123\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $pythonPath)) {
    # Tenta encontrar Python no PATH
    $pythonPath = "python"
}

# Verifica Python
Write-Host "Verificando Python..." -ForegroundColor Yellow
try {
    $version = & $pythonPath --version 2>&1
    Write-Host "  [OK] $version" -ForegroundColor Green
} catch {
    Write-Host "  [ERRO] Python nao encontrado!" -ForegroundColor Red
    Write-Host "  Execute: .\configurar_path.ps1" -ForegroundColor Yellow
    Write-Host "  Ou feche e reabra o PowerShell" -ForegroundColor Yellow
    exit 1
}

# Verifica se porta 8000 esta em uso
Write-Host ""
Write-Host "Verificando porta 8000..." -ForegroundColor Yellow
$portInUse = netstat -ano | findstr ":8000" | findstr "LISTENING"
if ($portInUse) {
    Write-Host "  [AVISO] Porta 8000 ja esta em uso!" -ForegroundColor Yellow
    Write-Host "  Parando processos Python na porta 8000..." -ForegroundColor Yellow
    
    # Para todos os processos Python primeiro
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    # Verifica novamente se ainda esta em uso
    $portStillInUse = netstat -ano | findstr ":8000" | findstr "LISTENING"
    if ($portStillInUse) {
        # Tenta parar pelo PID especifico
        $processes = netstat -ano | findstr ":8000" | findstr "LISTENING"
        if ($processes) {
            $processId = ($processes -split '\s+')[-1]
            Write-Host "  Encontrado processo PID: $processId" -ForegroundColor Yellow
            $choice = Read-Host "  Deseja finalizar este processo? (S/N)"
            if ($choice -eq "S" -or $choice -eq "s") {
                taskkill /F /PID $processId 2>$null
                Start-Sleep -Seconds 2
                Write-Host "  Processo finalizado!" -ForegroundColor Green
            } else {
                Write-Host "  Mantendo processo em execucao. O servidor pode nao iniciar." -ForegroundColor Yellow
                exit 1
            }
        }
    } else {
        Write-Host "  [OK] Porta 8000 liberada!" -ForegroundColor Green
    }
} else {
    Write-Host "  [OK] Porta 8000 disponivel" -ForegroundColor Green
}

# Navega para a pasta
Set-Location "C:\Users\pc123\Pictures\web scraipt"

Write-Host ""
Write-Host "Iniciando servidor..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SERVIDOR INICIADO!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Acesse:" -ForegroundColor Cyan
Write-Host "  - Documentacao: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Health Check: http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "Para parar o servidor, pressione Ctrl+C" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Inicia o servidor
& $pythonPath app.py

