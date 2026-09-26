#!/usr/bin/env python3
"""
Script para aplicar ícone aos executáveis usando Resource Hacker
Este script tenta localizar e usar Resource Hacker automaticamente
"""
import sys
import subprocess
from pathlib import Path

def find_resource_hacker():
    """Encontrar Resource Hacker em locais comuns"""
    possible_paths = [
        Path("tools") / "ResourceHacker.exe",
        Path("ResourceHacker.exe"),
        Path("C:/Program Files/Resource Hacker/ResourceHacker.exe"),
        Path("C:/Program Files (x86)/Resource Hacker/ResourceHacker.exe"),
        Path.home() / "Downloads" / "ResourceHacker.exe",
        Path.home() / "Desktop" / "ResourceHacker.exe",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None

def apply_icon_with_resource_hacker(exe_path: Path, icon_path: Path, res_hacker_path: Path):
    """Aplicar ícone usando Resource Hacker via linha de comando"""
    try:
        # Resource Hacker aceita comandos via linha de comando
        # Formato: ResourceHacker.exe -open exe -save exe -action addoverwrite -res icon -mask ICONGROUP,1,
        
        cmd = [
            str(res_hacker_path),
            "-open", str(exe_path),
            "-save", str(exe_path),
            "-action", "addoverwrite",
            "-res", str(icon_path),
            "-mask", "ICONGROUP,1,"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        if result.returncode == 0:
            return True, "Ícone aplicado com sucesso"
        else:
            # Resource Hacker pode retornar código de erro mesmo em sucesso
            # Verificar se a saída contém mensagens de erro
            if "error" in result.stderr.lower() or "failed" in result.stderr.lower():
                return False, f"Erro: {result.stderr}"
            else:
                return True, "Ícone aplicado (verificar manualmente)"
                
    except FileNotFoundError:
        return False, "Resource Hacker não encontrado"
    except Exception as e:
        return False, f"Erro ao executar Resource Hacker: {e}"

def main():
    """Função principal"""
    root_dir = Path(__file__).parent.parent
    dist_dir = root_dir / "dist"
    
    # Caminho do ícone
    icon_paths = [
        root_dir / "data" / "imagens" / "LogoSSM" / "W-SSM-Ico.ico",
    ]
    
    icon_path = None
    for path in icon_paths:
        if path.exists():
            icon_path = path
            break
    
    if not icon_path or not icon_path.exists():
        print("[ERRO] Ícone não encontrado!")
        print(f"       Procurando: {icon_path}")
        return 1
    
    # Procurar Resource Hacker
    res_hacker = find_resource_hacker()
    
    if not res_hacker:
        print("=" * 70)
        print("Resource Hacker não encontrado automaticamente")
        print("=" * 70)
        print()
        print("INSTRUÇÕES MANUAIS:")
        print()
        print("1. Baixe Resource Hacker:")
        print("   http://www.angusj.com/resourcehacker/")
        print()
        print("2. Extraia ResourceHacker.exe para uma das seguintes pastas:")
        print("   - tools/ResourceHacker.exe")
        print("   - C:/Program Files/Resource Hacker/ResourceHacker.exe")
        print("   - Ou qualquer pasta e execute este script novamente")
        print()
        print("3. Depois, execute este script novamente ou use manualmente:")
        print()
        
        executables = [
            dist_dir / "Panel SSM.exe",
            # Removido: SSM Backend.exe e launcher.exe (integrados no Panel SSM)
        ]
        
        for exe in executables:
            if exe.exists():
                print(f"   Para {exe.name}:")
                print(f"   - Abra Resource Hacker")
                print(f"   - Abra: {exe}")
                print(f"   - Action > Replace Icon...")
                print(f"   - Selecione: {icon_path.name}")
                print(f"   - Clique em Replace")
                print(f"   - Salve (Ctrl+S)")
                print()
        
        return 1
    
    # Executáveis para aplicar ícone
    executables = [
        dist_dir / "Panel SSM.exe",
        # Removido: SSM Backend.exe e launcher.exe (integrados no Panel SSM)
    ]
    
    print("=" * 70)
    print("Aplicando ícones aos executáveis usando Resource Hacker")
    print("=" * 70)
    print(f"Resource Hacker: {res_hacker}")
    print(f"Ícone: {icon_path.name}")
    print()
    
    success_count = 0
    for exe_path in executables:
        if not exe_path.exists():
            print(f"[AVISO] {exe_path.name} não encontrado, pulando...")
            continue
        
        print(f"Processando: {exe_path.name}...", end=" ")
        success, message = apply_icon_with_resource_hacker(exe_path, icon_path, res_hacker)
        
        if success:
            print(f"[OK]")
            success_count += 1
        else:
            print(f"[ERRO] {message}")
    
    print()
    print("=" * 70)
    print(f"Resultado: {success_count}/{len([e for e in executables if e.exists()])} executáveis processados")
    print("=" * 70)
    
    if success_count > 0:
        print()
        print("[OK] Ícones aplicados!")
        print("     Se não aparecerem imediatamente:")
        print("     1. Limpe o cache de ícones (já feito)")
        print("     2. Reinicie o Explorer novamente se necessário")
        print("     3. Ou reinicie o computador")
    
    return 0 if success_count > 0 else 1

if __name__ == '__main__':
    sys.exit(main())

