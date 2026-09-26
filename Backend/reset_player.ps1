# PowerShell Script to reset a single player and their orders directly using native Windows winsqlite3.dll
$ErrorActionPreference = "Stop"

# Title
Write-Host "==================================================" -ForegroundColor Yellow
Write-Host "      RESETADOR DE CADASTRO E PEDIDOS - SSM       " -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Yellow

# SteamID argument or input
$steamId = ""
if ($args.Count -gt 0) {
    $steamId = $args[0].Trim()
} else {
    $steamId = Read-Host "Digite o SteamID do jogador a resetar (ou pressione Enter para o padrao 76561198040636105)"
    if ([string]::IsNullOrWhiteSpace($steamId)) {
        $steamId = "76561198040636105"
    }
}

Write-Host "SteamID Alvo: $steamId"
Write-Host "==================================================`n"

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

# Load the Type
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
    
    # Executar SQL Statements com parametrizacao manual simples (SteamID eh numerico longo/string segura)
    # Sanitizacao basica
    $steamIdSafe = $steamId -replace "[^0-9]", ""
    if ([string]::IsNullOrWhiteSpace($steamIdSafe)) {
        Write-Host "SteamID invalido!" -ForegroundColor Red
        Exit
    }

    $sql = @"
    UPDATE players SET discord_user_id = NULL, discord_linked_at = NULL WHERE steam_id = '$steamIdSafe';
    DELETE FROM discord_link_tokens WHERE consumed_by_steam_id = '$steamIdSafe';
    DELETE FROM shop_order_item WHERE order_id IN (SELECT order_id FROM shop_order WHERE steam_id = '$steamIdSafe');
    DELETE FROM shop_delivery_item WHERE order_id IN (SELECT order_id FROM shop_order WHERE steam_id = '$steamIdSafe');
    DELETE FROM shop_order WHERE steam_id = '$steamIdSafe';
    UPDATE wallet SET balance = 5000 WHERE steam_id = '$steamIdSafe';
"@

    Write-Host "Executando reset para o SteamID $steamIdSafe..." -ForegroundColor Cyan
    $execRes = [WinSqlite]::Exec($db, $sql, [IntPtr]::Zero, [IntPtr]::Zero, [ref]$errmsg)
    
    if ($execRes -eq 0) {
        Write-Host "`n>>> Cadastro do jogador resetado com sucesso!" -ForegroundColor Green
        Write-Host "  - Registro do Discord desvinculado (tabela players)" -ForegroundColor Green
        Write-Host "  - Pedidos da loja removidos" -ForegroundColor Green
        Write-Host "  - Tokens antigos limpos" -ForegroundColor Green
        Write-Host "  - Saldo da carteira resetado para R$ 5000" -ForegroundColor Green
        Write-Host "`nPronto! O jogador pode usar o comando de registro e receber o kit de boas-vindas novamente!" -ForegroundColor Green
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
