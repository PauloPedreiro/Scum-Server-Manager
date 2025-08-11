# Configuração do Servidor

## Como alterar o IP do Backend

Para alterar o IP do servidor backend, edite o arquivo `public/config.json`:

```json
{
  "backend": {
    "host": "SEU_IP_AQUI",
    "port": 3000,
    "protocol": "http"
  },
  "frontend": {
    "port": 5173,
    "host": "0.0.0.0"
  }
}
```

### Exemplos:

**Para servidor local:**
```json
"host": "127.0.0.1"
```

**Para servidor na rede:**
```json
"host": "192.168.100.15"
```

**Para servidor externo:**
```json
"host": "meuservidor.com"
```

### Após alterar:

1. Salve o arquivo `config.json`
2. Reinicie o servidor: `npm run dev`
3. O Vite irá automaticamente usar a nova configuração

### Configurações disponíveis:

- `backend.host`: IP ou domínio do servidor backend
- `backend.port`: Porta do servidor backend (padrão: 3000)
- `backend.protocol`: Protocolo (http ou https)
- `frontend.port`: Porta do frontend (padrão: 5173)
- `frontend.host`: Host do frontend (padrão: 0.0.0.0 para acesso externo) 