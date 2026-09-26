# 🔄 Endpoint de Restart Assíncrono

## 📋 Mudança Importante

O endpoint `/api/server/restart` agora executa de forma **assíncrona** para evitar timeout no frontend. O restart pode levar vários minutos, especialmente quando há Elevated Users para sincronizar.

## 🚀 Novo Comportamento

### **Antes (Síncrono)**
- Endpoint aguardava todo o processo de restart
- Timeout de 60 segundos no frontend
- Erro quando o restart demorava mais que 60 segundos

### **Agora (Assíncrono)**
- Endpoint retorna **imediatamente** após iniciar o restart
- Restart executa em background
- Frontend deve verificar o status periodicamente

## 📡 Resposta do Endpoint

### **Resposta Imediata (200)**

```json
{
  "success": true,
  "message": "Reinicialização iniciada. O processo pode levar vários minutos, especialmente se houver Elevated Users para sincronizar.",
  "status": "restarting",
  "note": "Use o endpoint /api/server/status para verificar o progresso do restart"
}
```

## 💻 Implementação no Frontend

### **Opção 1: Polling do Status**

```typescript
import axios from 'axios';

const restartServer = async () => {
  try {
    // Iniciar restart
    const response = await axios.post('/api/server/restart', {
      force: false,
      wait_timeout: 0  // Não aguardar
    });
    
    if (response.data.success) {
      console.log('Restart iniciado:', response.data.message);
      
      // Verificar status periodicamente
      const checkStatus = setInterval(async () => {
        try {
          const statusResponse = await axios.get('/api/server/status');
          const status = statusResponse.data.data;
          
          if (status.is_running) {
            console.log('Servidor reiniciado com sucesso!');
            clearInterval(checkStatus);
          }
        } catch (error) {
          console.error('Erro ao verificar status:', error);
        }
      }, 5000); // Verificar a cada 5 segundos
      
      // Limpar intervalo após 10 minutos (timeout de segurança)
      setTimeout(() => {
        clearInterval(checkStatus);
      }, 600000);
    }
  } catch (error) {
    console.error('Erro ao iniciar restart:', error);
  }
};
```

### **Opção 2: Com React Hook**

```typescript
import { useState, useEffect } from 'react';
import axios from 'axios';

const useServerRestart = () => {
  const [isRestarting, setIsRestarting] = useState(false);
  const [restartStatus, setRestartStatus] = useState<string>('idle');

  const restartServer = async () => {
    setIsRestarting(true);
    setRestartStatus('starting');
    
    try {
      const response = await axios.post('/api/server/restart', {
        force: false,
        wait_timeout: 0
      });
      
      if (response.data.success) {
        setRestartStatus('in_progress');
        
        // Verificar status periodicamente
        const checkInterval = setInterval(async () => {
          try {
            const statusResponse = await axios.get('/api/server/status');
            const status = statusResponse.data.data;
            
            if (status.is_running && isRestarting) {
              setRestartStatus('completed');
              setIsRestarting(false);
              clearInterval(checkInterval);
            }
          } catch (error) {
            console.error('Erro ao verificar status:', error);
          }
        }, 5000);
        
        // Timeout de segurança (10 minutos)
        setTimeout(() => {
          clearInterval(checkInterval);
          if (isRestarting) {
            setRestartStatus('timeout');
            setIsRestarting(false);
          }
        }, 600000);
      }
    } catch (error) {
      setRestartStatus('error');
      setIsRestarting(false);
      console.error('Erro ao iniciar restart:', error);
    }
  };

  return { restartServer, isRestarting, restartStatus };
};
```

### **Opção 3: Com Feedback Visual**

```typescript
const RestartButton = () => {
  const [isRestarting, setIsRestarting] = useState(false);
  const [restartProgress, setRestartProgress] = useState(0);

  const handleRestart = async () => {
    setIsRestarting(true);
    setRestartProgress(0);
    
    try {
      // Iniciar restart
      await axios.post('/api/server/restart', {
        force: false,
        wait_timeout: 0
      });
      
      // Simular progresso (opcional)
      let progress = 0;
      const progressInterval = setInterval(() => {
        progress += 2;
        if (progress <= 90) {
          setRestartProgress(progress);
        }
      }, 1000);
      
      // Verificar status
      const checkInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get('/api/server/status');
          const status = statusResponse.data.data;
          
          if (status.is_running) {
            clearInterval(progressInterval);
            clearInterval(checkInterval);
            setRestartProgress(100);
            setIsRestarting(false);
            
            // Mostrar mensagem de sucesso
            alert('Servidor reiniciado com sucesso!');
          }
        } catch (error) {
          console.error('Erro ao verificar status:', error);
        }
      }, 5000);
      
      // Timeout de segurança
      setTimeout(() => {
        clearInterval(progressInterval);
        clearInterval(checkInterval);
        if (isRestarting) {
          setIsRestarting(false);
          alert('Restart está demorando mais que o esperado. Verifique o status do servidor.');
        }
      }, 600000);
      
    } catch (error) {
      setIsRestarting(false);
      alert('Erro ao iniciar restart: ' + error.message);
    }
  };

  return (
    <div>
      <button 
        onClick={handleRestart} 
        disabled={isRestarting}
      >
        {isRestarting ? 'Reiniciando...' : 'Reiniciar Servidor'}
      </button>
      
      {isRestarting && (
        <div>
          <p>Reiniciando servidor... Isso pode levar vários minutos.</p>
          <progress value={restartProgress} max={100} />
          <p>{restartProgress}%</p>
        </div>
      )}
    </div>
  );
};
```

## ⏱️ Tempos Esperados

- **Restart sem Elevated Users**: 30-60 segundos
- **Restart com Elevated Users**: 2-5 minutos (pode levar até 90 segundos só para sincronização)
- **Restart com problemas de WAL/SHM**: Pode levar mais tempo devido ao sistema de retry

## 🔍 Verificação de Status

Use o endpoint `/api/server/status` para verificar o progresso:

```typescript
const checkServerStatus = async () => {
  const response = await axios.get('/api/server/status');
  const status = response.data.data;
  
  if (status.is_running) {
    console.log('Servidor está rodando');
  } else {
    console.log('Servidor está parado');
  }
};
```

## ⚠️ Observações Importantes

1. **Não aguarde a resposta**: O endpoint retorna imediatamente
2. **Verifique o status**: Use polling para verificar quando o restart terminar
3. **Timeout de segurança**: Configure um timeout máximo (ex: 10 minutos)
4. **Feedback ao usuário**: Mostre mensagens claras sobre o progresso
5. **Tratamento de erros**: Trate erros de rede e timeout adequadamente

## 📝 Exemplo Completo com Tratamento de Erros

```typescript
const restartServerWithRetry = async (maxRetries = 3) => {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await axios.post('/api/server/restart', {
        force: false,
        wait_timeout: 0
      }, {
        timeout: 10000  // 10 segundos para iniciar o restart
      });
      
      if (response.data.success) {
        console.log('Restart iniciado com sucesso');
        return { success: true, message: 'Restart iniciado' };
      }
    } catch (error) {
      if (attempt === maxRetries) {
        throw new Error('Falha ao iniciar restart após múltiplas tentativas');
      }
      console.warn(`Tentativa ${attempt} falhou, tentando novamente...`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
};
```

