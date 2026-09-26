# 📊 Sistema de Processamento de Logs do SCUM

## 🎯 Visão Geral

Sistema completo para monitoramento em tempo real e armazenamento de dados de login/logout do servidor SCUM em banco de dados SQLite.

**Importante**: Os logs do SCUM são salvos em **UTF-16LE** (não UTF-8), e o sistema foi desenvolvido para lidar com essa codificação automaticamente.

## 🏗️ Arquitetura

### **Componentes Principais**

```
core/logs/
├── __init__.py              # Módulo principal
├── database_manager.py      # Gerenciador de banco SQLite
├── log_parser.py           # Parser de logs de login
├── file_monitor.py          # Monitor de arquivos em tempo real
├── log_processor.py        # Processador principal
├── temp_file_manager.py    # Gerenciador de arquivos temporários
├── player_processor.py     # Processador de jogadores
└── steam_api.py           # Integração com Steam API
```

### **Fluxo de Processamento**

```
Logs SCUM → Monitor → Cópia Temp → Parser → Banco SQLite → Analytics
    ↓           ↓         ↓         ↓         ↓           ↓
Arquivos    Detecta   Arquivo    Extrai    Armazena   Consultas
login_*.log mudanças  temporário dados     dados      futuras
```

### **Sistema de Arquivos Temporários**

Para evitar problemas de bloqueio quando o SCUM Server está escrevendo nos logs, o sistema utiliza arquivos temporários:

1. **Detecção**: Monitor detecta mudanças nos logs originais
2. **Cópia**: Arquivo é copiado para `data/temp/` (sem bloqueio)
3. **Processamento**: Dados são extraídos da cópia temporária
4. **Limpeza**: Arquivo temporário é removido automaticamente

**Vantagens:**
- ✅ Processamento em tempo real sem bloqueios
- ✅ Compatibilidade com arquivos em uso pelo SCUM
- ✅ Performance otimizada
- ✅ Limpeza automática de arquivos temporários

## 🗄️ Estrutura do Banco de Dados

### **Tabela Principal: `player_logins`**

```sql
CREATE TABLE player_logins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,           -- Steam ID único
    player_name TEXT NOT NULL,        -- Nome do jogador
    player_id INTEGER NOT NULL,       -- ID do jogo
    ip_address TEXT,                  -- IP (dado secundário)
    action TEXT NOT NULL,             -- 'login' ou 'logout'
    coordinates_x REAL,               -- Coordenada X
    coordinates_y REAL,               -- Coordenada Y
    coordinates_z REAL,               -- Coordenada Z
    timestamp DATETIME NOT NULL,      -- Timestamp exato
    server_date DATE,                 -- Data do servidor
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **Tabela de Controle: `log_files_processed`**

```sql
CREATE TABLE log_files_processed (
    file_name TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    last_position INTEGER DEFAULT 0,
    last_modified DATETIME,
    lines_processed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🚀 Como Usar

### **1. Instalar Dependências**

```bash
python install_log_dependencies.py
```

### **2. Testar Sistema**

```bash
# Teste completo
python test_log_processing.py

# Teste específico de UTF-16LE
python test_utf16_parsing.py
```

### **3. Usar em Código**

```python
from core.logs.log_processor import LogProcessor

# Inicializar (carregará diretório do config.json automaticamente)
processor = LogProcessor(db_path="data/SSM.db")

# Ou especificar diretório manualmente
processor = LogProcessor(
    log_directory=r"C:\Servers\scum\SCUM\Saved\SaveFiles\Logs",
    db_path="data/SSM.db"
)

# Processar arquivos existentes
processor.start_processing(real_time=False)

# Iniciar monitoramento em tempo real
processor.start_processing(real_time=True)

# Obter estatísticas
stats = processor.get_processing_stats()
print(f"Total de sessões: {stats['total_sessions']}")

# Parar processamento
processor.stop_processing()
```

## 📊 Dados Extraídos

### **Por Sessão de Login/Logout:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `steam_id` | TEXT | Steam ID único do jogador |
| `player_name` | TEXT | Nome do jogador no jogo |
| `player_id` | INTEGER | ID do jogador no servidor |
| `ip_address` | TEXT | Endereço IP (dado secundário) |
| `action` | TEXT | 'login' ou 'logout' |
| `coordinates_x` | REAL | Coordenada X no mapa |
| `coordinates_y` | REAL | Coordenada Y no mapa |
| `coordinates_z` | REAL | Coordenada Z (altura) |
| `timestamp` | DATETIME | Timestamp exato da ação |
| `server_date` | DATE | Data do servidor |

### **Exemplo de Dados:**

```json
{
  "steam_id": "76561198140545020",
  "player_name": "mariocs10",
  "player_id": 12,
  "ip_address": "177.34.46.28",
  "action": "login",
  "coordinates_x": 568142.000,
  "coordinates_y": -222472.000,
  "coordinates_z": 363.000,
  "timestamp": "2025-10-18 00:03:38",
  "server_date": "2025-10-18"
}
```

## 🔍 Monitoramento em Tempo Real

### **Características:**

- ✅ **Detecção instantânea** de mudanças nos arquivos
- ✅ **Processamento incremental** (só linhas novas)
- ✅ **Controle de posição** em cada arquivo
- ✅ **Baixo uso de recursos** (não reprocessa arquivos)
- ✅ **Tratamento de erros** robusto

### **Arquivos Monitorados:**

- `login_*.log` (apenas o mais recente) — base de Players Online
- `chat_*.log` — envio de mensagens em tempo real ao Discord
- `chest_ownership_*.log` — registro de veículos
- Detecção automática de novos arquivos e troca imediata

## 📈 Estatísticas Disponíveis

### **Estatísticas de Processamento:**

```python
stats = processor.get_processing_stats()
# {
#   'total_sessions': 150,
#   'files_processed': 5,
#   'errors': 0,
#   'runtime_seconds': 45.2,
#   'monitoring': {...}
# }
```

### **Estatísticas do Banco:**

```python
db_stats = processor.db_manager.get_database_stats()
# {
#   'total_logins': 150,
#   'logins_by_action': {'login': 75, 'logout': 75},
#   'files_processed': 5,
#   'last_login': '2025-10-18 01:17:36'
# }
```

## 🛠️ Configuração

### **Codificação dos Logs:**

O sistema detecta automaticamente a codificação dos logs do SCUM:

- **UTF-16LE** (padrão do SCUM) - detectado automaticamente
- **UTF-8** (fallback) - usado se UTF-16LE falhar
- **Detecção automática** - sem configuração necessária

### **Diretório de Logs:**

O diretório de logs é configurado no `config.json`:

```json
{
  "server": {
    "logs_directory": "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\Logs"
  }
}
```

**Configuração automática:**
```python
# O LogProcessor carrega automaticamente do config.json
processor = LogProcessor()  # Usa config.json
```

**Configuração manual:**
```python
# Especificar diretório manualmente
processor = LogProcessor(log_directory="C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\Logs")
```

### **Banco de Dados:**

```python
# Banco padrão
db_path = "data/SSM.db"

# Banco customizado
db_path = "custom/path/SSM.db"
```

## 🔧 Funcionalidades Avançadas

### **Limpeza de Dados Antigos:**

```python
# Limpar dados com mais de 30 dias
deleted_count = processor.cleanup_old_data(days_to_keep=30)
print(f"Dados antigos removidos: {deleted_count}")
```

### **Consultas Personalizadas:**

```python
# Obter logins recentes
recent_logins = processor.get_recent_logins(limit=100)

# Obter estatísticas do banco
db_stats = processor.db_manager.get_database_stats()
```

## 🚨 Troubleshooting

### **Problemas Comuns:**

#### **1. Diretório de logs não encontrado**
```
❌ Diretório de logs não encontrado: C:\Servers\scum\SCUM\Saved\SaveFiles\Logs
```
**Solução:** Verificar se o caminho está correto e se o servidor SCUM está rodando.

#### **2. Nenhum arquivo de login encontrado**
```
⚠️ Nenhum arquivo de login encontrado
```
**Solução:** Verificar se há jogadores fazendo login no servidor.

#### **3. Erro de permissão no banco**
```
❌ Erro ao inicializar banco de dados: [Errno 13] Permission denied
```
**Solução:** Verificar permissões de escrita no diretório `data/`.

### **Logs de Debug:**

```python
# Habilitar logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Exemplos de Uso

### **1. Processamento Básico:**

```python
from core.logs.log_processor import LogProcessor

processor = LogProcessor(
    log_directory=r"C:\Servers\scum\SCUM\Saved\SaveFiles\Logs",
    db_path="data/SSM.db"
)

# Processar arquivos existentes
processor.start_processing(real_time=False)

# Obter estatísticas
stats = processor.get_processing_stats()
print(f"Sessões processadas: {stats['total_sessions']}")
```

### **2. Monitoramento em Tempo Real:**

```python
# Iniciar monitoramento
processor.start_processing(real_time=True)

# Manter rodando
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    processor.stop_processing()
```

### **3. Consultas de Dados:**

```python
# Obter logins recentes
recent = processor.get_recent_logins(50)
for login in recent:
    print(f"{login['player_name']} - {login['action']} - {login['timestamp']}")
```

## 🎯 Próximos Passos

### **Funcionalidades Futuras:**

1. **Análise de Chat** - Processar logs de chat
2. **Análise de Kills** - Processar logs de mortes
3. **Dashboard Web** - Interface para visualização
4. **Relatórios** - Geração de relatórios automáticos
5. **Alertas** - Notificações para eventos específicos

### **Integração com Backend:**

```python
# Adicionar ao main.py
from core.logs.log_processor import LogProcessor

# Inicializar processador de logs
log_processor = LogProcessor(
    log_directory=r"C:\Servers\scum\SCUM\Saved\SaveFiles\Logs",
    db_path="data/SSM.db"
)

# Iniciar processamento
log_processor.start_processing(real_time=True)
```

---

## 🔔 **Sistema de Notificações**

### **Detecção de Novos Jogadores**
- **Automática**: Detecta quando um Steam ID aparece pela primeira vez
- **Discord**: Envia notificação com embed formatado
- **Steam API**: Obtém avatar e país do jogador (opcional)
- **Fallback**: Funciona mesmo sem Steam API

### **Configuração do Webhook**
Configure no `data/webhooks.json`:

```json
{
  "serverstatus": "https://discord.com/api/webhooks/...",
  "new_player": "https://discord.com/api/webhooks/..."
}
```

### **Steam API Key (Opcional)**
Para obter dados completos dos jogadores (avatar, país, nome Steam), configure no `data/config.json`:

```json
{
  "steam": {
    "api_key": "SUA_STEAM_API_KEY_AQUI"
  }
}
```

**Como obter Steam API Key:**
1. Acesse: https://steamcommunity.com/dev/apikey
2. Faça login com sua conta Steam
3. Preencha o formulário (Domain pode ser qualquer um)
4. Clique em "Register"
5. Copie a API Key gerada

**Benefícios com API Key:**
- ✅ Avatar do jogador em alta qualidade
- ✅ Nome Steam oficial
- ✅ País de origem
- ✅ Link do perfil Steam
- ✅ Dados mais precisos e atualizados

**Sem API Key:**
- ✅ Sistema funciona com Steam Community como fallback
- ✅ Dados básicos disponíveis
- ✅ Notificações funcionam normalmente

### **Formato da Notificação**
```json
{
  "content": "🆕 **New Player on Server!**",
  "embeds": [{
    "title": "New Player on Server!",
    "color": 16737077,
    "fields": [
      {"name": "In-Game Name", "value": "mariocs10", "inline": true},
      {"name": "Steam Name", "value": "mariocs10", "inline": true},
      {"name": "Steam ID", "value": "[76561198140545020](https://steamcommunity.com/profiles/76561198140545020)", "inline": false},
      {"name": "Country", "value": "🇧🇷 Brazil", "inline": true},
      {"name": "Join Time", "value": "2025-10-18 00:03:38", "inline": true}
    ],
    "thumbnail": {"url": "https://avatars.steamstatic.com/..."},
    "footer": {"text": "SCUM Server Manager • New Player"}
  }]
}
```

---

**Implementado em**: 15/01/2025  
**Versão**: 1.1.0  
**Status**: ✅ Funcional e Testado com Notificações Discord
