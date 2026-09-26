# 📚 Documentação do SSM 3.0 Frontend

Bem-vindo à documentação completa do **Scum Server Manager 3.0 - Frontend**.

Esta documentação fornece todas as informações necessárias para entender, configurar, desenvolver e usar o frontend do SSM 3.0.

## 📑 Índice

- [Visão Geral](#-visão-geral)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Desenvolvimento](#-desenvolvimento)
- [API e Integração](#-api-e-integração)
- [Sistema de Veículos](#-sistema-de-veículos)
- [Internacionalização](#-internacionalização)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Visão Geral

O **SSM 3.0 Frontend** é uma aplicação web moderna desenvolvida em React que fornece uma interface de gerenciamento completa para servidores SCUM. O sistema permite gerenciar players, controlar o servidor, visualizar mapas e configurar permissões de forma intuitiva.

### Características Principais

- ✅ **Interface Moderna**: Design responsivo com Tailwind CSS
- ✅ **Transições Visuais**: Sistema de transição entre páginas com logo animada (2 segundos)
- ✅ **Logo Interativa**: Logo clicável no header com hover effects e estado ativo
- ✅ **Tempo Real**: Atualização automática de status do servidor e players
- ✅ **Multilíngue**: Suporte para Português (pt-BR) e Inglês (en)
- ✅ **Título Descritivo**: "SCUM Server Manager" no lugar de apenas "SSM"
- ✅ **Gerenciamento de Players**: Lista completa com status online/offline e permissões
- ✅ **Gerenciamento de Veículos**: Visualização e gerenciamento de veículos por player
  - Layout responsivo: 2 veículos por card
  - Cards mais largos para melhor visualização
  - Cores por status (verde/amarelo/laranja/vermelho)
  - Informações sem quebra de linha
- ✅ **Controle do Servidor**: Iniciar, parar e reiniciar o servidor SCUM
- ✅ **Mapa Interativo**: Visualização precisa do mapa com inserção de coordenadas, marcadores, filtros e controle refinado de zoom/pan
- ✅ **Gerenciamento de Permissões**: Ativação/desativação de permissões avançadas (Admin, Banned, Config, etc.)
- ✅ **Ordenação Inteligente**: Ordenação por quantidade de veículos ativos
- ✅ **Busca e Filtros**: Busca por nome/Steam ID, filtros por permissões e pesquisa integrada de baús
- ✅ **Inventário de Baús**: Filtro global no mapa e aba dedicada por jogador com miniaturas, resumo e agrupamento por tipo
- ✅ **Gerenciamento de Configurações**: Interface completa para editar ServerSettings.ini, config.json e webhooks do Discord
  - Edição de seções do ServerSettings.ini (General, World, Respawn, Vehicles, Damage, Features)
  - Gerenciamento de config.json com sistema de backups
  - Configuração de webhooks do Discord com validação e testes

### Tecnologias Utilizadas

- **React 19.2.0** - Framework JavaScript
- **TypeScript 5.9.3** - Tipagem estática
- **Vite 5.4.21** - Build tool e dev server
- **React Router 7.9.5** - Roteamento
- **Axios 1.13.1** - Cliente HTTP
- **Tailwind CSS 3.4.18** - Framework CSS
- **i18next 25.6.0** - Internacionalização
- **SweetAlert2 11.26.3** - Notificações
- **Framer Motion 11.18.2** - Animações
- **Lucide React 0.548.0** - Ícones

---

## 📦 Instalação

### Pré-requisitos

- **Node.js** >= 18.x
- **npm** >= 9.x ou **yarn** >= 1.22.x
- Backend SSM 3.0 rodando e acessível

### Passos de Instalação

1. **Clone o repositório** (se aplicável):
```bash
git clone https://github.com/PauloPedreiro/PauloPedreiro-Scum-Server-Manager-3.0-Frontend.git
cd PauloPedreiro-Scum-Server-Manager-3.0-Frontend
```

2. **Instale as dependências**:
```bash
npm install
```

3. **Configure o backend** (veja [Configuração](#-configuração))

4. **Inicie o servidor de desenvolvimento**:
```bash
npm run dev
```

5. **Acesse a aplicação**:
```
http://localhost:5173
```

### Build para Produção

```bash
npm run build
```

Os arquivos compilados estarão na pasta `dist/`.

### Preview da Build

```bash
npm run preview
```

---

## ⚙️ Configuração

### Arquivo `src/config.json`

O arquivo de configuração principal está localizado em `src/config.json`:

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

### Configurações do Backend

| Campo | Tipo | Descrição | Padrão |
|-------|------|-----------|--------|
| `host` | string | IP ou hostname do backend | `192.168.100.3` |
| `port` | number | Porta do backend | `3000` |
| `protocol` | string | Protocolo (`http` ou `https`) | `http` |
| `basePath` | string | Caminho base da API | `/api` |
| `timeout` | number | Timeout das requisições (ms) | `60000` |

### Configurações do Frontend

| Campo | Tipo | Descrição | Padrão |
|-------|------|-----------|--------|
| `port` | number | Porta do servidor de desenvolvimento | `5173` |
| `host` | string | Host do servidor (`0.0.0.0` para todas as interfaces) | `0.0.0.0` |

### Variáveis de Ambiente

Você também pode usar variáveis de ambiente através do arquivo `.env`:

```env
VITE_API_BASE_URL=http://192.168.100.3:3000/api
```

---

## 📁 Estrutura do Projeto

```
Frontend/
├── src/
│   ├── app/              # Configuração principal da aplicação
│   │   ├── main.tsx      # Entry point
│   │   ├── routes.tsx    # Rotas da aplicação
│   │   └── styles/       # Estilos globais
│   ├── assets/           # Recursos estáticos
│   │   ├── backgrounds/  # Imagens de fundo
│   │   ├── logo/         # Logos
│   │   └── maps/         # Mapas
│   ├── components/        # Componentes reutilizáveis
│   │   ├── layout/        # Componentes de layout
│   │   └── ui/           # Componentes de UI
│   ├── i18n/             # Configuração de internacionalização
│   │   ├── index.ts      # Configuração i18next
│   │   └── locales/      # Arquivos de tradução
│   ├── lib/              # Utilitários e helpers
│   ├── utils/            # Funções auxiliares para mapa, baús e etc.
│   ├── pages/            # Páginas da aplicação
│   │   ├── home/         # Página inicial (dashboard)
│   │   ├── players/       # Página de gerenciamento de players (permissões, veículos e baús)
│   │   ├── server/       # Página de controle do servidor
│   │   ├── map/          # Página do mapa
│   │   ├── settings/     # Página de configurações
│   │   └── errors/       # Páginas de erro
│   ├── services/         # Serviços de API
│   │   └── server.ts     # Cliente API e interfaces
│   └── config.json       # Configurações do projeto
├── docs/                 # Documentação
├── dist/                 # Build de produção (gerado)
├── node_modules/         # Dependências
├── package.json          # Dependências e scripts
├── vite.config.ts        # Configuração do Vite
├── tsconfig.json         # Configuração TypeScript
└── tailwind.config.js    # Configuração Tailwind
```

### Descrição dos Diretórios

#### `src/app/`
Contém os arquivos principais da aplicação:
- **main.tsx**: Entry point que renderiza o React app
- **routes.tsx**: Define todas as rotas usando React Router
- **styles/index.css**: Estilos globais e configurações Tailwind

#### `src/pages/`
Cada subdiretório representa uma página:
- **home/**: Dashboard com visão geral (status, horário, players online)
- **players/**: Lista completa de players com gerenciamento de permissões
- **server/**: Controles para iniciar/parar/reiniciar o servidor
- **map/**: Mapa interativo do jogo com zoom e pan
- **settings/**: Configurações da aplicação
- **errors/**: Páginas de erro (404, etc.)

#### `src/components/`
Componentes reutilizáveis:
- **layout/AppShell.tsx**: Shell principal com navegação
- **ui/**: Componentes de UI (BackgroundSelector, LanguageSwitcher, etc.)

#### `src/services/`
Serviços de integração:
- **server.ts**: Cliente Axios, interfaces TypeScript e funções de API gerais
- **chests.ts**: Funções específicas para os endpoints de baús (lista global e por jogador)

#### `src/utils/`
Utilitários e mapeamentos auxiliares:
- **mapCalibration.ts / mapCoordinates.ts**: Conversão de coordenadas do jogo para o mapa
- **chestAssets.ts**: Mapeamento automático de classes/tipos de baús para suas miniaturas

#### `src/i18n/`
Internacionalização:
- Suporte para pt-BR e en
- Arquivos JSON com traduções

---

## 🛠️ Desenvolvimento

### Scripts Disponíveis

```bash
# Desenvolvimento (hot reload)
npm run dev

# Build para produção
npm run build

# Preview da build de produção
npm run preview
```

### Padrões de Código

- **TypeScript**: Tipagem estrita ativada
- **ESLint**: Seguir regras de lint (se configurado)
- **Prettier**: Formatação automática (se configurado)
- **Conventional Commits**: Padrão de commits (feat, fix, docs, etc.)

### Adicionando Novas Rotas

1. Crie o componente da página em `src/pages/`
2. Importe no `src/app/routes.tsx`
3. Adicione a rota no array `routes`

Exemplo:
```typescript
const NewPage = lazy(() => import('@/pages/new/NewPage'));

{
  path: 'new',
  element: (
    <Suspense>
      <NewPage />
    </Suspense>
  ),
}
```

### Adicionando Novas Traduções

1. Edite `src/i18n/locales/pt-BR/translation.json`
2. Edite `src/i18n/locales/en/translation.json`
3. Use no componente: `const { t } = useTranslation(); t('chave.traducao')`

### Hot Module Replacement (HMR)

O Vite oferece HMR automático. Mudanças em arquivos `.tsx` e `.ts` são refletidas instantaneamente no navegador.

---

## 🔌 API e Integração

### Endpoints Utilizados

#### Status do Servidor
- **GET** `/api/server/status` - Status atual do servidor SCUM

#### Controle do Servidor
- **POST** `/api/server/start` - Iniciar servidor
- **POST** `/api/server/stop` - Parar servidor
- **POST** `/api/server/restart` - Reiniciar servidor

#### Tempo e Clima
- **GET** `/api/weather/time` - Horário do servidor

#### Players
- **GET** `/api/players` - Lista todos os players
- **GET** `/api/players/online/list` - Lista players online
- **GET** `/api/players/online/stats` - Estatísticas de players online
- **GET** `/api/logs/players` - Logs de players

#### Baús
- **GET** `/api/chests` - Lista baús sincronizados (suporte a `steam_id`, `limit`, `offset`, `minimal`)
- **GET** `/api/chests/player/{steam_id}` - Lista baús de um jogador específico com resumo agregado

#### Permissões
- **GET** `/api/players/{steam_id}/permissions` - Permissões de um player
- **POST** `/api/players/{steam_id}/permissions/{type}/activate` - Ativar permissão
- **POST** `/api/players/{steam_id}/permissions/{type}/deactivate` - Desativar permissão
- **PUT** `/api/players/{steam_id}/permissao` - Atualizar permissão do comando /tm

### Cliente API

O cliente Axios está configurado em `src/services/server.ts`:

```typescript
import { getServerStatus, getPlayersOnlineList } from '@/services/server';

// Exemplo de uso
const status = await getServerStatus();
```

### Tratamento de Erros

O interceptor do Axios captura erros de conexão e fornece mensagens amigáveis:

```typescript
// Erro de conexão
if (e.code === 'ERR_NETWORK' || e.message?.includes('ERR_CONNECTION_REFUSED')) {
  // Mensagem de erro amigável
}
```

---

## 🌍 Internacionalização

### Idiomas Suportados

- **Português (pt-BR)** - Idioma padrão
- **Inglês (en)**

### Estrutura de Traduções

As traduções estão em `src/i18n/locales/{locale}/translation.json`:

```json
{
  "app": {
    "title": "SCUM Server Manager",
    "nav": {
      "overview": "Visão Geral",
      "map": "Mapa"
    }
  }
}
```

### Uso em Componentes

```typescript
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();
  
  return <h1>{t('app.title')}</h1>;
}
```

### Adicionar Novo Idioma

1. Crie `src/i18n/locales/{novo_idioma}/translation.json`
2. Adicione o idioma em `src/i18n/index.ts`

---

## 🔧 Troubleshooting

### Erro: "Cannot connect to backend"

**Causa**: Backend não está rodando ou configuração incorreta.

**Solução**:
1. Verifique se o backend está rodando
2. Verifique o `src/config.json` (host, port, protocol)
3. Teste a URL no navegador: `http://[HOST]:[PORT]/api/server/status`

### Erro: "ERR_ADDRESS_INVALID" no HMR

**Causa**: Configuração incorreta do HMR no Vite.

**Solução**: Se `host` for `0.0.0.0`, não defina `hmrHost` (deixe Vite detectar automaticamente).

### Erro: "Permission denied" ao fazer push

**Causa**: Problemas de permissão ou repositório remoto incorreto.

**Solução**: Verifique a URL remota com `git remote -v` e atualize se necessário.

### Build falha com erros de TypeScript

**Causa**: Tipos incorretos ou imports inválidos.

**Solução**: Execute `npm run build` e corrija os erros de tipo indicados.

### Players não aparecem ou permissões não são exibidas

**Causa**: Problema na sincronização com o backend.

**Solução**:
1. Verifique o console do navegador para erros
2. Verifique os logs do backend
3. Recarregue a página ou force um refresh das permissões

---

## 📝 Licença

Este projeto está sob a licença **Unlicense** (domínio público).

---

## 👥 Contribuição

Para contribuir:

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## 📞 Suporte

Para suporte, abra uma issue no repositório do GitHub ou entre em contato com a equipe de desenvolvimento.

---

---

## 🎨 Novidades e Melhorias Recentes

### Sistema de Transição com Logo
- **Transição Visual**: Ao mudar de página, logo aparece centralizada por 2 segundos
- **Animação de Pulsação**: Logo pulsa continuamente durante a transição
- **Overlay Fullscreen**: Background escuro com blur para destacar a logo
- **Responsivo**: Tamanhos adaptativos (208px mobile, 256px tablet, 288px desktop, 320px telas grandes)

### Logo Interativa no Header
- **Clicável**: Logo leva para a home ao clicar
- **Hover Effects**: Escala e mudança de background ao passar o mouse
- **Estado Ativo**: Background destacado quando na página home
- **Tamanho Aumentado**: Logo maior e mais visível (32px mobile, 36px desktop)

### Mapa Interativo Aprimorado
- **Entrada de Coordenadas**: Aceita coordenadas no formato do jogo e posiciona marcador automaticamente
- **Quadrante Automático**: Exibe o quadrante correspondente (A0–D4, Z0–Z4)
- **Controle de Zoom**: Toggle para scroll zoom, limites mínimos de 100% e feedback visual
- **Bloqueio Dinâmico de Pan**: Arraste liberado apenas quando o zoom está acima de 100%
- **Marcador Preciso**: Indicador pulsante que acompanha o mapa durante zoom/pan

### Filtro de Baús e inventário por jogador
- **Filtro "Baús" no mapa**: Carrega marcadores via API, exibe resumo e itens armazenados em veículos
- **Pesquisa Inteligente**: Campo de coordenadas também aceita nome/Steam ID para filtrar baús
- **Resumo Dinâmico**: Quantidade total, em veículos e agrupamento por tipo diretamente no painel
- **Aba "Baús" na página de players**: Cards com miniaturas, localização, última visualização e veículo associado
- **Atualização On-demand**: Botões de atualizar baús tanto no mapa quanto no perfil do jogador

### Sistema de Gerenciamento de Configurações
- **ServerSettings.ini**: Edição completa de configurações do servidor SCUM
  - Seções organizadas: General, World, Respawn, Vehicles, Damage, Features
  - Busca por chave ou valor
  - Adicionar/remover campos customizados
  - Backup automático ao salvar
- **Config.json**: Gerenciamento de configuração da aplicação
  - Edição de todas as seções (server, updates, syncs, etc.)
  - Sistema de backups com restauração
  - Validação de campos e tipos
  - Indicador de seções que requerem reinício
- **Discord Webhooks**: Configuração completa de webhooks
  - Lista de webhooks disponíveis
  - Edição de URLs com validação
  - Teste de webhooks antes de salvar
  - Sistema de backups automático

---

**Última atualização**: 2025-12-03  
**Versão**: 1.4.1

