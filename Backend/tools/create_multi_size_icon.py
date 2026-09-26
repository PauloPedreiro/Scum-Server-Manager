#!/usr/bin/env python3
"""
Script para criar um arquivo ICO com múltiplos tamanhos
Windows precisa de múltiplos tamanhos no arquivo ICO para melhor compatibilidade
"""
import sys
from pathlib import Path
from PIL import Image


def _prepare_icon_rgba(img: Image.Image) -> Image.Image:
    img_rgba = img.convert("RGBA")
    alpha = img_rgba.getchannel("A")
    alpha_cut = alpha.point(lambda a: 255 if a > 20 else 0)
    bbox = alpha_cut.getbbox()
    if bbox:
        img_rgba = img_rgba.crop(bbox)
    return img_rgba


def _render_square(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    target = Image.new("RGBA", size, (0, 0, 0, 0))
    if min(size) <= 32:
        margin_ratio = 0.0
    elif min(size) <= 48:
        margin_ratio = 0.01
    else:
        margin_ratio = 0.08
    margin = max(0, int(min(size) * margin_ratio))
    avail = (max(1, size[0] - 2 * margin), max(1, size[1] - 2 * margin))
    src = img.copy()
    src.thumbnail(avail, Image.Resampling.LANCZOS)
    x = (size[0] - src.size[0]) // 2
    y = (size[1] - src.size[1]) // 2
    target.paste(src, (x, y), src)
    return target


def create_multi_size_ico(input_path: Path, output_path: Path):
    """
    Criar arquivo ICO com múltiplos tamanhos a partir de uma imagem

    Args:
        input_path: Caminho da imagem de entrada (PNG ou ICO)
        output_path: Caminho do arquivo ICO de saída
    """
    try:
        # Carregar imagem de entrada
        img = _prepare_icon_rgba(Image.open(input_path))

        # Tamanhos necessários para Windows (em ordem de prioridade)
        sizes = [
            (256, 256),  # Para alta resolução e barra de tarefas
            (128, 128),  # Para ícones grandes
            (64, 64),  # Para ícones médios
            (48, 48),  # Para ícones padrão
            (32, 32),  # Para ícones pequenos
            (16, 16),  # Para ícones muito pequenos
        ]

        # Criar lista de imagens redimensionadas
        images = []
        for size in sizes:
            images.append(_render_square(img, size))

        # Salvar como ICO com múltiplos tamanhos
        # PIL suporta múltiplos tamanhos usando o parâmetro 'sizes'
        try:
            images[0].save(output_path, format="ICO", sizes=sizes)

            print(f"[OK] Ícone salvo com {len(images)} tamanhos diferentes")

        except Exception as e:
            # Fallback: tentar salvar sem especificar sizes (PIL pode detectar automaticamente)
            try:
                print(f"[AVISO] Método 1 falhou: {e}")
                print(f"        Tentando método alternativo...")

                images[0].save(
                    output_path,
                    format="ICO",
                    save_all=True,
                    append_images=images[1:],
                )
                print(f"[OK] Ícone salvo com {len(images)} tamanhos diferentes")

            except Exception as e2:
                print(f"[ERRO] Não foi possível salvar ícone: {e2}")
                return False

        print(f"[OK] Ícone criado com sucesso: {output_path}")
        print(f"     Tamanhos incluídos: {', '.join([f'{w}x{h}' for w, h in sizes])}")
        return True

    except Exception as e:
        print(f"[ERRO] Erro ao criar ícone: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Função principal"""
    # Caminhos
    root_dir = Path(__file__).parent.parent
    input_path = root_dir / "data" / "imagens" / "LogoSSM" / "SSM-Ico.webp"
    output_path = root_dir / "data" / "imagens" / "LogoSSM" / "SSM-Ico.ico"

    # Se o arquivo de entrada não existir, tentar PNG
    if not input_path.exists():
        input_path = root_dir / "data" / "imagens" / "LogoSSM" / "Logo_SSM_256x256.ico"
        output_path = root_dir / "data" / "imagens" / "LogoSSM" / "Logo_SSM_Multi.ico"

    if not input_path.exists():
        input_path = root_dir / "data" / "imagens" / "LogoSSM" / "Logo_SSM.png"
        output_path = root_dir / "data" / "imagens" / "LogoSSM" / "Logo_SSM_Multi.ico"
        if not input_path.exists():
            input_path = root_dir / "data" / "imagens" / "LogoSSM" / "Grande.png"

    if not input_path.exists():
        print(f"[ERRO] Arquivo de entrada não encontrado: {input_path}")
        print("     Procurando alternativas...")
        # Listar arquivos disponíveis
        logo_dir = root_dir / "data" / "imagens" / "LogoSSM"
        if logo_dir.exists():
            print("     Arquivos disponíveis:")
            for f in logo_dir.iterdir():
                if f.suffix.lower() in [".png", ".ico", ".webp"]:
                    print(f"       - {f.name}")
        return 1

    print(f"Criando ícone multi-tamanho...")
    print(f"  Entrada: {input_path}")
    print(f"  Saída: {output_path}")

    if create_multi_size_ico(input_path, output_path):
        print(f"\n[OK] Ícone criado com sucesso!")
        print(f"     Use este arquivo no spec: {output_path.relative_to(root_dir)}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
