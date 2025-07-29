# Correção do Endpoint AdminUsers.ini

## Problema Identificado

O endpoint `POST /api/configserver/AdminUsers.ini` está automaticamente adicionando o sufixo `[setgodmode]` a todos os SteamIDs, mesmo quando o frontend envia apenas o SteamID básico.

### Comportamento Atual (Incorreto)
```json
// Frontend envia:
{
  "steamId": "76561198422507274"
}

// Backend salva automaticamente:
"76561198422507274[setgodmode]"
```

### Comportamento Desejado (Correto)

O frontend precisa ter controle sobre quando adicionar o sufixo `[setgodmode]`:

1. **Admin Básico** (sem sufixo):
   ```json
   // Frontend envia:
   {
     "steamId": "76561198422507274"
   }
   
   // Backend deve salvar:
   "76561198422507274"
   ```

2. **Admin com Set God Mode** (com sufixo):
   ```json
   // Frontend envia:
   {
     "steamId": "76561198422507274[setgodmode]"
   }
   
   // Backend deve salvar:
   "76561198422507274[setgodmode]"
   ```

## Solução Necessária

### Modificação no Backend

**Endpoint:** `POST /api/configserver/AdminUsers.ini`

**Comportamento Atual:**
- Adiciona automaticamente `[setgodmode]` a todos os SteamIDs

**Comportamento Desejado:**
- Salvar o SteamID exatamente como recebido do frontend
- Se o frontend enviar `"76561198422507274"` → salvar `"76561198422507274"`
- Se o frontend enviar `"76561198422507274[setgodmode]"` → salvar `"76561198422507274[setgodmode]"`

### Fluxo de Funcionamento

1. **Usuário clica "Tornar Admin"** → Frontend envia SteamID básico → Backend salva sem sufixo
2. **Usuário clica "Set God Mode"** → Frontend envia SteamID com sufixo → Backend salva com sufixo

### Benefícios da Correção

- **Flexibilidade:** Permite criar admins com diferentes níveis de privilégio
- **Controle:** O frontend decide quando aplicar o sufixo
- **Clareza:** Separação clara entre admin básico e admin com setgodmode
- **Interface Intuitiva:** Duas colunas separadas na tabela de jogadores

## Teste de Validação

Após a correção, o seguinte fluxo deve funcionar:

1. Adicionar admin básico → SteamID salvo sem `[setgodmode]`
2. Adicionar setgodmode → SteamID salvo com `[setgodmode]`
3. Remover admin → Remove todas as entradas do SteamID (com e sem sufixo)

## Impacto

- **Baixo risco:** Apenas remove a adição automática do sufixo
- **Compatibilidade:** Mantém todos os endpoints existentes
- **Melhoria:** Permite controle granular sobre privilégios de admin 