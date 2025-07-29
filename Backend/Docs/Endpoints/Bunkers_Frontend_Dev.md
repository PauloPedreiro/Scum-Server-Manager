# 🚀 Atualização do Sistema de Bunkers - Frontend Dev

## 📋 Resumo das Modificações

O sistema de bunkers foi **completamente reformulado** para incluir um banco de dados persistente e formatação detalhada. Agora o sistema é muito mais inteligente e fornece informações completas sobre o status dos bunkers.

## 🔄 Principais Mudanças

### 1. **Banco de Dados Persistente**
- **Antes:** Dados temporários baseados apenas no log atual
- **Agora:** Banco de dados persistente em `src/data/bunkers/bunkers.json`
- **Benefício:** Informações mantidas entre reinicializações do servidor

### 2. **Formatação Detalhada no Discord**
- **Antes:** Lista simples de nomes dos bunkers
- **Agora:** Informações completas com status, tempo, coordenadas

### 3. **Controle de Processamento**
- **Antes:** Processava logs repetidamente
- **Agora:** Evita reprocessamento desnecessário

## 📊 Estrutura de Dados Atualizada

### Resposta da API - GET `/api/bunkers/status`

```json
{
  "success": true,
  "message": "Status dos bunkers recuperado com sucesso.",
  "data": {
    "active": [
      {
        "name": "A1",
        "status": "active",
        "activated": "00h 00m 00s",
        "coordinates": {
          "x": -348529.312,
          "y": -469201.781,
          "z": 4247.645
        },
        "lastUpdate": "2025.07.15-20.16.51",
        "activationTime": "2025.07.15-20.16.51"
      }
    ],
    "locked": [
      {
        "name": "D1",
        "status": "locked",
        "nextActivation": "21h 53m 18s",
        "coordinates": {
          "x": -537889.562,
          "y": 540004.312,
          "z": 81279.648
        },
        "lastUpdate": "2025.07.15-20.16.51"
      }
    ],
    "lastUpdate": "2025.07.15-20.16.51"
  },
  "logFile": "gameplay_2025.07.15.log"
}
```

## 🎯 Novos Campos Disponíveis

### Para Bunkers Ativos:
- `status`: Sempre "active"
- `activated`: Tempo desde ativação (ex: "00h 00m 00s")
- `coordinates`: Objeto com x, y, z (pode ser null)
- `lastUpdate`: Timestamp da última atualização
- `activationTime`: Timestamp da ativação
- `activationMethod`: "keycard" (quando aplicável)

### Para Bunkers Bloqueados:
- `status`: Sempre "locked"
- `nextActivation`: Tempo até próxima ativação
- `coordinates`: Objeto com x, y, z
- `lastUpdate`: Timestamp da última atualização

## 💡 Sugestões para o Frontend

### 1. **Exibição de Status**
```javascript
// Exemplo de como exibir bunkers ativos
bunkers.active.forEach(bunker => {
    console.log(`${bunker.name} - ${bunker.status}`);
    console.log(`Ativado: ${bunker.activated}`);
    if (bunker.coordinates) {
        console.log(`Localização: ${bunker.coordinates.x}, ${bunker.coordinates.y}, ${bunker.coordinates.z}`);
    }
});
```

### 2. **Cálculo de Tempo Decorrido**
```javascript
// Função para calcular tempo decorrido desde ativação
function calculateTimeElapsed(activationTime) {
    if (!activationTime) return null;
    
    const now = new Date();
    const activation = new Date(activationTime.replace(/(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})\.(\d{2})/, '$1-$2-$3T$4:$5:$6.000Z'));
    const diffMs = now.getTime() - activation.getTime();
    
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
    
    return `${hours.toString().padStart(2, '0')}h ${minutes.toString().padStart(2, '0')}m ${seconds.toString().padStart(2, '0')}s`;
}
```

### 3. **Interface Sugerida**
```javascript
// Componente React/Vue para exibir bunkers
function BunkerStatus({ bunkers }) {
    return (
        <div className="bunker-status">
            <h3>🏰 Status dos Bunkers</h3>
            
            {/* Bunkers Ativos */}
            <div className="active-bunkers">
                <h4>🟢 Ativos ({bunkers.active.length})</h4>
                {bunkers.active.map(bunker => (
                    <div key={bunker.name} className="bunker-card active">
                        <h5>{bunker.name} Bunker</h5>
                        <p>Status: Ativo</p>
                        <p>Ativado: {bunker.activated}</p>
                        {bunker.activationMethod && (
                            <p>Método: Via Keycard</p>
                        )}
                        {bunker.coordinates && (
                            <p>Coordenadas: X={bunker.coordinates.x} Y={bunker.coordinates.y} Z={bunker.coordinates.z}</p>
                        )}
                    </div>
                ))}
            </div>
            
            {/* Bunkers Bloqueados */}
            <div className="locked-bunkers">
                <h4>🔴 Bloqueados ({bunkers.locked.length})</h4>
                {bunkers.locked.map(bunker => (
                    <div key={bunker.name} className="bunker-card locked">
                        <h5>{bunker.name} Bunker</h5>
                        <p>Status: Bloqueado</p>
                        <p>Próxima ativação: {bunker.nextActivation}</p>
                        {bunker.coordinates && (
                            <p>Coordenadas: X={bunker.coordinates.x} Y={bunker.coordinates.y} Z={bunker.coordinates.z}</p>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
```

## 🔧 Endpoints Disponíveis

### GET `/api/bunkers/status`
- **Descrição:** Obtém status atual dos bunkers
- **Uso:** Para exibir informações em tempo real
- **Cache:** Sistema evita reprocessamento desnecessário

### POST `/api/bunkers/force-update`
- **Descrição:** Força atualização sem enviar webhook
- **Uso:** Para atualizar dados manualmente
- **Resposta:** Mesma estrutura do GET /status

## 📱 Exemplo de Integração

```javascript
// Função para buscar status dos bunkers
async function fetchBunkerStatus() {
    try {
        const response = await fetch('/api/bunkers/status');
        const data = await response.json();
        
        if (data.success) {
            return data.data;
        } else {
            console.error('Erro ao buscar status dos bunkers:', data.message);
            return null;
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        return null;
    }
}

// Uso no componente
useEffect(() => {
    const loadBunkers = async () => {
        const bunkerData = await fetchBunkerStatus();
        if (bunkerData) {
            setBunkers(bunkerData);
        }
    };
    
    loadBunkers();
    // Atualizar a cada 5 minutos
    const interval = setInterval(loadBunkers, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
}, []);
```

## 🎨 Estilos CSS Sugeridos

```css
.bunker-status {
    padding: 20px;
    background: #1a1a1a;
    border-radius: 8px;
}

.bunker-card {
    padding: 15px;
    margin: 10px 0;
    border-radius: 6px;
    border-left: 4px solid;
}

.bunker-card.active {
    background: #1a2e1a;
    border-left-color: #4caf50;
}

.bunker-card.locked {
    background: #2e1a1a;
    border-left-color: #f44336;
}

.bunker-card h5 {
    margin: 0 0 10px 0;
    color: #fff;
}

.bunker-card p {
    margin: 5px 0;
    color: #ccc;
    font-size: 14px;
}
```

## ⚠️ Notas Importantes

1. **Compatibilidade:** A API mantém compatibilidade com versões anteriores
2. **Performance:** Sistema otimizado para evitar reprocessamento
3. **Dados Persistidos:** Informações mantidas entre reinicializações
4. **Tempo Real:** Atualizações automáticas via webhook Discord
5. **Coordenadas:** Podem ser null para bunkers sem localização

## 🚀 Próximos Passos

1. **Implementar interface** com os novos dados
2. **Adicionar cálculos de tempo** decorrido
3. **Criar visualizações** para coordenadas (mapa)
4. **Implementar atualizações** em tempo real
5. **Adicionar filtros** por status (ativo/bloqueado)

O sistema agora é muito mais robusto e fornece todas as informações necessárias para uma interface completa e detalhada! 🏰✨ 