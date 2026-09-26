# 🐛 Resumo: Bug no Endpoint de Sincronização

> **Para**: Desenvolvedor do Gestão  
> **Prioridade**: Alta  
> **Data**: 2025-01-15

---

## ❌ Problema

**Endpoint**: `POST /api/v1/servers/sync`  
**Erro**: `500 Internal Server Error`  
**Mensagem**: `"float() argument must be a string or a real number, not 'NoneType'"`

---

## 🔍 Causa

O código está tentando converter valores `None` para `float()` ou `int()`, causando erro.

**Campos problemáticos:**
- `fame` (pode ser `None`)
- `score`, `kdr`, `deaths` (podem ser `None`)
- `last_seen` (pode ser `None`)
- Arrays vazios em `rankings`

---

## ✅ Solução Rápida

Implementar funções helper para conversão segura:

```python
def safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
```

**Usar antes de converter valores:**
```python
# ❌ Antes (causa erro)
fame = float(player.get('fame'))

# ✅ Depois (seguro)
fame = safe_float(player.get('fame'), 0.0)
```

---

## 📋 Checklist

- [ ] Adicionar `safe_float()` e `safe_int()`
- [ ] Validar todos os campos numéricos antes de processar
- [ ] Tratar arrays vazios em `rankings`
- [ ] Testar com payload contendo `None`
- [ ] Testar com arrays vazios

---

## 📄 Documentação Completa

Para detalhes completos, exemplos de código e testes, consulte:
**`docs/CORRECAO_BUG_SINCRONIZACAO_GESTAO.md`**

---

## 🧪 Teste Rápido

Enviar este payload deve funcionar sem erro:

```json
{
  "server_hash": "9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0",
  "api_key": "ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10",
  "server_info": {
    "name": "Test",
    "version": "3.0.0",
    "max_players": 64,
    "current_players": 0
  },
  "players": [
    {
      "steam_id": "76561198012345678",
      "name": "TestPlayer",
      "fame": null,
      "is_online": false,
      "last_seen": null
    }
  ],
  "rankings": {
    "kills": [],
    "survival": [],
    "lockpicking": [],
    "fishing": []
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resultado esperado**: `200 OK` com `{"success": true}`

