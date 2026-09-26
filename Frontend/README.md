# 🎮 SSM 3.0 Frontend

**Scum Server Manager 3.0** - Interface web moderna para gerenciamento de servidores SCUM.

## 🚀 Início Rápido

```bash
# Instalar dependências
npm install

# Configurar backend em src/config.json
# Edite host, port, protocol conforme seu backend

# Iniciar desenvolvimento
npm run dev

# Build para produção
npm run build

# Iniciar em produção (após build)
npm run start:prod
```

> 💡 **Para produção completa**, consulte o [Guia de Produção](./docs/PRODUCAO.md) com opções de Nginx, Apache, PM2 e mais.

## 📚 Documentação Completa

Toda a documentação está disponível na pasta [`docs/`](./docs/):

- **[README Principal](./docs/README.md)** - Visão geral completa do projeto
- **[Guia de Instalação](./docs/INSTALACAO.md)** - Instalação passo a passo
- **[Guia de Produção](./docs/PRODUCAO.md)** - Como iniciar em produção 🚀
- **[Guia de Configuração](./docs/CONFIGURACAO.md)** - Todas as configurações disponíveis
- **[Documentação da API](./docs/API.md)** - Endpoints e integração com backend
- **[Estrutura do Projeto](./docs/ESTRUTURA.md)** - Estrutura de diretórios e arquivos
- **[Changelog](./docs/CHANGELOG.md)** - Histórico de versões

## ⚙️ Configuração Rápida

Edite `src/config.json`:

```json
{
  "backend": {
    "host": "192.168.100.3",
    "port": 3000,
    "protocol": "http",
    "basePath": "/api",
    "timeout": 60000
  },
  "frontend": {
    "port": 5173,
    "host": "0.0.0.0"
  }
}
```

## 🎯 Características

- ✅ Interface moderna e responsiva
- ✅ Transições visuais entre páginas com logo animada
- ✅ Logo interativa no header (clicável, hover effects)
- ✅ Gerenciamento de players e permissões
- ✅ Gerenciamento de veículos com layout responsivo (2 por card)
- ✅ Controle do servidor (Start/Stop/Restart)
- ✅ Mapa interativo com inserção de coordenadas, pesquisa por jogador e filtro de baús
- ✅ Atualização em tempo real
- ✅ Suporte multilíngue (pt-BR, en)
- ✅ Inventário de baús com miniaturas por jogador (aba dedicada em Players)
- ✅ Gerenciamento de configurações (ServerSettings.ini, config.json, webhooks Discord)

## 🛠️ Tecnologias

- React 19.2.0
- TypeScript 5.9.3
- Vite 5.4.21
- Tailwind CSS 3.4.18
- Axios 1.13.1
- React Router 7.9.5

## 📄 Licença

Unlicense (Domínio Público)

## 📞 Suporte

Para suporte, consulte a [documentação completa](./docs/README.md) ou abra uma issue no GitHub.

---

**Versão**: 1.4.1  
**Última atualização**: 2025-12-03

