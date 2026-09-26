# 👨‍💼 Sistema de Monitoramento de Comandos Admin

## 📋 Visão Geral

O sistema de monitoramento de comandos admin permite acompanhar em tempo real todos os comandos executados por administradores no servidor SCUM, enviando notificações organizadas para Discord.

## 🎯 Funcionalidades

### ✅ Monitoramento Automático
- **Arquivos monitorados**: `admin_*.log`
- **Detecção em tempo real**: Polling a cada 5 segundos
- **Processamento incremental**: Apenas comandos novos
- **Controle de duplicatas**: Sistema baseado em timestamp + steam_id

### ✅ Categorização Inteligente
- **🚀 Teleport**: Comandos de teleporte (roxo)
- **🎁 Spawn**: Spawn de itens (amarelo)
- **🛡️ God Mode**: Comandos de god mode (vermelho)
- **👁️ Info**: Informações de jogadores (azul)
- **⚡ Command**: Outros comandos (laranja)
- **📋 Default**: Comandos não categorizados (verde)

### ✅ Notificações Discord
- **Embeds coloridos**: Cores específicas por categoria
- **Emojis categorizados**: Emojis únicos para cada tipo de comando
- **Informações completas**: Timestamp, jogador, steam_id e comando
- **Rate limiting**: Sem limitação para comandos admin

## 🔧 Configuração

### 1. Webhook Discord
Adicione o webhook no arquivo `data/webhooks.json`:

```json
{
  "adminlog": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

### 2. Categorização Personalizada
Edite o arquivo `core/logs/admin_log_processor.py` para personalizar categorias:

```python
self.command_categories = {
    'teleport': {
        'keywords': ['teleport', 'tp', 'goto'],
        'emoji': '🚀',
        'color': 0x9b59b6,  # Roxo
        'name': 'Teleport'
    },
    # ... outras categorias
}
```

## 📊 Estrutura dos Dados

### Formato do Log Admin
```
2025.10.21-00.13.01: '76561198040636105:Pedreiro(1)' Command: 'SpawnItem Phoenix_Tears'
```

### ID Único do Comando
```
2025.10.21-00.13.01:76561198040636105
```
- **Timestamp**: `2025.10.21-00.13.01`
- **Steam ID**: `76561198040636105`
- **Combinação única**: Garante que cada comando seja processado apenas uma vez

### Embed Discord
```json
{
  "embeds": [{
    "title": "🎁 Spawn Item - Pedreiro",
    "color": 16119260,
    "fields": [
      {
        "name": "👤 Jogador",
        "value": "Pedreiro (76561198040636105)",
        "inline": true
      },
      {
        "name": "⚡ Comando",
        "value": "SpawnItem Phoenix_Tears",
        "inline": true
      },
      {
        "name": "🕐 Timestamp",
        "value": "2025-10-21 00:13:01",
        "inline": true
      }
    ],
    "footer": {
      "text": "SCUM Server Manager - Admin Log"
    }
  }]
}
```

## 🔄 Fluxo de Processamento

### 1. Detecção
- **FileMonitor**: Detecta mudanças em `admin_*.log`
- **Polling**: Verifica arquivos a cada 5 segundos
- **Trigger**: Qualquer mudança no arquivo

### 2. Processamento
- **Cópia para temp**: Evita conflitos com arquivo em uso
- **Parse das linhas**: Extrai timestamp, steam_id, jogador e comando
- **Geração de ID**: Cria ID único (timestamp + steam_id)
- **Verificação de duplicatas**: Compara com último comando processado

### 3. Envio
- **Categorização**: Determina categoria e cor do embed
- **Formatação**: Cria embed Discord com informações
- **Envio**: POST para webhook Discord
- **Salvamento**: Atualiza último comando processado

## 📁 Arquivos do Sistema

### Core Files
- `core/logs/admin_log_processor.py` - Processador principal
- `core/logs/log_processor.py` - Integração com sistema de logs
- `core/logs/file_monitor.py` - Monitoramento de arquivos

### Data Files
- `data/SSM.db` - Banco de dados SQLite com comandos processados
- `data/webhooks.json` - Configuração de webhooks

## 🚀 Vantagens do Sistema

### ✅ Eficiência
- **Processamento incremental**: Não reprocessa comandos antigos
- **Controle de duplicatas**: Sistema robusto baseado em ID único
- **Tempo real**: Detecção e envio imediatos

### ✅ Organização
- **Categorização automática**: Comandos organizados por tipo
- **Embeds coloridos**: Fácil identificação visual
- **Informações completas**: Todos os dados relevantes

### ✅ Confiabilidade
- **Sistema robusto**: Funciona mesmo com múltiplos admins
- **Controle de estado**: Não perde comandos entre reinicializações
- **Tratamento de erros**: Sistema resiliente a falhas

## 🔧 Troubleshooting

### Problema: Comandos não aparecem no Discord
1. Verifique se o webhook está configurado em `data/webhooks.json`
2. Confirme se o arquivo `admin_*.log` existe e tem conteúdo
3. Verifique os logs do backend para erros

### Problema: Comandos duplicados
1. O sistema usa ID único baseado em timestamp + steam_id
2. Verifique se o banco de dados `data/SSM.db` está sendo atualizado
3. Reinicie o backend se necessário

### Problema: Categorização incorreta
1. Edite as categorias em `core/logs/admin_log_processor.py`
2. Adicione palavras-chave específicas para seus comandos
3. Reinicie o backend após alterações

### Problema: Erro "_get_last_processed_command"
1. **CORRIGIDO**: Este erro foi resolvido na versão atual
2. O método `_get_last_processed_command()` foi implementado
3. Sistema agora usa banco de dados SQLite para controle de estado
4. Reinicie o backend para aplicar a correção

### Problema: Arquivos temporários não removidos
1. **CORRIGIDO**: Limpeza de arquivos temporários movida para bloco `finally`
2. Arquivos temporários são removidos mesmo em caso de erro
3. Sistema mais robusto e não acumula arquivos órfãos
4. Reinicie o backend para aplicar a correção

### Problema: Tabela log_files_processed não usada
1. **CORRIGIDO**: Arquivos admin agora são registrados na tabela
2. Controle de arquivos processados implementado
3. Estatísticas de processamento disponíveis
4. Evita reprocessamento desnecessário

## 📈 Estatísticas

O sistema mantém estatísticas de:
- **Comandos processados**: Total de comandos enviados para Discord
- **Categorias mais usadas**: Frequência de cada tipo de comando
- **Admins mais ativos**: Ranking de administradores por atividade
- **Horários de pico**: Análise temporal de uso de comandos

---

**Última atualização**: 21/10/2025  
**Versão**: 1.2.0  
**Status**: ✅ Implementado e Funcionando  
**Correções**: 
- Método `_get_last_processed_command()` implementado
- Limpeza de arquivos temporários corrigida
- Registro na tabela `log_files_processed` implementado
