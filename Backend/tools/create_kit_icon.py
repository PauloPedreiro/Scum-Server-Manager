#!/usr/bin/env python3
"""
Script para criar ICO multi-size a partir de kit.png
"""
import sys
from pathlib import Path
from PIL import Image


def main():
    root_dir = Path(__file__).parent.parent
    kit_png = root_dir / "data" / "imagens" / "loot" / "kit.png"
    ico_output = root_dir / "data" / "imagens" / "LogoSSM" / "Kit_SSM_Multi.ico"

    # Criar diretório se não existir
    ico_output.parent.mkdir(parents=True, exist_ok=True)

    if not kit_png.exists():
        print(f"[ERRO] Arquivo não encontrado: {kit_png}")
        return 1

    try:
        img = Image.open(kit_png)
        print(f"[INFO] Imagem carregada: {img.size[0]}x{img.size[1]}")

        # Tamanhos para o ICO
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

        # Redimensionar para cada tamanho
        images = []
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            images.append(resized)

        # Salvar como ICO com múltiplos tamanhos
        size_tuples = [(img.width, img.height) for img in images]
        images[0].save(
            ico_output,
            format="ICO",
            sizes=size_tuples,
        )

        print(f"[OK] ICO criado com sucesso: {ico_output}")
        print(f"     Tamanhos incluídos: {', '.join([f'{w}x{h}' for w, h in sizes])}")
        print(f"     Tamanho do arquivo: {ico_output.stat().st_size / 1024:.2f} KB")

        return 0
    except Exception as e:
        print(f"[ERRO] Erro ao criar ICO: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
