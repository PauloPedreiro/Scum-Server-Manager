# 🔐 Documentação - Endpoint de Permissão do Comando /tm

## 📋 Visão Geral

Este endpoint permite atualizar a permissão do comando `/tm` para um jogador específico. A coluna `permissao` na tabela `players` controla se o jogador pode ou não usar o comando `/tm` no servidor SCUM.

---

## 🎯 **PUT/PATCH /api/players/{steam_id}/permissao**

Atualiza a permissão do comando `/tm` para um jogador na tabela `players`.

### **URL Base**
```
http://192.168.100.3:3000/api/players/{steam_id}/permissao
```

**Exemplo:**
```
http://192.168.100.3:3000/api/players/76561198040636105/permissao
```

*(Substitua `192.168.100.3` pela URL do seu ambiente de produção)*

---

## 📡 **Especificações**

### **Métodos HTTP Suportados**
```
PUT
PATCH
```
*(Ambos os métodos funcionam da mesma forma)*

### **Headers Necessários**
```
Content-Type: application/json
```

### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Local | Descrição | Exemplo |
|-----------|------|-------------|-------|-----------|---------|
| `steam_id` | string | ✅ Sim | Path | Steam ID do jogador | `76561198040636105` |
| `permissao` | number | ✅ Sim | Body | Valor da permissão (`0` ou `1`) | `1` |

---

## 📝 **Body da Requisição**

### **Formato JSON**
```json
{
  "permissao": 1
}
```

### **Valores Válidos**
- **`0`**: Jogador **NÃO pode** usar o comando `/tm` (permissão desativada)
- **`1`**: Jogador **PODE** usar o comando `/tm` (permissão ativada)

---

## ✅ **Respostas**

### **Resposta de Sucesso (200 OK)**

**Status HTTP:** `200`

**Body:**
```json
{
  "success": true,
  "message": "Permissão do comando /tm ativada com sucesso",
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "player_id": 230,
    "first_seen": "2025-10-27 22:21:01",
    "last_seen": "2025-10-31 02:53:09",
    "total_sessions": 34,
    "total_playtime": 9.928,
    "is_new_player": false,
    "notification_sent": true,
    "permissao": 1,
    "created_at": "2025-10-27 22:21:01"
  }
}
```

**Observações:**
- O campo `message` varia conforme o valor de `permissao`:
  - `permissao: 1` → "Permissão do comando /tm ativada com sucesso"
  - `permissao: 0` → "Permissão do comando /tm desativada com sucesso"
- O campo `data` contém todos os dados atualizados do jogador

---

### **Resposta de Erro (400 Bad Request) - Campo Obrigatório**

**Status HTTP:** `400`

**Body:**
```json
{
  "success": false,
  "error": "Campo 'permissao' é obrigatório"
}
```

**Quando ocorre:** O campo `permissao` não foi enviado no body.

---

### **Resposta de Erro (400 Bad Request) - Valor Inválido**

**Status HTTP:** `400`

**Body:**
```json
{
  "success": false,
  "error": "Campo 'permissao' deve ser 0 ou 1"
}
```

**Quando ocorre:** O valor enviado não é `0` ou `1`.

---

### **Resposta de Erro (404 Not Found)**

**Status HTTP:** `404`

**Body:**
```json
{
  "success": false,
  "error": "Jogador com steam_id 76561198040636105 não encontrado"
}
```

**Quando ocorre:** O `steam_id` fornecido não existe na tabela `players`.

---

### **Resposta de Erro (500 Internal Server Error)**

**Status HTTP:** `500`

**Body:**
```json
{
  "success": false,
  "error": "Erro específico"
}
```

**Quando ocorre:** Erro interno do servidor (banco de dados, configuração, etc.).

---

## 💻 **Exemplos de Implementação**

### **JavaScript/TypeScript (Fetch API)**

```typescript
/**
 * Atualiza a permissão do comando /tm para um jogador
 * @param steamId - Steam ID do jogador
 * @param permissao - 0 (desativado) ou 1 (ativado)
 * @returns Dados atualizados do jogador
 */
const updatePlayerPermissao = async (
  steamId: string, 
  permissao: 0 | 1
): Promise<any> => {
  try {
    const response = await fetch(
      `http://192.168.100.3:3000/api/players/${steamId}/permissao`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          permissao
        })
      }
    );

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Erro ao atualizar permissão');
    }

    return data.data;
  } catch (error) {
    console.error('Erro ao atualizar permissão:', error);
    throw error;
  }
};

// Uso:
// Ativar permissão
await updatePlayerPermissao('76561198040636105', 1);

// Desativar permissão
await updatePlayerPermissao('76561198040636105', 0);
```

---

### **TypeScript/React (Axios)**

```typescript
import axios, { AxiosError } from 'axios';

interface UpdatePermissaoResponse {
  success: boolean;
  message: string;
  data: {
    steam_id: string;
    player_name: string;
    player_id: number;
    first_seen: string;
    last_seen: string;
    total_sessions: number;
    total_playtime: number;
    is_new_player: boolean;
    notification_sent: boolean;
    permissao: 0 | 1;
    created_at: string;
  };
}

interface ErrorResponse {
  success: false;
  error: string;
}

/**
 * Atualiza a permissão do comando /tm para um jogador
 */
const updatePlayerPermissao = async (
  baseUrl: string,
  steamId: string,
  permissao: 0 | 1
): Promise<UpdatePermissaoResponse['data']> => {
  try {
    const response = await axios.put<UpdatePermissaoResponse>(
      `${baseUrl}/api/players/${steamId}/permissao`,
      { permissao }
    );
    
    return response.data.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data as ErrorResponse;
      throw new Error(errorData?.error || error.message);
    }
    throw error;
  }
};

// Exemplo de uso em componente React
const PlayerPermissaoComponent: React.FC<{ steamId: string }> = ({ steamId }) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [permissao, setPermissao] = React.useState<0 | 1>(0);

  const handleTogglePermissao = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const newPermissao: 0 | 1 = permissao === 1 ? 0 : 1;
      const playerData = await updatePlayerPermissao(
        'http://192.168.100.3:3000',
        steamId,
        newPermissao
      );
      
      setPermissao(playerData.permissao);
      alert(`Permissão ${newPermissao === 1 ? 'ativada' : 'desativada'} com sucesso!`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <p>Permissão atual: {permissao === 1 ? '✅ Ativada' : '❌ Desativada'}</p>
      <button 
        onClick={handleTogglePermissao} 
        disabled={loading}
      >
        {loading ? 'Processando...' : permissao === 1 ? 'Desativar' : 'Ativar'}
      </button>
      {error && <div style={{ color: 'red' }}>{error}</div>}
    </div>
  );
};
```

---

### **JavaScript/React Hooks**

```typescript
import { useState } from 'react';

const usePlayerPermissao = (baseUrl: string, steamId: string) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updatePermissao = async (permissao: 0 | 1) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${baseUrl}/api/players/${steamId}/permissao`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ permissao })
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Erro ao atualizar permissão');
      }

      return data.data;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    updatePermissao,
    loading,
    error
  };
};

// Uso no componente
const MyComponent = () => {
  const { updatePermissao, loading, error } = usePlayerPermissao(
    'http://192.168.100.3:3000',
    '76561198040636105'
  );

  const handleActivate = () => updatePermissao(1);
  const handleDeactivate = () => updatePermissao(0);

  return (
    <div>
      <button onClick={handleActivate} disabled={loading}>
        Ativar
      </button>
      <button onClick={handleDeactivate} disabled={loading}>
        Desativar
      </button>
      {error && <p>Erro: {error}</p>}
    </div>
  );
};
```

---

## 🔍 **Tratamento de Erros**

### **Estrutura Recomendada**

```typescript
try {
  const playerData = await updatePlayerPermissao(steamId, 1);
  // Sucesso
} catch (error: any) {
  if (error.message.includes('não encontrado')) {
    // Jogador não existe (404)
    console.error('Jogador não encontrado');
  } else if (error.message.includes('deve ser 0 ou 1')) {
    // Valor inválido (400)
    console.error('Valor de permissão inválido');
  } else if (error.message.includes('obrigatório')) {
    // Campo faltando (400)
    console.error('Campo permissao é obrigatório');
  } else {
    // Erro genérico (500)
    console.error('Erro interno do servidor');
  }
}
```

---

## 📊 **Validações no Frontend**

### **Antes de Enviar a Requisição**

```typescript
const validatePermissao = (steamId: string, permissao: any): string | null => {
  // Validar Steam ID
  if (!steamId || steamId.trim() === '') {
    return 'Steam ID é obrigatório';
  }

  // Validar formato do Steam ID (apenas números)
  if (!/^\d+$/.test(steamId)) {
    return 'Steam ID deve conter apenas números';
  }

  // Validar permissao
  if (permissao === null || permissao === undefined) {
    return 'Campo permissao é obrigatório';
  }

  // Validar valor da permissão
  if (permissao !== 0 && permissao !== 1) {
    return 'Campo permissao deve ser 0 ou 1';
  }

  return null; // Válido
};

// Uso
const error = validatePermissao(steamId, permissao);
if (error) {
  alert(error);
  return;
}
```

---

## 🎨 **Exemplo Completo de UI**

```typescript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Player {
  steam_id: string;
  player_name: string;
  permissao: 0 | 1;
}

const PlayerPermissaoToggle: React.FC<{ player: Player }> = ({ player }) => {
  const [permissao, setPermissao] = useState<0 | 1>(player.permissao);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const BASE_URL = 'http://192.168.100.3:3000';

  const handleToggle = async () => {
    const newPermissao: 0 | 1 = permissao === 1 ? 0 : 1;
    
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await axios.put(
        `${BASE_URL}/api/players/${player.steam_id}/permissao`,
        { permissao: newPermissao }
      );

      if (response.data.success) {
        setPermissao(newPermissao);
        setSuccess(true);
        
        // Limpar mensagem de sucesso após 3 segundos
        setTimeout(() => setSuccess(false), 3000);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '16px', border: '1px solid #ddd', borderRadius: '8px' }}>
      <h3>{player.player_name}</h3>
      <p>Steam ID: {player.steam_id}</p>
      
      <div style={{ margin: '16px 0' }}>
        <label>
          Permissão do comando /tm:
          <strong style={{ marginLeft: '8px', color: permissao === 1 ? 'green' : 'red' }}>
            {permissao === 1 ? '✅ Ativada' : '❌ Desativada'}
          </strong>
        </label>
      </div>

      <button
        onClick={handleToggle}
        disabled={loading}
        style={{
          padding: '8px 16px',
          backgroundColor: permissao === 1 ? '#f44336' : '#4caf50',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer'
        }}
      >
        {loading ? 'Processando...' : permissao === 1 ? 'Desativar' : 'Ativar'}
      </button>

      {success && (
        <div style={{ marginTop: '8px', color: 'green' }}>
          ✅ Permissão atualizada com sucesso!
        </div>
      )}

      {error && (
        <div style={{ marginTop: '8px', color: 'red' }}>
          ❌ Erro: {error}
        </div>
      )}
    </div>
  );
};

export default PlayerPermissaoToggle;
```

---

## ⚠️ **Observações Importantes**

### **1. Diferença entre Sistemas de Permissão**

Este endpoint atualiza a coluna `permissao` na tabela `players`, que é **diferente** do sistema de permissões (`player_permissions`):

- **`permissao` (tabela `players`):** Controla apenas o comando `/tm`
- **`player_permissions` (tabela separada):** Controla outros tipos de permissões (admin, banned, exclusive, etc.)

### **2. Valores da Permissão**

- **`0`**: Jogador **NÃO pode** usar `/tm`
- **`1`**: Jogador **PODE** usar `/tm`

### **3. Validações Automáticas**

O backend valida automaticamente:
- ✅ Campo `permissao` foi fornecido
- ✅ Valor é `0` ou `1`
- ✅ Jogador existe na tabela `players`

### **4. Retorno de Dados**

Após atualização bem-sucedida, o endpoint retorna **todos os dados atualizados** do jogador, incluindo a nova permissão.

---

## 🧪 **Testando o Endpoint**

### **Via cURL**

```bash
# Ativar permissão
curl -X PUT http://192.168.100.3:3000/api/players/76561198040636105/permissao \
  -H "Content-Type: application/json" \
  -d '{"permissao": 1}'

# Desativar permissão
curl -X PUT http://192.168.100.3:3000/api/players/76561198040636105/permissao \
  -H "Content-Type: application/json" \
  -d '{"permissao": 0}'
```

### **Via Postman/Insomnia**

1. **Método:** `PUT` ou `PATCH`
2. **URL:** `http://192.168.100.3:3000/api/players/76561198040636105/permissao`
3. **Headers:**
   - `Content-Type: application/json`
4. **Body (raw JSON):**
   ```json
   {
     "permissao": 1
   }
   ```

---

## 📞 **Suporte**

Em caso de dúvidas ou problemas:

1. Verifique se o backend está rodando
2. Confirme que o `steam_id` existe na tabela `players`
3. Verifique os logs do backend para mais detalhes
4. Entre em contato com o time de backend

---

## 📋 **Checklist de Implementação**

- [ ] Configurar URL base da API no frontend
- [ ] Criar função para atualizar permissão
- [ ] Implementar tratamento de erros (400, 404, 500)
- [ ] Adicionar validação no frontend antes de enviar
- [ ] Implementar feedback visual (loading, success, error)
- [ ] Testar com diferentes `steam_id`
- [ ] Testar valores inválidos de `permissao`
- [ ] Testar com jogador inexistente

---

**Última atualização:** 2025-01-15  
**Versão da API:** 1.10.0

