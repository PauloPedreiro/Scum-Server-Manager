# 📋 Coluna "Admin Config" - ServerSettingsAdminUsers.ini

## 📖 Visão Geral

A coluna "Admin Config" na tabela de jogadores permite gerenciar administradores de configuração do servidor através do endpoint `ServerSettingsAdminUsers.ini`. Esta funcionalidade é separada do botão "Admin" que gerencia o endpoint `AdminUsers.ini`.

## 🎯 Funcionalidades

### ✅ Adicionar Configuração de Admin
- **Botão:** "Config" (azul)
- **Ação:** Adiciona o Steam ID do jogador ao arquivo `ServerSettingsAdminUsers.ini`
- **Método:** POST
- **Payload:** `{ "steamId": "76561198123456789" }`

### ❌ Remover Configuração de Admin
- **Botão:** "✕" (vermelho) ao lado do badge "Config"
- **Ação:** Remove o Steam ID do jogador do arquivo `ServerSettingsAdminUsers.ini`
- **Método:** DELETE
- **Payload:** `{ "steamId": "76561198123456789" }`

## 🏗️ Estrutura da Implementação

### 📁 Arquivos Modificados

#### `src/config/api.ts`
```typescript
// Novo endpoint adicionado
SERVER_SETTINGS_ADMIN_USERS: '/api/configserver/ServerSettingsAdminUsers.ini',
```

#### `src/services/serverSettingsAdminUsersService.ts`
- **Interface:** `ServerSettingsAdminUser`
- **Interface:** `ServerSettingsAdminUsersResponse`
- **Classe:** `ServerSettingsAdminUsersService`
  - `getServerSettingsAdminUsers()`
  - `addServerSettingsAdminUser(steamId)`
  - `removeServerSettingsAdminUser(steamId)`
  - `updateServerSettingsAdminUser(steamId, admin)`
  - `updateServerSettingsAdminUsersBulk(admins)`

#### `src/components/PlayersTable.tsx`
- **Nova prop:** `serverSettingsAdmins?: string[]`
- **Nova prop:** `onServerSettingsAdminAdded?: () => void`
- **Nova condição:** `isServerSettingsAdmin`
- **Nova coluna:** "Admin Config" com botões add/remove

#### `src/pages/Dashboard.tsx`
- **Novo estado:** `serverSettingsAdminSteamIds`
- **Nova função:** `fetchServerSettingsAdmins()`
- **Nova função:** `refreshServerSettingsAdmins()`
- **Nova prop passada:** `serverSettingsAdmins={serverSettingsAdminSteamIds}`
- **Nova prop passada:** `onServerSettingsAdminAdded={refreshServerSettingsAdmins}`

## 🔧 Integração com API

### Endpoint Principal
```
GET/POST/DELETE/PUT http://localhost:3000/api/configserver/ServerSettingsAdminUsers.ini
```

### Resposta de Sucesso (POST)
```json
{
  "success": true,
  "message": "Admin adicionado com sucesso",
  "steamId": "76561198123456789",
  "steamIdSaved": "76561198123456789",
  "backupCreated": "ServerSettingsAdminUsers_ini_2025-07-27_19-38-45.backup"
}
```

### Resposta de Sucesso (DELETE)
```json
{
  "success": true,
  "message": "Admin removido com sucesso",
  "steamId": "76561198123456789",
  "backupCreated": "ServerSettingsAdminUsers_ini_2025-07-27_19-38-45.backup"
}
```

## 🎨 Interface do Usuário

### Estado: Jogador NÃO tem configuração de admin
```html
<button class="px-2 py-1 bg-blue-700 hover:bg-blue-800 text-white rounded text-xs">
  Config
</button>
```

### Estado: Jogador JÁ tem configuração de admin
```html
<div class="flex items-center justify-center gap-1">
  <span class="bg-blue-600 text-white px-2 py-1 rounded text-xs font-bold">Config</span>
  <button class="px-1 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs">✕</button>
</div>
```

## 🔄 Fluxo de Uso

1. **Usuário clica em "Config"** → POST para `/api/configserver/ServerSettingsAdminUsers.ini`
2. **Backend processa** → Adiciona Steam ID ao arquivo INI
3. **Backend responde** → `{ "success": true, "message": "Admin adicionado com sucesso" }`
4. **Frontend atualiza** → Chama `onServerSettingsAdminAdded()` callback
5. **Lista é atualizada** → Badge "Config" aparece com botão "✕"
6. **Usuário clica em "✕"** → DELETE para `/api/configserver/ServerSettingsAdminUsers.ini`
7. **Backend processa** → Remove Steam ID do arquivo INI
8. **Backend responde** → `{ "success": true, "message": "Admin removido com sucesso" }`
9. **Frontend atualiza** → Chama `onServerSettingsAdminAdded()` callback
10. **Lista é atualizada** → Botão "Config" volta a aparecer

## ✅ Validações

### Frontend
- ✅ Verifica se o Steam ID está na lista `serverSettingsAdmins`
- ✅ Mostra loading durante operações
- ✅ Exibe toast de sucesso/erro
- ✅ Atualiza lista após operações

### Backend
- ✅ Valida formato do Steam ID
- ✅ Verifica se Steam ID já existe (POST)
- ✅ Verifica se Steam ID existe (DELETE)
- ✅ Cria backup automático
- ✅ Preserva estrutura do arquivo INI

## 🎯 Benefícios

1. **Separação de Responsabilidades:** Admin (AdminUsers.ini) vs Admin Config (ServerSettingsAdminUsers.ini)
2. **Interface Consistente:** Segue o padrão dos outros botões (VIP, Whitelist, etc.)
3. **Feedback Imediato:** Toast notifications e atualização visual
4. **Backup Automático:** Backend cria backup antes de modificar
5. **Validação Robusta:** Verifica existência antes de adicionar/remover

## 🔮 Melhorias Futuras

- [ ] Auditoria de ações de administradores de configuração
- [ ] Sincronização com Discord/Steam
- [ ] Templates de configuração pré-definidos
- [ ] Histórico de mudanças
- [ ] Exportação/importação de configurações
- [ ] Níveis de permissão (diferentes tipos de admin config) 