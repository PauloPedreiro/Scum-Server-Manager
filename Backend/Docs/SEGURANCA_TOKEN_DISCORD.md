# 🔒 Segurança - Token do Discord

## ⚠️ ALERTA DE SEGURANÇA

O token do Discord foi removido do arquivo `config.json` por questões de segurança. **NUNCA** commite tokens ou senhas no repositório!

## Como Configurar o Token de Forma Segura

### 1. Revogue o Token Atual (IMEDIATO)
1. Acesse [Discord Developer Portal](https://discord.com/developers/applications)
2. Selecione sua aplicação
3. Vá em "Bot" → "Reset Token"
4. **IMEDIATAMENTE** revogue o token antigo

### 2. Gere um Novo Token
1. No Discord Developer Portal, gere um novo token
2. Copie o novo token

### 3. Configure o Token Localmente
Edite o arquivo `src/data/server/config.json` e substitua `"SEU_TOKEN_AQUI"` pelo seu novo token:

```json
{
  "discord_bot": {
    "enabled": true,
    "token": "SEU_NOVO_TOKEN_AQUI",
    // ... resto da configuração
  }
}
```

### 4. Adicione ao .gitignore
Certifique-se de que o arquivo `config.json` está no `.gitignore`:

```gitignore
# Configurações com tokens
src/data/server/config.json
```

### 5. Use Variáveis de Ambiente (Recomendado)
Para maior segurança, use variáveis de ambiente:

1. Crie um arquivo `.env` na raiz do projeto:
```env
DISCORD_BOT_TOKEN=seu_token_aqui
```

2. Modifique o código para ler da variável de ambiente:
```javascript
const token = process.env.DISCORD_BOT_TOKEN || config.discord_bot.token;
```

## Comandos para Corrigir o Repositório

```bash
# 1. Remova o arquivo do histórico do Git
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch src/data/server/config.json" \
  --prune-empty --tag-name-filter cat -- --all

# 2. Force push para limpar o histórico
git push origin --force --all

# 3. Adicione o arquivo ao .gitignore
echo "src/data/server/config.json" >> .gitignore

# 4. Faça um novo commit
git add .gitignore
git commit -m "fix: remove sensitive data and update gitignore"
git push origin main
```

## Verificação de Segurança

Após fazer as correções, verifique se não há mais tokens expostos:

```bash
# Procure por padrões de token no repositório
grep -r "MTM5NTQ5NjY1NDE1NjU5NTQwNA" .
grep -r "discord.*token" . --ignore-case
```

## Próximos Passos

1. ✅ Revogue o token antigo
2. ✅ Gere novo token
3. ✅ Configure localmente
4. ✅ Limpe o histórico do Git
5. ✅ Atualize .gitignore
6. ✅ Teste a aplicação
