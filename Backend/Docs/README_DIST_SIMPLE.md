# Scum Server Manager - Distribuição Simples

## 🚀 Como executar:

### Windows:
1. Clique duas vezes em `start.bat`
2. Aguarde a instalação das dependências
3. O servidor iniciará automaticamente

### Linux/Mac:
```bash
chmod +x start.sh
./start.sh
```

### Manual:
```bash
npm install
node server.js
```

## 📁 Arquivos de configuração:
- `src/data/server/config.json` - Configurações do servidor
- `src/data/webhooks.json` - Webhooks do Discord
- `src/data/funny_statistics.json` - Estatísticas divertidas
- `.env` - Variáveis de ambiente

## ✅ Vantagens desta distribuição:
- ✅ Não precisa compilar
- ✅ Funciona em qualquer sistema
- ✅ Fácil de instalar e executar
- ✅ Arquivos JSON separados e editáveis
- ✅ Sem problemas de dependências

## 🔧 Configuração:
1. Edite `.env` com suas configurações
2. Configure `src/data/server/config.json`
3. Adicione webhooks em `src/data/webhooks.json`
4. Execute `start.bat` (Windows) ou `start.sh` (Linux/Mac)

## 📡 Acesso:
- API: http://localhost:3000
- Health: http://localhost:3000/health
- Estatísticas: http://localhost:3000/funny-stats
- Jogadores: http://localhost:3000/players
