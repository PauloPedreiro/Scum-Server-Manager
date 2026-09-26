# Script para resetar senha do admin no SSM 3.0 para 'admin123'
$ErrorActionPreference = "Stop"

$code = @"
using System;
using System.Runtime.InteropServices;

public class WinSqlite {
    [DllImport("winsqlite3.dll", EntryPoint = "sqlite3_open", CallingConvention = CallingConvention.Cdecl)]
    public static extern int Open(string filename, out IntPtr db);

    [DllImport("winsqlite3.dll", EntryPoint = "sqlite3_close", CallingConvention = CallingConvention.Cdecl)]
    public static extern int Close(IntPtr db);

    [DllImport("winsqlite3.dll", EntryPoint = "sqlite3_exec", CallingConvention = CallingConvention.Cdecl)]
    public static extern int Exec(IntPtr db, string sql, IntPtr callback, IntPtr arg, out IntPtr errmsg);
}
"@

# Compilar a definição C# para SQLite nativo do Windows
Add-Type -TypeDefinition $code

# Tenta achar o banco na pasta atual (se rodar dentro de /data)
$dbPath = Join-Path $PSScriptRoot "SSM.db"
if (-not (Test-Path $dbPath)) {
    # Tenta achar na subpasta data (se rodar na raiz)
    $dbPath = Join-Path $PSScriptRoot "data\SSM.db"
}

if (-not (Test-Path $dbPath)) {
    Write-Host "[ERRO] Banco de dados SSM.db nao encontrado!" -ForegroundColor Red
    Write-Host "Caminhos testados:" -ForegroundColor Yellow
    Write-Host "  - $(Join-Path $PSScriptRoot 'SSM.db')" -ForegroundColor Yellow
    Write-Host "  - $(Join-Path $PSScriptRoot 'data\SSM.db')" -ForegroundColor Yellow
    exit 1
}

$db = [IntPtr]::Zero
$dbFullPath = (Get-Item $dbPath).FullName

$openResult = [WinSqlite]::Open($dbFullPath, [ref]$db)
if ($openResult -ne 0) {
    Write-Host "[ERRO] Falha ao abrir o banco de dados. Verifique se o Panel SSM esta fechado." -ForegroundColor Red
    exit 1
}

# Hashing de 'admin123' gerado com bcrypt (rounds=12)
$hash = '$2b$12$tCau17QlxTKQ1MwwpoVf0e.yv7Hz9368RtZbtWF6m3SZvADNSQwbm'
$sql = "UPDATE frontend_users SET password_hash = '$hash', password_changed = 1, role = 'admin', is_active = 1 WHERE username = 'admin';"

$errmsg = [IntPtr]::Zero
$execResult = [WinSqlite]::Exec($db, $sql, [IntPtr]::Zero, [IntPtr]::Zero, [ref]$errmsg)

if ($execResult -eq 0) {
    Write-Host "[OK] Senha do admin redefinida com sucesso para 'admin123'!" -ForegroundColor Green
    Write-Host "Usuario: admin" -ForegroundColor White
    Write-Host "Senha: admin123" -ForegroundColor White
} else {
    Write-Host "[ERRO] Erro ao rodar comando no banco: $execResult" -ForegroundColor Red
}

[WinSqlite]::Close($db) | Out-Null
