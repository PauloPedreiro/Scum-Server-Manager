#!/usr/bin/env python3
"""
Script para converter PNG para ICO
Converte Mine_01.png para Mine_01.ico com múltiplos tamanhos
"""

import sys
import os
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[ERRO] Pillow nao esta instalado!")
    print("[INFO] Instalando Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image

def convert_png_to_ico(png_path, ico_path, sizes=None):
    """
    Converte PNG para ICO com múltiplos tamanhos
    
    Args:
        png_path: Caminho do arquivo PNG
        ico_path: Caminho do arquivo ICO de saída
        sizes: Lista de tamanhos (padrão: [256, 128, 64, 48, 32, 16])
    """
    if sizes is None:
        sizes = [256, 128, 64, 48, 32, 16]
    
    # Abrir imagem PNG
    img = Image.open(png_path)
    if img.mode not in ('RGBA', 'RGB'):
        img = img.convert('RGBA')
    
    # Criar lista de imagens em diferentes tamanhos
    ico_images = []
    for size in sizes:
        # Redimensionar mantendo proporção
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        ico_images.append(resized)
    
    # Salvar como ICO
    ico_images[0].save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=ico_images[1:]
    )
    
    print(f"[OK] Convertido: {png_path} -> {ico_path}")
    print(f"[INFO] Tamanhos incluidos: {sizes}")
    
    # Mostrar tamanho do arquivo
    file_size = os.path.getsize(ico_path)
    print(f"[INFO] Tamanho do arquivo: {file_size / 1024:.2f} KB")


def convert_image_to_png(input_path, output_path, size=180):
    img = Image.open(input_path)
    if img.mode not in ('RGBA', 'RGB'):
        img = img.convert('RGBA')
    resized = img.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(output_path, format='PNG')
    file_size = os.path.getsize(output_path)
    print(f"[OK] Gerado PNG: {input_path} -> {output_path}")
    print(f"[INFO] Tamanho: {size}x{size}")
    print(f"[INFO] Tamanho do arquivo: {file_size / 1024:.2f} KB")

if __name__ == "__main__":
    # Uso:
    #   python convert_to_ico.py <input.(png|webp|jpg|jpeg)> <output.(ico|png)> [size]
    # Sem argumentos: converte Mine_01.png -> Mine_01.ico
    if len(sys.argv) >= 3:
        input_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
        size = 180
        if len(sys.argv) >= 4:
            try:
                size = int(sys.argv[3])
            except ValueError:
                print("[ERRO] size invalido. Use um numero inteiro.")
                sys.exit(1)

        if not input_path.exists():
            print(f"[ERRO] Arquivo nao encontrado: {input_path}")
            sys.exit(1)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if output_path.suffix.lower() == '.ico':
                print("[INFO] Convertendo imagem para ICO...")
                print(f"[INFO] Entrada: {input_path}")
                print(f"[INFO] Saida: {output_path}")
                print()
                convert_png_to_ico(str(input_path), str(output_path))
            elif output_path.suffix.lower() == '.png':
                print("[INFO] Gerando PNG redimensionado...")
                print(f"[INFO] Entrada: {input_path}")
                print(f"[INFO] Saida: {output_path}")
                print()
                convert_image_to_png(str(input_path), str(output_path), size=size)
            else:
                print("[ERRO] Extensao de saida nao suportada. Use .ico ou .png")
                sys.exit(1)

            print()
            print("[OK] Conversao concluida com sucesso!")
        except Exception as e:
            print(f"[ERRO] Erro durante conversao: {e}")
            sys.exit(1)
    else:
        # Caminhos (modo legado)
        script_dir = Path(__file__).parent
        png_file = script_dir / "Mine_01.png"
        ico_file = script_dir / "Mine_01.ico"

        if not png_file.exists():
            print(f"[ERRO] Arquivo nao encontrado: {png_file}")
            sys.exit(1)

        print("[INFO] Convertendo PNG para ICO...")
        print(f"[INFO] Entrada: {png_file}")
        print(f"[INFO] Saida: {ico_file}")
        print()

        try:
            convert_png_to_ico(str(png_file), str(ico_file))
            print()
            print("[OK] Conversao concluida com sucesso!")
        except Exception as e:
            print(f"[ERRO] Erro durante conversao: {e}")
            sys.exit(1)

