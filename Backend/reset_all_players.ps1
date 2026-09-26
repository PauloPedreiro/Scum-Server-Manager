# PowerShell Script to reset all players and shop orders directly using native Windows winsqlite3.dll
$ErrorActionPreference = "Stop"

# Title
Write-Host "==================================================" -ForegroundColor Yellow
Write-Host "   RESETADOR GERAL DE CADASTRO E PEDIDOS - SSM    " -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Yellow
Write-Host "Este script ira desvincular TODOS os jogadores do Discord,"
Write-Host "limpar todos os tokens e apagar todos os pedidos da loja."
Write-Host "==================================================`n"

# Confirmation
$confirm = Read-Host "Tem certeza que deseja resetar TODOS os registros? (S/N)"
if ($confirm.ToUpper() -ne "S" -and $confirm.ToUpper() -ne "SIM") {
    Write-Host "Operacao cancelada." -ForegroundColor Red
    Exit
}

# Resolve Database Path
$dbPath = Join-Path $PSScriptRoot "data\SSM.db"
if (-not (Test-Path $dbPath)) {
    Write-Host "Erro: Banco de dados nao encontrado em: $dbPath" -ForegroundColor Red
    Exit
}

Write-Host "Conectando ao banco de dados: $dbPath..." -ForegroundColor Cyan

# C# Wrapper for winsqlite3.dll
$Source = @"
using System;
using System.Runtime.InteropServices;

public class WinSqlite {
    [DllImport("winsqlite3.dll", EntryPoint = "sqlite3_open", CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Ansi)]
    public static extern int Open(string filename, out IntPtr db);

    [DllImport("winsqlite3.dll", EntryPoint = "sqlite3_exec", CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Ansi)]
    public static extern int Exec(IntPtr db, string sql, IntPtr callback, IntPtr arg, out IntPtr errmsg);

    [DllImport("winsqlite3.dll", EntryPoint = "sqlite3_close", CallingConvention = CallingConvention.Cdecl)]
    public static extern int Close(IntPtr db);
}
"@

# Load the Type (ignore error if already loaded in this session)
try {
    Add-Type -TypeDefinition $Source
} catch {
    # Type already exists in this PowerShell session
}

# Connect
$db = [IntPtr]::Zero
$res = [WinSqlite]::Open($dbPath, [ref]$db)

if ($res -ne 0) {
    Write-Host "Erro ao abrir o banco de dados. Codigo: $res" -ForegroundColor Red
    Exit
}

try {
    $errmsg = [IntPtr]::Zero
    
    # Executar SQL Statements
    $sql = @"
    UPDATE players SET discord_user_id = NULL, discord_linked_at = NULL;
    DELETE FROM discord_link_tokens;
    DELETE FROM shop_order_item;
    DELETE FROM shop_delivery_item;
    DELETE FROM shop_order;
    UPDATE wallet SET balance = 5000;
"@

    Write-Host "Executando reset no banco de dados..." -ForegroundColor Cyan
    $execRes = [WinSqlite]::Exec($db, $sql, [IntPtr]::Zero, [IntPtr]::Zero, [ref]$errmsg)
    
    if ($execRes -eq 0) {
        Write-Host "`n>>> TODOS os registros foram resetados com sucesso!" -ForegroundColor Green
        Write-Host "  - Jogadores desvinculados do Discord" -ForegroundColor Green
        Write-Host "  - Tokens de vinculacao deletados" -ForegroundColor Green
        Write-Host "  - Historico de pedidos/entregas da loja removidos" -ForegroundColor Green
        Write-Host "  - Carteiras resetadas para R$ 5000" -ForegroundColor Green
        Write-Host "`nPronto! Todos os jogadores podem se registrar novamente e o Welcome Pack sera entregue do zero." -ForegroundColor Green
    } else {
        Write-Host "Erro ao executar comandos SQL. Codigo: $execRes" -ForegroundColor Red
        if ($errmsg -ne [IntPtr]::Zero) {
            $msg = [Marshal]::PtrToStringAnsi($errmsg)
            Write-Host "Detalhe do erro: $msg" -ForegroundColor Red
        }
    }
} finally {
    # Close
    [WinSqlite]::Close($db) | Out-Null
}
