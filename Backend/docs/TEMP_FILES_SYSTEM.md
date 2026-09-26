# 📁 Sistema de Arquivos Temporários

## 🎯 Visão Geral

Sistema desenvolvido para resolver problemas de bloqueio ao processar logs do SCUM em tempo real. Quando o servidor SCUM está ativo, os arquivos de log ficam "em uso" e podem causar erros de leitura.

## 🔧 Como Funciona

### **Problema Original:**
```
SCUM Server → Escreve no login_*.log (arquivo em uso)
     ↓
SSM Backend → Tenta ler login_*.log (BLOQUEADO!)
     ↓
❌ ERRO: Arquivo em uso, não consegue ler
```

### **Solução com Arquivos Temporários:**
```
SCUM Server → Escreve no login_*.log (arquivo em uso)
     ↓
SSM Backend → Copia para data/temp/login_*.log (cópia livre)
     ↓
SSM Backend → Lê da cópia (SEM BLOQUEIO!)
     ↓
SSM Backend → Alimenta banco de dados
     ↓
SSM Backend → Remove cópia temporária
```

## 🏗️ Arquitetura

### **TempFileManager**
```python
from core.logs.temp_file_manager import TempFileManager

# Inicializar
temp_manager = TempFileManager("data/temp")

# Criar cópia temporária
temp_path = temp_manager.create_temp_copy(original_file)

# Ler conteúdo
content = temp_manager.read_temp_file(temp_path)

# Limpar arquivo
temp_manager.cleanup_temp_file(temp_path)
```

### **Integração no LogProcessor**
```python
def _process_file(self, file_path: str):
    temp_path = None
    try:
        # Criar cópia temporária
        temp_path = self.temp_manager.create_temp_copy(file_path)
        
        # Processar arquivo temporário
        sessions = self.parser.parse_file(temp_path)
        
        # ... processar dados ...
        
    finally:
        # Limpar arquivo temporário
        if temp_path:
            self.temp_manager.cleanup_temp_file(temp_path)
```

## 📊 Funcionalidades

### **1. Criação de Cópias**
- ✅ Copia arquivos para pasta `data/temp/`
- ✅ Nomes únicos com timestamp
- ✅ Preserva encoding UTF-16LE
- ✅ Fallback para UTF-8

### **2. Leitura Segura**
- ✅ Lê arquivos sem bloqueio
- ✅ Suporte UTF-16LE (SCUM)
- ✅ Fallback UTF-8
- ✅ Tratamento de erros

### **3. Limpeza Automática**
- ✅ Remove arquivos após uso
- ✅ Limpeza em caso de erro
- ✅ Limpeza geral de arquivos órfãos
- ✅ Controle de arquivos ativos

### **4. Monitoramento**
- ✅ Conta arquivos ativos
- ✅ Calcula tamanho da pasta temp
- ✅ Estatísticas de uso

## 🔧 Configuração

### **Estrutura de Pastas**
```
data/
├── temp/                    # Pasta de arquivos temporários
│   ├── login_2025.10.18_1234567890.log
│   ├── login_2025.10.18_1234567891.log
│   └── ...
├── SSM.db                  # Banco de dados
└── config.json             # Configurações
```

### **Configuração Automática**
O sistema cria automaticamente a pasta `data/temp/` se não existir.

## 📈 Benefícios

### **Performance**
- ✅ Leitura mais rápida (arquivo não bloqueado)
- ✅ Processamento em tempo real
- ✅ Sem espera por liberação de arquivo

### **Confiabilidade**
- ✅ Não falha por arquivo em uso
- ✅ Processamento consistente
- ✅ Recuperação automática de erros

### **Manutenção**
- ✅ Limpeza automática
- ✅ Não acumula arquivos
- ✅ Controle de espaço em disco

## 🚨 Troubleshooting

### **Problemas Comuns**

#### **1. Pasta temp não criada**
```
ERRO: Pasta temp não encontrada
```
**Solução:** Verificar permissões de escrita no diretório `data/`

#### **2. Arquivo temporário não removido**
```
AVISO: Erro ao limpar arquivo temporário
```
**Solução:** O sistema tenta novamente na próxima execução

#### **3. Espaço em disco**
```
AVISO: Pasta temp muito grande
```
**Solução:** Executar limpeza manual:
```python
temp_manager.cleanup_all_temp_files()
```

### **Logs de Debug**
```python
# Habilitar logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Exemplos de Uso

### **Uso Básico**
```python
from core.logs.temp_file_manager import TempFileManager

# Inicializar
temp_manager = TempFileManager()

# Processar arquivo
temp_path = temp_manager.create_temp_copy("logs/login_2025.10.18.log")
if temp_path:
    content = temp_manager.read_temp_file(temp_path)
    # ... processar content ...
    temp_manager.cleanup_temp_file(temp_path)
```

### **Uso Avançado**
```python
# Verificar estatísticas
print(f"Arquivos ativos: {temp_manager.get_active_files_count()}")
print(f"Tamanho da pasta: {temp_manager.get_temp_dir_size()} bytes")

# Limpeza manual
removed = temp_manager.cleanup_all_temp_files()
print(f"Arquivos removidos: {removed}")
```

### **Integração com LogProcessor**
```python
from core.logs.log_processor import LogProcessor

# LogProcessor já inclui TempFileManager
processor = LogProcessor()
# Sistema funciona automaticamente
```

## 🔄 Ciclo de Vida

1. **Detecção**: Monitor detecta mudança no arquivo original
2. **Cópia**: Arquivo é copiado para `data/temp/`
3. **Processamento**: Dados são extraídos da cópia
4. **Armazenamento**: Dados são salvos no banco
5. **Limpeza**: Arquivo temporário é removido

## 📋 Resumo

O sistema de arquivos temporários resolve completamente o problema de processamento de logs em tempo real, permitindo que o SSM Backend funcione perfeitamente mesmo quando o SCUM Server está ativo e escrevendo nos logs.

**Principais vantagens:**
- ✅ Processamento em tempo real sem bloqueios
- ✅ Compatibilidade total com SCUM Server
- ✅ Performance otimizada
- ✅ Limpeza automática
- ✅ Sistema robusto e confiável
