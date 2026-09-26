import sys
import os
from pathlib import Path
from utils.app_data_dir import get_runtime_data_dir

# Detectar se está rodando como executável
if getattr(sys, "frozen", False):
    # Rodando como executável (PyInstaller)
    ROOT_DIR = Path(sys._MEIPASS)  # Diretório temporário do PyInstaller
    EXE_DIR = Path(sys.executable).parent  # Diretório onde o .exe está
    IS_EXE = True
else:
    # Rodando como script Python
    # app/constants.py -> app/ -> root/
    ROOT_DIR = Path(__file__).parent.parent
    EXE_DIR = ROOT_DIR
    IS_EXE = False

DATA_DIR = get_runtime_data_dir(is_exe=IS_EXE, exe_dir=EXE_DIR, project_root=ROOT_DIR)
