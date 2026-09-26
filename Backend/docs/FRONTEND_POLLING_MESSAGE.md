# 📨 Mensagem para o Desenvolvedor do Frontend

---

**Assunto:** Otimização de Polling - Ajuste Necessário no Frontend

Olá!

Fizemos uma otimização no sistema de polling do backend para reduzir a carga no servidor. O intervalo de polling do endpoint `/api/server/status` foi aumentado de **2 segundos** para **30 segundos**.

**O que precisa ser feito:**

No componente do frontend que monitora o status do servidor (`/api/server/status`), alterar o intervalo de polling:

```typescript
// De:
setInterval(fetchStatus, 2000);  // 2 segundos

// Para:
setInterval(fetchStatus, 30000); // 30 segundos
```

**Impacto:**
- Redução de ~60 requisições/minuto para ~4 requisições/minuto
- Menos carga no servidor
- Experiência do usuário mantida (30s ainda é tempo real suficiente)

**Outros endpoints não precisam de ajuste:**
- `/api/weather/time` - OK manter ~18s
- `/api/players/online/stats` - OK manter ~18s  
- `/api/scheduler/status` - OK manter ~18s

**Documentação completa:** Ver `docs/FRONTEND_POLLING_OPTIMIZATION.md`

Obrigado! 🚀
