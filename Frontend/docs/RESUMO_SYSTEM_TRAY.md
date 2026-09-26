# 📋 Resumo: System Tray com Start/Stop e Toast

## 🎯 Funcionalidades Solicitadas

### ✅ System Tray
- Ícone na área de notificação (Mine_01.ico)
- Menu de contexto ao clicar com botão direito

### ✅ Start/Stop
- Menu "▶️ Iniciar Servidor" - Inicia servidor HTTP
- Menu "⏹️ Parar Servidor" - Para servidor HTTP
- Menu dinâmico (habilita/desabilita baseado no estado)
- Sincronização com mutex

### ✅ Notificações Toast
- Toast quando servidor inicia
- Toast quando servidor para
- Toast de erro (se necessário)
- Ação "Abrir" na notificação de início

---

## 📦 Dependências

```go
require (
	github.com/getlantern/systray v1.2.2
	github.com/go-toast/toast v0.0.0-20190211030409-01e6764cf0a4
)
```

---

## 🎨 Menu Proposto

```
┌─────────────────────────┐
│ ▶️  Iniciar Servidor    │ (desabilitado quando rodando)
│ ⏹️  Parar Servidor      │ (desabilitado quando parado)
├─────────────────────────┤
│ 🎯 Abrir no Navegador   │
├─────────────────────────┤
│ 🚪 Sair                 │
└─────────────────────────┘
```

---

## 🔔 Notificações Toast

### Quando Servidor Inicia
- **Título:** "Servidor Iniciado"
- **Mensagem:** "SSM Server rodando na porta 5173"
- **Ação:** Botão "Abrir" → Abre navegador

### Quando Servidor Para
- **Título:** "Servidor Parado"
- **Mensagem:** "SSM Server foi encerrado"
- **Sem ação**

---

## ⚙️ Arquitetura

### Controle de Estado
- Variável `serverRunning` (protegida por mutex)
- Menu atualizado dinamicamente
- Tooltip atualizado com status

### Goroutines
- System Tray: goroutine principal (bloqueia)
- Servidor HTTP: goroutine separada quando iniciado
- Handlers de menu: goroutine separada

### Sincronização
- `sync.Mutex` para proteger estado
- Graceful shutdown ao parar
- Notificações Toast sincronizadas

---

## 📊 Impacto

- **Tamanho:** +1.5-2.5 MB (total: ~28-30 MB)
- **Tempo:** 3-4 horas de implementação
- **Complexidade:** Média
- **Requisitos:** Windows 10/11 (para Toast)

---

## ✅ Checklist

- [ ] Adicionar dependências (systray, go-toast)
- [ ] Criar `tray.go` com System Tray
- [ ] Implementar Start/Stop
- [ ] Implementar notificações Toast
- [ ] Integrar com `main.go`
- [ ] Testar menu dinâmico
- [ ] Testar notificações
- [ ] Testar sincronização

---

**Status:** Planejamento completo ✅

