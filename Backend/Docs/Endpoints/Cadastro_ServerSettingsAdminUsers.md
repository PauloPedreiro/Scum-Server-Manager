# 📋 Endpoints do ServerSettingsAdminUsers.ini

## 🎯 Visão Geral

Este documento descreve os endpoints para gerenciar o arquivo **ServerSettingsAdminUsers.ini** do servidor SCUM. Este arquivo contém a lista de administradores do servidor com permissões de gerenciamento.

---

## 🔗 Endpoints Disponíveis

### **Base URL:** `http://localhost:3000/api/configserver/ServerSettingsAdminUsers.ini`

---

## 📤 **GET** `/api/configserver/ServerSettingsAdminUsers.ini`

### **Descrição**
Consulta a lista atual de administradores do servidor.

### **Headers**
```
Content-Type: application/json
```

### **Resposta de Sucesso**
```json
{
  "success": true,
  "adminUsers": [
    {
      "steamId": "76561198012345678[setgodmode]",
      "playerName": "Nome do Jogador"
    },
    {
      "steamId": "76561198087654321[setgodmode]",
      "playerName": "Outro Jogador"
    }
  ],
  "stats": {
    "size": 1024,
    "modified": "2025-01-27T10:30:00.000Z",
    "created": "2025-01-27T10:00:00.000Z"
  }
}
```

### **Resposta de Erro (Arquivo não encontrado)**
```json
{
  "success": false,
  "error": "Arquivo não encontrado"
}
```

### **Status Codes**
- `200` - Sucesso
- `404` - Arquivo não encontrado
- `500` - Erro interno do servidor

---

## 📥 **POST** `/api/configserver/ServerSettingsAdminUsers.ini`

### **Descrição**
Adiciona um novo administrador à lista.

### **Headers**
```
Content-Type: application/json
```

### **Body (JSON)**
```json
{
  "steamId": "76561198012345678"
}
```

### **Validações**
- `steamId` deve ser uma string válida
- SteamID deve ter exatamente 17 dígitos numéricos
- Sistema salva apenas o SteamID puro (17 dígitos)

### **Resposta de Sucesso**
```json
{
  "success": true,
  "message": "Admin adicionado com sucesso",
  "steamId": "76561198012345678",
  "steamIdSaved": "76561198012345678",
  "backupCreated": "ServerSettingsAdminUsers_ini_2025-01-27_10-30-00.backup"
}
```

### **Resposta de Erro (SteamID já existe)**
```json
{
  "success": false,
  "error": "SteamID já existe no ServerSettingsAdminUsers.ini"
}
```

### **Resposta de Erro (SteamID inválido)**
```json
{
  "success": false,
  "error": "steamId é obrigatório e deve ser uma string"
}
```

### **Status Codes**
- `200` - Sucesso
- `400` - SteamID inválido ou já existe
- `500` - Erro interno do servidor

---

## 🗑️ **DELETE** `/api/configserver/ServerSettingsAdminUsers.ini`

### **Descrição**
Remove um administrador da lista.

### **Headers**
```
Content-Type: application/json
```

### **Body (JSON)**
```json
{
  "steamId": "76561198012345678"
}
```

### **Resposta de Sucesso**
```json
{
  "success": true,
  "message": "Admin removido com sucesso",
  "backupCreated": "ServerSettingsAdminUsers_ini_2025-01-27_10-30-00.backup"
}
```

### **Resposta de Erro (SteamID não encontrado)**
```json
{
  "success": false,
  "error": "SteamID não encontrado no ServerSettingsAdminUsers.ini"
}
```

### **Resposta de Erro (Arquivo não encontrado)**
```json
{
  "success": false,
  "error": "Arquivo ServerSettingsAdminUsers.ini não encontrado"
}
```

### **Status Codes**
- `200` - Sucesso
- `400` - SteamID inválido
- `404` - SteamID não encontrado ou arquivo não existe
- `500` - Erro interno do servidor

---

## 📝 **PUT** `/api/configserver/ServerSettingsAdminUsers.ini`

### **Descrição**
Substitui completamente o conteúdo do arquivo.

### **Headers**
```
Content-Type: application/json
```

### **Body (JSON)**
```json
{
  "content": [
    "76561198012345678[setgodmode]",
    "76561198087654321[setgodmode]",
    "76561198011111111[setgodmode]"
  ]
}
```

### **Validações**
- `content` deve ser um array de strings
- Cada linha deve ser um SteamID válido
- Sistema adiciona automaticamente `[setgodmode]` se não presente

### **Resposta de Sucesso**
```json
{
  "success": true,
  "message": "Arquivo ServerSettingsAdminUsers.ini atualizado com sucesso",
  "backupCreated": "ServerSettingsAdminUsers_ini_2025-01-27_10-30-00.backup",
  "linesCount": 3
}
```

### **Resposta de Erro (Conteúdo inválido)**
```json
{
  "success": false,
  "error": "Conteúdo deve ser um array de linhas"
}
```

### **Status Codes**
- `200` - Sucesso
- `400` - Conteúdo inválido
- `500` - Erro interno do servidor

---

## 🧪 Casos de Teste

### **1. Consultar Lista de Admins**
```bash
curl -X GET http://localhost:3000/api/configserver/ServerSettingsAdminUsers.ini
```

### **2. Adicionar Novo Admin**
```bash
curl -X POST http://localhost:3000/api/configserver/ServerSettingsAdminUsers.ini \
  -H "Content-Type: application/json" \
  -d '{"steamId": "76561198012345678"}'
```

### **3. Remover Admin**
```bash
curl -X DELETE http://localhost:3000/api/configserver/ServerSettingsAdminUsers.ini \
  -H "Content-Type: application/json" \
  -d '{"steamId": "76561198012345678"}'
```

### **4. Substituir Lista Completa**
```bash
curl -X PUT http://localhost:3000/api/configserver/ServerSettingsAdminUsers.ini \
  -H "Content-Type: application/json" \
  -d '{"content": ["76561198012345678[setgodmode]", "76561198087654321[setgodmode]"]}'
```

---

## 🎨 Implementação Frontend

### **Exemplo de Interface Sugerida**

```javascript
// Componente React/Vue/Angular
const ServerSettingsAdminUsers = () => {
  const [adminUsers, setAdminUsers] = useState([]);
  const [newSteamId, setNewSteamId] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Buscar lista de admins
  const fetchAdminUsers = async () => {
    try {
      const response = await fetch('/api/configserver/ServerSettingsAdminUsers.ini');
      const data = await response.json();
      
      if (data.success) {
        setAdminUsers(data.adminUsers);
      }
    } catch (error) {
      console.error('Erro ao buscar admins:', error);
    }
  };

  // Adicionar admin
  const addAdmin = async () => {
    setLoading(true);
    setMessage('');
    
    try {
      const response = await fetch('/api/configserver/ServerSettingsAdminUsers.ini', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ steamId: newSteamId }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMessage(data.message);
        setNewSteamId('');
        fetchAdminUsers(); // Recarregar lista
      } else {
        setMessage(data.error);
      }
    } catch (error) {
      setMessage('Erro ao adicionar admin');
    } finally {
      setLoading(false);
    }
  };

  // Remover admin
  const removeAdmin = async (steamId) => {
    if (!confirm('Tem certeza que deseja remover este admin?')) return;
    
    setLoading(true);
    setMessage('');
    
    try {
      const response = await fetch('/api/configserver/ServerSettingsAdminUsers.ini', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ steamId }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMessage(data.message);
        fetchAdminUsers(); // Recarregar lista
      } else {
        setMessage(data.error);
      }
    } catch (error) {
      setMessage('Erro ao remover admin');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-users-config">
      <h2>👑 Administradores do Servidor</h2>
      
      <div className="add-admin-form">
        <div className="form-group">
          <label>Steam ID do Novo Admin:</label>
          <input
            type="text"
            value={newSteamId}
            onChange={(e) => setNewSteamId(e.target.value)}
            placeholder="76561198012345678"
            className="form-control"
          />
        </div>
        
        <button 
          onClick={addAdmin} 
          disabled={loading || !newSteamId}
          className="btn btn-primary"
        >
          {loading ? 'Adicionando...' : 'Adicionar Admin'}
        </button>
      </div>
      
      {message && (
        <div className={`alert ${message.includes('sucesso') ? 'alert-success' : 'alert-danger'}`}>
          {message}
        </div>
      )}
      
      <div className="admin-list">
        <h3>Admins Atuais ({adminUsers.length})</h3>
        
        {adminUsers.length === 0 ? (
          <p>Nenhum administrador cadastrado.</p>
        ) : (
          <div className="admin-grid">
            {adminUsers.map((admin, index) => (
              <div key={index} className="admin-card">
                <div className="admin-info">
                  <strong>Steam ID:</strong> {admin.steamId}
                  {admin.playerName && (
                    <div><strong>Nome:</strong> {admin.playerName}</div>
                  )}
                </div>
                <button 
                  onClick={() => removeAdmin(admin.steamId)}
                  className="btn btn-danger btn-sm"
                  disabled={loading}
                >
                  Remover
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
```

---

## 🔧 Funcionalidades Especiais

### **Sufixo Automático**
- Sistema adiciona automaticamente `[setgodmode]` ao SteamID
- Aceita SteamID com ou sem sufixo na entrada
- Remove sufixos antigos e adiciona o correto

### **Validação de SteamID**
- Verifica se tem 17 dígitos numéricos
- Remove caracteres especiais automaticamente
- Previne duplicatas baseado no número do SteamID

### **Backup Automático**
- Cria backup antes de qualquer modificação
- Nome do backup inclui timestamp
- Backup salvo em `src/data/configserver/backups/`

### **Integração com Players**
- Busca nomes dos jogadores no `players.json`
- Exibe nome do jogador quando disponível
- Fallback para SteamID quando nome não encontrado

---

## 📊 Estrutura do Arquivo

### **Formato do Arquivo**
```
76561198012345678[setgodmode]
76561198087654321[setgodmode]
76561198011111111[setgodmode]
```

### **Regras de Formato**
- Uma linha por SteamID
- Sufixo `[setgodmode]` obrigatório
- Apenas números no SteamID (17 dígitos)
- Sem espaços extras

---

## 🚨 Tratamento de Erros

### **Erros Comuns**
1. **SteamID inválido:** Retorna 400 com mensagem específica
2. **SteamID já existe:** Retorna 400 com aviso
3. **Arquivo não encontrado:** Retorna 404
4. **Permissões:** Verificar acesso ao arquivo
5. **Formato inválido:** Validação de entrada

### **Boas Práticas**
- Sempre validar SteamID antes de enviar
- Mostrar feedback visual para o usuário
- Implementar confirmação para remoção
- Cache local da lista de admins
- Refresh automático após operações

---

## 📝 Notas Importantes

1. **Permissões:** Apenas admins podem gerenciar outros admins
2. **Sufixo Obrigatório:** `[setgodmode]` é adicionado automaticamente
3. **Backup Automático:** Sistema cria backup antes de modificar
4. **Validação:** SteamID deve ter exatamente 17 dígitos
5. **Integração:** Usado pelo servidor SCUM para permissões

---

## 🎯 Checklist de Implementação

- [ ] Interface para listar admins atuais
- [ ] Campo de input para novo SteamID
- [ ] Validação de SteamID no frontend
- [ ] Botão para adicionar admin
- [ ] Botão para remover admin (com confirmação)
- [ ] Feedback visual de sucesso/erro
- [ ] Loading state durante operações
- [ ] Tratamento de erros de rede
- [ ] Exibição de nomes dos jogadores
- [ ] Refresh automático da lista
- [ ] Confirmação antes de remover admin

---

**Desenvolvedor Frontend:** Use este documento como referência completa para implementar a interface de gerenciamento dos administradores do servidor! 🚀 