# 🔄 Otimização de Polling - Frontend

## 📋 Resumo

Foi realizada uma otimização no sistema de polling para reduzir a carga no servidor e os logs excessivos no console. O intervalo de polling do endpoint `/api/server/status` foi aumentado de **2 segundos** para **30 segundos**.

---

## 🎯 Objetivo

Reduzir a quantidade de requisições HTTP desnecessárias mantendo uma experiência de usuário adequada. O intervalo de 30 segundos ainda é suficiente para atualizações em tempo real do status do servidor.

---

## ⚙️ Mudanças Necessárias no Frontend

### **1. Endpoint Principal: `/api/server/status`**

**Arquivo:** Componente que monitora o status do servidor SCUM

**Mudança necessária:**

```typescript
// ❌ ANTES (2 segundos - muito frequente)
useEffect(() => {
  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/server/status`);
      const data = await response.json();
      // ... processar dados
    } catch (err) {
      console.error('Erro:', err);
    }
  };

  fetchStatus();
  const interval = setInterval(fetchStatus, 2000); // ← MUDAR AQUI
  return () => clearInterval(interval);
}, []);

// ✅ DEPOIS (30 segundos - otimizado)
useEffect(() => {
  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/server/status`);
      const data = await response.json();
      // ... processar dados
    } catch (err) {
      console.error('Erro:', err);
    }
  };

  fetchStatus();
  const interval = setInterval(fetchStatus, 30000); // ← 30 segundos
  return () => clearInterval(interval);
}, []);
```

---

## 📊 Impacto das Mudanças

### **Antes da Otimização:**
- **GUI Backend:** ~30 requisições/minuto
- **Frontend:** ~30 requisições/minuto
- **Total:** ~60 requisições/minuto de `/api/server/status`
- **Logs:** ~120 linhas/minuto no console

### **Depois da Otimização:**
- **GUI Backend:** ~2 requisições/minuto ✅
- **Frontend:** ~2 requisições/minuto (após ajuste)
- **Total:** ~4 requisições/minuto de `/api/server/status`
- **Logs:** Reduzidos significativamente ✅

**Redução:** ~93% menos requisições! 🎉

---

## 🔍 Endpoints que NÃO Precisam de Ajuste

Os seguintes endpoints podem manter seus intervalos atuais, pois não estão causando sobrecarga:

| Endpoint | Intervalo Atual | Status |
|----------|----------------|--------|
| `/api/weather/time` | ~18 segundos | ✅ OK |
| `/api/players/online/stats` | ~18 segundos | ✅ OK |
| `/api/scheduler/status` | ~18 segundos | ✅ OK |
| `/api/notifications/status` | ~5-10 segundos | ✅ OK |

---

## 📝 Checklist de Implementação

- [ ] Localizar componente que faz polling de `/api/server/status`
- [ ] Alterar `setInterval` de `2000ms` para `30000ms` (30 segundos)
- [ ] Testar que o status ainda atualiza corretamente
- [ ] Verificar que não há regressões visuais na interface
- [ ] Confirmar que a experiência do usuário permanece adequada

---

## 🧪 Como Testar

1. **Abrir o frontend** e verificar o console do navegador (F12 → Network)
2. **Observar requisições** para `/api/server/status`
3. **Confirmar** que as requisições ocorrem a cada ~30 segundos (não a cada 2 segundos)
4. **Verificar** que o status do servidor ainda atualiza corretamente na interface

---

## 💡 Benefícios

✅ **Redução de carga no servidor** - Menos requisições HTTP  
✅ **Menos logs no console** - Console mais limpo e fácil de debugar  
✅ **Melhor performance** - Menos overhead de rede  
✅ **Experiência mantida** - 30 segundos ainda é tempo real suficiente  

---

## 📞 Dúvidas?

Se houver alguma dúvida sobre a implementação ou impacto das mudanças, entre em contato com a equipe de backend.

---

**Data:** 2025-12-08  
**Versão Backend:** 3.0  
**Status:** ⏳ Aguardando implementação no frontend
