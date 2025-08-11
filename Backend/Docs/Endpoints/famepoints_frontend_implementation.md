# Implementação Frontend - Endpoint Famepoints

## 📋 Prompt para o Desenvolvedor Frontend

### Objetivo
Implementar a integração com o endpoint de famepoints para exibir dados de pontos de fama dos jogadores no painel administrativo.

---

## 🎯 Endpoint Principal

### URL Base
```
GET http://localhost:3000/api/famepoints
```

### Comportamento do Endpoint

#### 1. **Primeira Chamada (Log Novo)**
```json
{
    "success": true,
    "message": "Dados de famepoints processados com sucesso",
    "data": [
        {
            "playerName": "Aqu1n0",
            "steamId": "76561197995901898",
            "totalFame": 588.845947,
            "timestamp": "2025-07-14T23:53:08.970Z"
        },
        {
            "playerName": "ARKANJO",
            "steamId": "76561198094354554",
            "totalFame": 771.324768,
            "timestamp": "2025-07-14T23:53:08.970Z"
        }
    ]
}
```

#### 2. **Chamadas Subsequentes (Sem Log Novo)**
```json
{
    "success": true,
    "message": "Arquivo já processado",
    "data": []
}
```

---

## 🚀 Implementação Sugerida

### 1. **Função de Fetch Básica**
```javascript
const fetchFamepoints = async () => {
    try {
        const response = await fetch('http://localhost:3000/api/famepoints');
        const data = await response.json();
        
        if (data.success) {
            if (data.data.length > 0) {
                // Dados processados com sucesso
                return data.data;
            } else {
                // Arquivo já processado - buscar dados salvos
                return await fetchSavedFamepoints();
            }
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('Erro ao buscar famepoints:', error);
        throw error;
    }
};
```

### 2. **Função para Buscar Dados Salvos**
```javascript
const fetchSavedFamepoints = async () => {
    try {
        // Endpoint alternativo para buscar dados salvos
        const response = await fetch('http://localhost:3000/api/famepoints/saved');
        const data = await response.json();
        return data.data || [];
    } catch (error) {
        console.error('Erro ao buscar dados salvos:', error);
        return [];
    }
};
```

### 3. **Hook React (se usando React)**
```javascript
import { useState, useEffect } from 'react';

const useFamepoints = () => {
    const [famepoints, setFamepoints] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const loadFamepoints = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const data = await fetchFamepoints();
            setFamepoints(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadFamepoints();
    }, []);

    return { famepoints, loading, error, refetch: loadFamepoints };
};
```

---

## 📊 Estrutura de Dados

### Tipo TypeScript (se aplicável)
```typescript
interface FamepointPlayer {
    playerName: string;
    steamId: string;
    totalFame: number;
    timestamp: string;
}

interface FamepointsResponse {
    success: boolean;
    message: string;
    data: FamepointPlayer[];
}
```

### Exemplo de Uso no Componente
```javascript
const FamepointsComponent = () => {
    const { famepoints, loading, error, refetch } = useFamepoints();

    if (loading) return <div>Carregando dados de fama...</div>;
    if (error) return <div>Erro: {error}</div>;

    return (
        <div>
            <h2>Pontos de Fama dos Jogadores</h2>
            <button onClick={refetch}>Atualizar</button>
            
            <table>
                <thead>
                    <tr>
                        <th>Jogador</th>
                        <th>Steam ID</th>
                        <th>Total Fame</th>
                        <th>Última Atualização</th>
                    </tr>
                </thead>
                <tbody>
                    {famepoints.map((player) => (
                        <tr key={player.steamId}>
                            <td>{player.playerName}</td>
                            <td>{player.steamId}</td>
                            <td>{player.totalFame.toFixed(2)}</td>
                            <td>{new Date(player.timestamp).toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};
```

---

## 🔄 Estratégias de Atualização

### 1. **Atualização Manual**
```javascript
// Botão para forçar atualização
const handleRefresh = async () => {
    // Deletar controle de processamento no backend
    await fetch('http://localhost:3000/api/famepoints/force-refresh', {
        method: 'POST'
    });
    
    // Recarregar dados
    await refetch();
};
```

### 2. **Atualização Automática**
```javascript
// Atualizar a cada 5 minutos
useEffect(() => {
    const interval = setInterval(() => {
        refetch();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
}, [refetch]);
```

### 3. **WebSocket (Futuro)**
```javascript
// Implementação futura para atualizações em tempo real
const useFamepointsWebSocket = () => {
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:3000/famepoints');
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'famepoints_updated') {
                refetch();
            }
        };

        return () => ws.close();
    }, []);
};
```

---

## 🎨 Sugestões de UI/UX

### 1. **Indicadores Visuais**
- **Verde**: Dados atualizados recentemente
- **Amarelo**: Dados podem estar desatualizados
- **Vermelho**: Erro na busca de dados

### 2. **Ordenação**
```javascript
// Ordenar por total de fama (maior primeiro)
const sortedFamepoints = famepoints.sort((a, b) => b.totalFame - a.totalFame);
```

### 3. **Filtros**
```javascript
// Filtrar por nome do jogador
const [searchTerm, setSearchTerm] = useState('');
const filteredFamepoints = famepoints.filter(player => 
    player.playerName.toLowerCase().includes(searchTerm.toLowerCase())
);
```

### 4. **Paginação**
```javascript
const [currentPage, setCurrentPage] = useState(1);
const itemsPerPage = 10;
const paginatedFamepoints = famepoints.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
);
```

---

## ⚠️ Considerações Importantes

### 1. **Tratamento de Estados**
- **Loading**: Mostrar spinner ou skeleton
- **Error**: Mostrar mensagem de erro com opção de retry
- **Empty**: Mostrar mensagem quando não há dados

### 2. **Performance**
- **Debounce**: Para busca em tempo real
- **Memoização**: Para evitar re-renders desnecessários
- **Lazy Loading**: Para grandes listas

### 3. **Acessibilidade**
- **ARIA labels**: Para leitores de tela
- **Keyboard navigation**: Para navegação por teclado
- **Color contrast**: Para usuários com deficiência visual

---

## 🔧 Endpoints Adicionais Úteis

### 1. **Análise Completa**
```
GET http://localhost:3000/api/famepoints/analysis
```
- Retorna histórico completo de todos os jogadores
- Útil para gráficos e análises detalhadas

### 2. **Forçar Reprocessamento**
```
POST http://localhost:3000/api/famepoints/force-refresh
```
- Força o reprocessamento do último log
- Útil quando há novos dados disponíveis

---

## 📝 Checklist de Implementação

- [ ] Implementar função de fetch básica
- [ ] Criar hook/context para gerenciar estado
- [ ] Implementar tratamento de erros
- [ ] Adicionar indicadores de loading
- [ ] Implementar ordenação e filtros
- [ ] Adicionar paginação (se necessário)
- [ ] Implementar atualização manual
- [ ] Adicionar atualização automática
- [ ] Testar diferentes cenários de resposta
- [ ] Implementar acessibilidade básica
- [ ] Adicionar testes unitários

---

## 🎯 Próximos Passos

1. **Implementar a integração básica**
2. **Testar com dados reais**
3. **Adicionar funcionalidades avançadas**
4. **Otimizar performance**
5. **Implementar testes**

---

**Dúvidas?** Consulte a documentação completa em `Docs/Endpoints/famepoints.md` ou entre em contato com o backend team. 