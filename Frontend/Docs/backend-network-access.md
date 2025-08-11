# ⚠️ Ajuste Necessário no Backend para Acesso em Rede

O frontend do SCUM Server Manager está rodando em outro IP da rede (ex: `192.168.100.3:5173`) e precisa acessar a API do backend via IP (ex: `192.168.100.3:3000`).
Atualmente, o backend está ouvindo apenas em `localhost`, o que impede o acesso externo e resulta em erro de "Network Error" no frontend.

## ✅ O que precisa ser feito

**Altere o comando de inicialização do servidor para ouvir em todas as interfaces de rede (`0.0.0.0`), não apenas em `localhost`.**

### Exemplo para Express.js:

```js
// Antes:
app.listen(3000, () => {
  console.log('Servidor rodando em localhost:3000');
});

// Depois:
app.listen(3000, '0.0.0.0', () => {
  console.log('Servidor rodando em 0.0.0.0:3000 (acessível na rede)');
});
```

### Exemplo para Fastify:

```js
// Antes:
fastify.listen({ port: 3000 });

// Depois:
fastify.listen({ port: 3000, host: '0.0.0.0' });
```

## 🔥 Não esqueça:
- **Liberar a porta 3000 no firewall do Windows** para acesso externo.
- **Reiniciar o backend** após a alteração.

Assim, o frontend conseguirá acessar a API normalmente via IP da rede! 