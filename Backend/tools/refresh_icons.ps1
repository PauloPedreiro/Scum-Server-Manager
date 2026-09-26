# Script PowerShell para limpar cache de ícones do Windows
# Execute como Administrador para melhor resultado

Write-Host "Limpando cache de ícones do Windows..." -ForegroundColor Yellow
Write-Host ""

# Parar o processo explorer.exe temporariamente
Write-Host "Parando explorer.exe..." -ForegroundColor Cyan
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Limpar cache de ícones
Write-Host "Limpando arquivos de cache..." -ForegroundColor Cyan
$cachePaths = @(
    "$env:LOCALAPPDATA\IconCache.db",
    "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\iconcache*.db",
    "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\thumbcache*.db"
)

foreach ($path in $cachePaths) {
    if (Test-Path $path) {
        Remove-Item $path -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "  Removido: $path" -ForegroundColor Green
    }
}

# Reiniciar explorer.exe
Write-Host ""
Write-Host "Reiniciando explorer.exe..." -ForegroundColor Cyan
Start-Process explorer.exe

Write-Host ""
Write-Host "Cache de ícones limpo!" -ForegroundColor Green
Write-Host ""
Write-Host "NOTA: Se os ícones ainda não aparecerem corretamente:" -ForegroundColor Yellow
Write-Host "  1. Feche e reabra o explorador de arquivos" -ForegroundColor White
Write-Host "  2. Reinicie o computador" -ForegroundColor White
Write-Host "  3. Verifique se o arquivo .ico tem múltiplos tamanhos (16x16, 32x32, 48x48, 256x256)" -ForegroundColor White
Write-Host ""
Write-Host "Pressione qualquer tecla para continuar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

