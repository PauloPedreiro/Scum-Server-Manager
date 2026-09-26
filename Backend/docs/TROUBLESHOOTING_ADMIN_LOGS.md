# 🔧 Guia de Troubleshooting - Sistema de Admin Logs

## 📋 Visão Geral

Este guia contém soluções para problemas comuns no sistema de monitoramento de comandos admin do SCUM Server Manager.

## 🚨 Problemas Críticos (v1.2.0)

### ✅ Problema: Erro "_get_last_processed_command"
**Sintoma:**
```
ERRO Erro ao processar admin log: 'AdminLogProcessor' object has no attribute '_get_last_processed_command'
```

**Status:** ✅ **CORRIGIDO na v1.2.0**

**Solução:**
1. Atualize para a versão mais recente do backend
2. Reinicie o serviço
3. Verifique se o erro não aparece mais nos logs

**Verificação:**
```bash
curl -X GET "http://localhost:3000/api/admin-logs/processing-status"
```

### ✅ Problema: Arquivos temporários não removidos
**Sintoma:**
- Pasta `data/temp` acumula arquivos admin_*.log
- Espaço em disco sendo consumido desnecessariamente
- Arquivos órfãos não são limpos

**Status:** ✅ **CORRIGIDO na v1.2.0**

**Solução:**
1. Atualize para a versão mais recente
2. Execute o script de limpeza: `python auto_cleanup_temp.py`
3. Reinicie o backend

**Verificação:**
```bash
# Verificar pasta temp
ls -la data/temp/

# Executar limpeza automática
python auto_cleanup_temp.py
```

### ✅ Problema: Tabela log_files_processed não usada
**Sintoma:**
- Arquivos admin não aparecem na tabela `log_files_processed`
- Estatísticas de processamento incompletas
- Reprocessamento desnecessário de arquivos

**Status:** ✅ **CORRIGIDO na v1.2.0**

**Solução:**
1. Atualize para a versão mais recente
2. Reinicie o backend
3. Execute comandos admin para testar

**Verificação:**
```bash
python check_log_files_status.py
```

## 🔍 Problemas de Configuração

### Problema: Comandos não aparecem no Discord

**Sintomas:**
- Comandos admin executados no jogo
- Nenhuma notificação no Discord
- Logs mostram "Webhook adminlog não configurado"

**Solução:**
1. Verificar configuração do webhook:
```json
{
  "adminlog": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

2. Testar webhook:
```bash
curl -X GET "http://localhost:3000/api/admin-logs/status"
```

3. Verificar se o arquivo `data/webhooks.json` existe e está correto

### Problema: Categorização incorreta

**Sintomas:**
- Comandos aparecem com categoria "Default" 
- Emojis e cores incorretos
- Categorias não reconhecidas

**Solução:**
1. Editar categorias em `core/logs/admin_log_processor.py`:
```python
self.command_categories = {
    'custom': {
        'keywords': ['meucomando', 'custom'],
        'emoji': '⭐',
        'color': 0xff6b35,
        'name': 'Comando Customizado'
    }
}
```

2. Reiniciar o backend após alterações

### Problema: Comandos duplicados

**Sintomas:**
- Mesmo comando aparece múltiplas vezes no Discord
- Sistema reprocessa comandos antigos

**Solução:**
1. Verificar banco de dados:
```bash
python check_log_files_status.py
```

2. Limpar banco se necessário:
```sql
DELETE FROM admin_commands_processed WHERE command_id = 'ID_DUPLICADO';
```

## 📊 Verificações de Status

### 1. Status Geral do Sistema
```bash
curl -X GET "http://localhost:3000/api/admin-logs/status"
```

**Resposta esperada:**
```json
{
  "success": true,
  "data": {
    "admin_log_processor": true,
    "webhook_configured": true,
    "total_commands_processed": 156
  }
}
```

### 2. Status de Processamento
```bash
curl -X GET "http://localhost:3000/api/admin-logs/processing-status"
```

**Resposta esperada:**
```json
{
  "success": true,
  "data": {
    "processing_status": "active",
    "method_available": true,
    "temp_files_cleanup": "working",
    "log_files_table": "active"
  }
}
```

### 3. Status da Tabela de Arquivos
```bash
curl -X GET "http://localhost:3000/api/admin-logs/files-status"
```

**Resposta esperada:**
```json
{
  "success": true,
  "data": {
    "admin_files": 3,
    "files_by_status": {
      "completed": 3
    }
  }
}
```

## 🛠️ Scripts de Diagnóstico

### Script 1: Verificar Status Completo
```python
#!/usr/bin/env python3
import requests

def check_admin_logs_status():
    base_url = "http://localhost:3000"
    
    print("=== DIAGNÓSTICO SISTEMA ADMIN LOGS ===")
    
    # Status geral
    try:
        response = requests.get(f"{base_url}/api/admin-logs/status")
        if response.status_code == 200:
            data = response.json()
            print("✅ Status geral: OK")
            print(f"   - Comandos processados: {data['data']['total_commands_processed']}")
        else:
            print("❌ Status geral: ERRO")
    except Exception as e:
        print(f"❌ Erro ao verificar status: {e}")
    
    # Status de processamento
    try:
        response = requests.get(f"{base_url}/api/admin-logs/processing-status")
        if response.status_code == 200:
            data = response.json()
            print("✅ Status de processamento: OK")
            print(f"   - Versão: {data['data']['version']}")
        else:
            print("❌ Status de processamento: ERRO")
    except Exception as e:
        print(f"❌ Erro ao verificar processamento: {e}")

if __name__ == "__main__":
    check_admin_logs_status()
```

### Script 2: Limpeza de Arquivos Temporários
```python
#!/usr/bin/env python3
from pathlib import Path

def cleanup_temp_files():
    temp_dir = Path("data/temp")
    
    if not temp_dir.exists():
        print("❌ Pasta temp não encontrada")
        return
    
    files = list(temp_dir.glob("*"))
    if not files:
        print("✅ Pasta temp já está vazia")
        return
    
    print(f"📁 Encontrados {len(files)} arquivos temporários")
    
    for file_path in files:
        if file_path.is_file():
            try:
                file_path.unlink()
                print(f"✅ Removido: {file_path.name}")
            except Exception as e:
                print(f"❌ Erro ao remover {file_path.name}: {e}")

if __name__ == "__main__":
    cleanup_temp_files()
```

## 📝 Logs de Diagnóstico

### Verificar Logs do Backend
```bash
# Logs em tempo real
tail -f data/logs/scum_backend.log

# Filtrar apenas admin logs
grep "ADMIN LOG" data/logs/scum_backend.log

# Filtrar erros
grep "ERRO.*admin" data/logs/scum_backend.log
```

### Logs Importantes a Monitorar
- `ADMIN LOG Processando arquivo:` - Processamento iniciado
- `OK Admin log processado com sucesso` - Processamento concluído
- `ERRO Erro ao processar admin log` - Erro no processamento
- `OK Arquivo temporário removido` - Limpeza funcionando

## 🔄 Procedimentos de Recuperação

### Recuperação Completa do Sistema
1. **Parar o backend**
2. **Limpar arquivos temporários:**
   ```bash
   python auto_cleanup_temp.py
   ```
3. **Verificar banco de dados:**
   ```bash
   python check_log_files_status.py
   ```
4. **Reiniciar o backend**
5. **Testar com comando admin**

### Reset do Sistema de Admin Logs
1. **Parar o backend**
2. **Limpar tabela de comandos:**
   ```sql
   DELETE FROM admin_commands_processed;
   ```
3. **Limpar tabela de arquivos:**
   ```sql
   DELETE FROM log_files_processed WHERE file_name LIKE 'admin_%';
   ```
4. **Reiniciar o backend**

## 📞 Suporte

### Informações para Suporte
Ao reportar problemas, inclua:

1. **Versão do sistema:**
   ```bash
   curl -X GET "http://localhost:3000/api/admin-logs/processing-status" | grep version
   ```

2. **Logs de erro:**
   ```bash
   grep "ERRO.*admin" data/logs/scum_backend.log | tail -10
   ```

3. **Status da pasta temp:**
   ```bash
   ls -la data/temp/ | wc -l
   ```

4. **Status do banco:**
   ```bash
   python check_log_files_status.py
   ```

### Checklist de Verificação
- [ ] Webhook configurado em `data/webhooks.json`
- [ ] Backend na versão 1.2.0 ou superior
- [ ] Pasta temp limpa (sem arquivos órfãos)
- [ ] Tabela `log_files_processed` funcionando
- [ ] Método `_get_last_processed_command` disponível
- [ ] Logs sem erros de processamento

---

**Última atualização**: 21/10/2025  
**Versão**: 1.2.0  
**Status**: ✅ Guia Completo e Atualizado
