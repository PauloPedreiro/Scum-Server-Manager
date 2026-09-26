"""
Helper para carregar ícones usando FontAwesome ou Material Design Icons
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import customtkinter as ctk
import io


class IconHelper:
    """Helper para criar e carregar ícones"""

    # Cores padrão para ícones
    DEFAULT_COLOR = "#ffffff"

    @staticmethod
    def get_icons_path(root_dir: Path, exe_dir: Path, is_exe: bool) -> Path:
        """
        Obter caminho da pasta de ícones

        Args:
            root_dir: Diretório raiz (quando executável)
            exe_dir: Diretório do executável
            is_exe: Se está rodando como executável

        Returns:
            Path da pasta de ícones
        """
        if is_exe:
            return exe_dir / "data" / "imagens" / "Icons"
        else:
            return root_dir / "data" / "imagens" / "Icons"

    @staticmethod
    def load_icon(
        icon_name: str, root_dir: Path, exe_dir: Path, is_exe: bool, size: int = 20
    ) -> ctk.CTkImage:
        """
        Carregar ícone da pasta Icons ou criar fallback

        Args:
            icon_name: Nome do ícone ('editar', 'salvar', 'copiar', 'eye')
            root_dir: Diretório raiz
            exe_dir: Diretório do executável
            is_exe: Se está rodando como executável
            size: Tamanho do ícone

        Returns:
            CTkImage com o ícone
        """
        icons_path = IconHelper.get_icons_path(root_dir, exe_dir, is_exe)
        icon_file = icons_path / f"{icon_name}.png"

        # Tentar carregar do arquivo
        if icon_file.exists():
            try:
                return IconHelper.load_icon_from_file(icon_file, size)
            except Exception as e:
                print(f"Erro ao carregar ícone {icon_file}: {e}")

        # Fallback: criar ícone simples
        return IconHelper.create_simple_icon(icon_name, size)

    @staticmethod
    def create_icon_image(
        icon_type: str, size: int = 20, color: str = None
    ) -> ctk.CTkImage:
        """
        Criar ícone usando caracteres Unicode ou símbolos simples

        Args:
            icon_type: Tipo de ícone ('eye', 'edit', 'save', 'copy', 'hide')
            size: Tamanho do ícone em pixels
            color: Cor do ícone (hex)

        Returns:
            CTkImage com o ícone
        """
        if color is None:
            color = IconHelper.DEFAULT_COLOR

        # Criar imagem transparente
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Mapeamento de ícones usando símbolos Unicode simples
        icon_symbols = {
            "eye": "👁",
            "eye_hide": "🙈",
            "edit": "✏",
            "save": "💾",
            "copy": "📋",
            "check": "✓",
            "cross": "✗",
            "play": "▶",
            "stop": "■",
            "settings": "⚙",
        }

        symbol = icon_symbols.get(icon_type, "?")

        # Tentar usar fonte para melhor renderização
        try:
            # Tentar usar fonte do sistema
            font_size = int(size * 0.8)
            try:
                # Windows
                font = ImageFont.truetype("seguiemj.ttf", font_size)
            except:
                try:
                    # Linux
                    font = ImageFont.truetype(
                        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", font_size
                    )
                except:
                    # Fallback
                    font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        # Desenhar símbolo
        bbox = draw.textbbox((0, 0), symbol, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (size - text_width) // 2
        y = (size - text_height) // 2

        # Converter cor hex para RGB
        if color.startswith("#"):
            color_rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
        else:
            color_rgb = (255, 255, 255)

        draw.text((x, y), symbol, fill=color_rgb + (255,), font=font)

        # Converter para CTkImage
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    @staticmethod
    def load_icon_from_file(file_path: Path, size: int = 20) -> ctk.CTkImage:
        """
        Carregar ícone de arquivo PNG/SVG

        Args:
            file_path: Caminho do arquivo
            size: Tamanho desejado

        Returns:
            CTkImage com o ícone
        """
        try:
            img = Image.open(file_path)
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        except Exception as e:
            print(f"Erro ao carregar ícone {file_path}: {e}")
            # Retornar ícone padrão
            return IconHelper.create_icon_image("settings", size)

    @staticmethod
    def create_simple_icon(
        shape: str, size: int = 20, color: str = None
    ) -> ctk.CTkImage:
        """
        Criar ícones simples usando formas geométricas

        Args:
            shape: Tipo de forma ('eye', 'edit', 'save', 'copy')
            size: Tamanho do ícone
            color: Cor do ícone

        Returns:
            CTkImage com o ícone
        """
        if color is None:
            color = IconHelper.DEFAULT_COLOR

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Converter cor hex para RGB
        if color.startswith("#"):
            color_rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
        else:
            color_rgb = (255, 255, 255)

        fill_color = color_rgb + (255,)

        # Desenhar formas simples
        if shape == "eye":
            # Olho simples
            center = size // 2
            radius = size // 3
            draw.ellipse(
                [center - radius, center - radius, center + radius, center + radius],
                outline=fill_color,
                width=2,
            )
            draw.ellipse(
                [
                    center - radius // 3,
                    center - radius // 3,
                    center + radius // 3,
                    center + radius // 3,
                ],
                fill=fill_color,
            )

        elif shape == "edit":
            # Lápis simples
            points = [
                (size * 0.2, size * 0.8),
                (size * 0.3, size * 0.7),
                (size * 0.7, size * 0.3),
                (size * 0.8, size * 0.2),
                (size * 0.6, size * 0.2),
                (size * 0.2, size * 0.6),
            ]
            draw.polygon(points, outline=fill_color, width=2)
            draw.line(
                [size * 0.2, size * 0.8, size * 0.3, size * 0.7],
                fill=fill_color,
                width=2,
            )

        elif shape == "save":
            # Disquete simples
            margin = size // 4
            # Corpo do disquete
            draw.rectangle(
                [margin, margin, size - margin, size - margin],
                outline=fill_color,
                width=2,
            )
            # Etiqueta
            draw.rectangle(
                [margin * 1.5, margin * 1.5, size - margin * 1.5, margin * 2],
                fill=fill_color,
            )
            # Slot
            draw.rectangle(
                [
                    size // 2 - margin // 2,
                    size - margin * 1.5,
                    size // 2 + margin // 2,
                    size - margin,
                ],
                fill=fill_color,
            )

        elif shape == "copy":
            # Dois quadrados sobrepostos
            offset = size // 6
            draw.rectangle(
                [offset, offset, size - offset, size - offset],
                outline=fill_color,
                width=2,
            )
            draw.rectangle(
                [0, 0, size - offset, size - offset], outline=fill_color, width=2
            )

        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
