#!/usr/bin/env python3
"""
Gerenciador de arquivos temporários para evitar bloqueio de logs em uso
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import time

class TempFileManager:
    """Gerenciador de arquivos temporários para logs SCUM"""
    
    def __init__(self, temp_dir: str = "data/temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.active_files = {}  # {original_path: temp_path}
    
    def create_temp_copy(self, source_path: str) -> Optional[str]:
        """
        Criar cópia temporária de um arquivo de log
        
        Args:
            source_path: Caminho do arquivo original
            
        Returns:
            Caminho do arquivo temporário ou None se falhar
        """
        try:
            source = Path(source_path)
            if not source.exists():
                print(f"AVISO Arquivo não encontrado: {source_path}")
                return None
            
            # Gerar nome único para arquivo temporário
            timestamp = int(time.time() * 1000)
            temp_filename = f"{source.stem}_{timestamp}{source.suffix}"
            temp_path = self.temp_dir / temp_filename
            
            # Copiar arquivo para pasta temp
            shutil.copy2(source_path, temp_path)
            
            # Registrar arquivo ativo
            self.active_files[str(source)] = str(temp_path)
            
            # logger.debug(f"Arquivo copiado para temp: {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            print(f"ERRO Erro ao criar cópia temporária: {e}")
            return None
    
    def create_temp_file_with_content(self, filename: str, lines: list) -> Optional[str]:
        """
        Criar arquivo temporário com conteúdo específico
        
        Args:
            filename: Nome do arquivo original
            lines: Lista de linhas para escrever
            
        Returns:
            Caminho do arquivo temporário ou None se falhar
        """
        try:
            # Gerar nome único para arquivo temporário
            timestamp = int(time.time() * 1000)
            temp_filename = f"{filename}_{timestamp}"
            temp_path = self.temp_dir / temp_filename
            
            # Escrever linhas no arquivo temporário
            with open(temp_path, 'w', encoding='utf-16le') as f:
                for line in lines:
                    f.write(line + '\n')
            
            print(f"OK Arquivo temporário criado: {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            print(f"ERRO Erro ao criar arquivo temporário com conteúdo: {e}")
            return None
    
    def read_temp_file(self, temp_path: str, encoding: str = 'utf-16le') -> Optional[str]:
        """
        Ler conteúdo do arquivo temporário
        
        Args:
            temp_path: Caminho do arquivo temporário
            encoding: Encoding do arquivo (padrão UTF-16LE para SCUM)
            
        Returns:
            Conteúdo do arquivo ou None se falhar
        """
        try:
            with open(temp_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"OK Arquivo temporário lido: {len(content)} caracteres")
            return content
            
        except UnicodeDecodeError:
            # Tentar UTF-8 como fallback
            try:
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"OK Arquivo temporário lido (UTF-8): {len(content)} caracteres")
                return content
            except Exception as e:
                print(f"ERRO Erro ao ler arquivo temporário: {e}")
                return None
                
        except Exception as e:
            print(f"ERRO Erro ao ler arquivo temporário: {e}")
            return None
    
    def cleanup_temp_file(self, temp_path: str) -> bool:
        """
        Limpar arquivo temporário
        
        Args:
            temp_path: Caminho do arquivo temporário
            
        Returns:
            True se sucesso, False se falhar
        """
        try:
            temp_file = Path(temp_path)
            if temp_file.exists():
                temp_file.unlink()
                # logger.debug(f"Arquivo temporário removido: {temp_path}")
            
            # Remover da lista de arquivos ativos
            for original, temp in list(self.active_files.items()):
                if temp == temp_path:
                    del self.active_files[original]
                    break
            
            return True
            
        except Exception as e:
            print(f"AVISO Erro ao limpar arquivo temporário: {e}")
            return False
    
    def cleanup_all_temp_files(self, silent: bool = False) -> int:
        """
        Limpar todos os arquivos temporários
        
        Returns:
            Número de arquivos removidos
        """
        removed_count = 0
        
        try:
            # Limpar arquivos ativos
            for original, temp_path in list(self.active_files.items()):
                if self.cleanup_temp_file(temp_path):
                    removed_count += 1
            
            # Limpar arquivos órfãos na pasta temp
            for temp_file in self.temp_dir.glob("*"):
                if temp_file.is_file():
                    try:
                        temp_file.unlink()
                        removed_count += 1
                        if not silent:
                            print(f"OK Arquivo órfão removido: {temp_file}")
                    except Exception as e:
                        if not silent:
                            print(f"AVISO Erro ao remover arquivo órfão: {e}")
            
            if not silent:
                print(f"OK Limpeza concluída: {removed_count} arquivos removidos")
            return removed_count
            
        except Exception as e:
            if not silent:
                print(f"ERRO Erro na limpeza geral: {e}")
            return removed_count
    
    def get_temp_dir_size(self) -> int:
        """Obter tamanho da pasta temp em bytes"""
        try:
            total_size = 0
            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception:
            return 0
    
    def get_active_files_count(self) -> int:
        """Obter número de arquivos temporários ativos"""
        return len(self.active_files)
    
    def __del__(self):
        """Destructor - limpar arquivos temporários ao sair"""
        try:
            self.cleanup_all_temp_files(silent=True)
        except Exception:
            pass  # Ignorar erros no destructor
