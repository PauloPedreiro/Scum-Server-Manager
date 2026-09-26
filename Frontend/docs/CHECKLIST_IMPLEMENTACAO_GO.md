# ✅ Checklist de Implementação - Servidor Go Standalone

## 📋 Resumo Rápido

**Objetivo:** Criar `SSM-Server.exe` que serve a aplicação React sem precisar de Node.js.

**Tecnologia:** Go (Golang) com embed de arquivos estáticos

**Tempo estimado:** 4-5 horas

**Resultado:** Executável ~10-15 MB, zero dependências

---

## 🎯 Fases de Implementação

### ✅ FASE 1: Preparação (30 minutos)

#### 1.1 Instalar Go SDK
- [ ] Baixar Go: https://golang.org/dl/
- [ ] Instalar (padrão: `C:\Program Files\Go`)
- [ ] Verificar: `go version` (deve mostrar 1.21+)
- [ ] Testar: `go env` (deve mostrar variáveis)

#### 1.2 Converter Logo para ICO
- [ ] ✅ Imagem `Mine_01.png` já copiada para `tools/`
- [ ] Acessar: https://convertio.co/png-ico/
- [ ] Upload: `tools/Mine_01.png`
- [ ] Download: `Mine_01.ico`
- [ ] Salvar em: `tools/Mine_01.ico`
- [ ] Verificar tamanho: ~50-200 KB

#### 1.3 Criar Estrutura de Projeto
- [ ] Criar pasta: `tools/server/`
- [ ] Inicializar módulo: `cd tools/server && go mod init ssm-server`
- [ ] Verificar: `go.mod` foi criado

---

### ✅ FASE 2: Desenvolvimento (2-3 horas)

#### 2.1 Servidor HTTP Básico (`main.go`)
- [ ] Criar `tools/server/main.go`
- [ ] Implementar servidor HTTP na porta 5173
- [ ] Implementar handler básico `/`
- [ ] Testar: `go run main.go` (deve iniciar servidor)

#### 2.2 Embed de Arquivos (`embed.go`)
- [ ] Criar `tools/server/embed.go`
- [ ] Implementar `//go:embed dist/*`
- [ ] Implementar função `serveFile()`
- [ ] Testar: Servir `index.html` corretamente

#### 2.3 Suporte a SPA
- [ ] Implementar lógica de roteamento SPA
- [ ] Redirecionar rotas não encontradas para `index.html`
- [ ] Manter exceções: `/config.json`, `/assets/*`
- [ ] Testar: Acessar `/players` → deve servir `index.html`

#### 2.4 Leitura de Config (`config.go`)
- [ ] Criar `tools/server/config.go`
- [ ] Implementar leitura de `config.json` embutido
- [ ] Extrair porta e host da configuração
- [ ] Implementar valores padrão (5173, 0.0.0.0)
- [ ] Testar: Servidor usa porta do config.json

---

### ✅ FASE 3: Funcionalidades Avançadas (1 hora)

#### 3.1 Abertura do Navegador (`browser.go`)
- [ ] Criar `tools/server/browser.go`
- [ ] Implementar `openBrowser(url string)`
- [ ] Suportar Windows, Linux, Mac
- [ ] Aguardar 1-2 segundos antes de abrir
- [ ] Testar: Navegador abre automaticamente

#### 3.2 Tratamento de Erros
- [ ] Verificar se porta está em uso
- [ ] Mensagens de erro claras
- [ ] Graceful shutdown (Ctrl+C)
- [ ] Testar: Porta em uso → mensagem clara

#### 3.3 Logs Informativos
- [ ] Adicionar logs de inicialização
- [ ] Mostrar URLs de acesso
- [ ] Mostrar status do servidor
- [ ] Testar: Logs aparecem corretamente

#### 3.4 Suporte a CORS
- [ ] Adicionar headers CORS
- [ ] Suportar OPTIONS requests
- [ ] Testar: Requisições do backend funcionam

---

### ✅ FASE 4: Build e Distribuição (1 hora)

#### 4.1 Script de Build
- [ ] Criar `tools/build-server.bat`
- [ ] Verificar se Go está instalado
- [ ] Verificar se `dist/` existe
- [ ] Compilar servidor
- [ ] Copiar executável para `dist/`
- [ ] Testar: Script funciona corretamente

#### 4.2 Adicionar Ícone
- [ ] Instalar `rsrc`: `go install github.com/akavel/rsrc@latest`
- [ ] Gerar `rsrc.syso`: `rsrc -ico Mine_01.ico -o rsrc.syso`
- [ ] Compilar com ícone
- [ ] Verificar: Ícone da mina aparece no Windows Explorer

#### 4.3 Integração com Vite (Opcional)
- [ ] Atualizar `vite.config.ts`
- [ ] Adicionar plugin para build do servidor
- [ ] Testar: `npm run build` compila servidor também

#### 4.4 Testes Finais
- [ ] Teste local completo
- [ ] Teste em máquina limpa (sem Node.js)
- [ ] Teste de rede (acesso externo)
- [ ] Verificar tamanho do executável (~10-15 MB)

---

## 🧪 Testes Obrigatórios

### Teste 1: Funcionalidade Básica
```
1. Executar SSM-Server.exe
2. Verificar: Servidor inicia na porta 5173
3. Verificar: Navegador abre automaticamente
4. Verificar: Aplicação carrega corretamente
5. Verificar: Login funciona
```

### Teste 2: SPA Routing
```
1. Acessar http://localhost:5173/players
2. Verificar: Página de players carrega
3. Acessar http://localhost:5173/settings
4. Verificar: Página de settings carrega
5. Verificar: Navegação funciona
```

### Teste 3: Config.json
```
1. Acessar http://localhost:5173/config.json
2. Verificar: JSON é retornado (não HTML)
3. Verificar: Content-Type é application/json
4. Verificar: Configuração está correta
```

### Teste 4: Máquina Limpa
```
1. Copiar SSM-Server.exe para máquina sem Node.js
2. Executar
3. Verificar: Funciona sem erros
4. Verificar: Não precisa de dependências
```

### Teste 5: Rede
```
1. Acessar de outra máquina: http://[IP]:5173
2. Verificar: Aplicação carrega
3. Verificar: API do backend funciona
4. Verificar: Config.json funciona
```

---

## 📦 Estrutura Final Esperada

```
dist/
├── SSM-Server.exe          # ✅ Executável standalone
├── config.json             # ✅ Configuração (editável)
├── index.html              # ✅ HTML principal
├── assets/                 # ✅ Arquivos estáticos
│   ├── *.js
│   ├── *.css
│   └── *.png/jpg
└── README.md               # ✅ Instruções
```

---

## 🐛 Troubleshooting Comum

### Problema: "go: command not found"
**Solução:** Instalar Go SDK e adicionar ao PATH

### Problema: "porta já está em uso"
**Solução:** Mudar porta no config.json ou fechar processo que usa a porta

### Problema: "dist/ não encontrada"
**Solução:** Executar `npm run build` primeiro

### Problema: Ícone não aparece
**Solução:** Verificar se `rsrc.syso` foi gerado e está na pasta do servidor

### Problema: Navegador não abre
**Solução:** Abrir manualmente `http://localhost:5173`

---

## 📚 Arquivos de Referência

- **Planejamento Completo:** `docs/IMPLEMENTACAO_GO_EMBED.md`
- **Análise de Opções:** `docs/PLANO_EXECUTAVEL_STANDALONE.md`

---

## 🎯 Próximos Passos Após Implementação

1. ✅ Testar em produção
2. ✅ Documentar uso para usuários finais
3. ✅ Criar release notes
4. ✅ Distribuir executável

---

**Status:** 🟡 Aguardando início da implementação

