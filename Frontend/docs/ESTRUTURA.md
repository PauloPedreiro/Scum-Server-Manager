# 📁 Estrutura do Projeto - SSM 3.0 Frontend

Documentação detalhada da estrutura de diretórios e arquivos do projeto.

## 🌳 Árvore de Diretórios

```
Frontend/
├── docs/                          # Documentação do projeto
│   ├── README.md                  # Documentação principal
│   ├── INSTALACAO.md              # Guia de instalação
│   ├── CONFIGURACAO.md            # Guia de configuração
│   ├── API.md                     # Documentação da API
│   └── ESTRUTURA.md               # Este arquivo
│
├── src/                           # Código-fonte
│   ├── app/                       # Configuração principal
│   │   ├── main.tsx              # Entry point da aplicação
│   │   ├── routes.tsx            # Definição de rotas
│   │   └── styles/
│   │       └── index.css         # Estilos globais
│   │
│   ├── assets/                    # Recursos estáticos
│   │   ├── backgrounds/          # Imagens de fundo
│   │   ├── logo/                 # Logos da aplicação
│   │   └── maps/                 # Mapas do jogo
│   │
│   ├── components/                # Componentes reutilizáveis
│   │   ├── layout/
│   │   │   └── AppShell.tsx      # Shell principal com navegação
│   │   └── ui/
│   │       ├── BackgroundSelector.tsx
│   │       ├── LanguageSwitcher.tsx
│   │       └── TopMenu.tsx
│   │
│   ├── i18n/                      # Internacionalização
│   │   ├── index.ts              # Configuração i18next
│   │   └── locales/
│   │       ├── pt-BR/
│   │       │   └── translation.json
│   │       └── en/
│   │           └── translation.json
│   │
│   ├── lib/                       # Utilitários e helpers
│   │   ├── alert.ts              # Helpers para alertas
│   │   ├── cn.ts                 # Utilitário className
│   │   ├── motion.ts             # Configurações de animação
│   │   └── storage.ts            # Helpers para localStorage
│   │
│   ├── pages/                     # Páginas da aplicação
│   │   ├── home/
│   │   │   └── Home.tsx          # Dashboard principal
│   │   ├── players/
│   │   │   └── Players.tsx       # Gerenciamento de players
│   │   ├── server/
│   │   │   └── Server.tsx        # Controle do servidor
│   │   ├── map/
│   │   │   └── Map.tsx           # Mapa interativo
│   │   ├── settings/
│   │   │   ├── Settings.tsx      # Página principal de configurações
│   │   │   ├── components/       # Componentes de Settings
│   │   │   │   ├── SettingsHeader.tsx
│   │   │   │   ├── MainTabs.tsx
│   │   │   │   └── SearchBar.tsx
│   │   │   ├── tabs/             # Abas de configurações
│   │   │   │   ├── ServerSettingsTab.tsx
│   │   │   │   ├── ConfigTab.tsx
│   │   │   │   └── DiscordTab.tsx
│   │   │   └── hooks/            # Hooks customizados
│   │   │       └── useServerSettings.ts
│   │   └── errors/
│   │       └── NotFound.tsx     # Página 404
│   │
│   ├── services/                  # Serviços de API
│   │   ├── server.ts             # Cliente Axios e interfaces principais
│   │   ├── config.ts             # Serviços de configuração (config.json)
│   │   ├── settings.ts           # Serviços de ServerSettings.ini
│   │   ├── webhooks.ts           # Serviços de webhooks do Discord
│   │   ├── chests.ts             # Serviços de baús
│   │   ├── rankings.ts           # Serviços de rankings
│   │   └── ...                   # Outros serviços
│   │
│   └── config.json               # Configurações do projeto
│
├── dist/                          # Build de produção (gerado)
├── node_modules/                  # Dependências (gerado)
├── prompts/                       # Prompts e guias
│   ├── GUIA_CONFIGURACAO_BACKEND.md
│   └── PROMPT_BACKEND_DEV.md
│
├── .gitignore                     # Arquivos ignorados pelo Git
├── index.html                     # HTML principal
├── package.json                   # Dependências e scripts
├── package-lock.json              # Lockfile do npm
├── postcss.config.js              # Configuração PostCSS
├── tailwind.config.js             # Configuração Tailwind CSS
├── tsconfig.json                   # Configuração TypeScript
└── vite.config.ts                 # Configuração Vite
```

---

## 📂 Descrição Detalhada dos Diretórios

### `/src/app/`

Configuração principal da aplicação React.

#### `main.tsx`
- Entry point da aplicação
- Renderiza o React app no DOM
- Configura providers globais (Router, i18n, etc.)
- Inicializa toasts e notificações

#### `routes.tsx`
- Define todas as rotas usando React Router
- Implementa lazy loading para code splitting
- Configura Suspense para loading states

#### `styles/index.css`
- Estilos globais
- Importações do Tailwind CSS
- Variáveis CSS customizadas
- Reset CSS básico

---

### `/src/pages/`

Cada subdiretório representa uma página da aplicação.

#### `home/Home.tsx`
- **Rota**: `/`
- **Descrição**: Dashboard principal com visão geral
- **Funcionalidades**:
  - Status do servidor (Online/Offline)
  - Horário do servidor
  - Contador de players online
  - Cards informativos
  - Preview do mapa

#### `players/Players.tsx`
- **Rota**: `/players`
- **Descrição**: Gerenciamento completo de players
- **Funcionalidades**:
  - Lista todos os players (online/offline)
  - Status online/offline
  - Coluna de veículos ativos com contagem visual (verde se > 0, vermelho se = 0)
  - Ordenação por quantidade de veículos (maior para menor)
  - Busca por nome ou Steam ID
  - Filtros por permissões (Timer, Admin, Banned, Config, Silenced, Whitelist)
  - Painel colapsável com abas (Permissões | Veículos)
  - **Aba Permissões**: Gerenciamento de permissões (Timer, Admin, Banned, Config, Silenced, Whitelist)
  - **Aba Veículos**: 
    - Resumo de veículos por status (Ativo, Inativo, Desaparecido, Destruído)
    - Filtros por status
    - **Layout Responsivo**: Veículos agrupados 2 por card
      - Grid responsivo: 1 coluna (mobile), 2 colunas (desktop)
      - Cards mais largos para melhor visualização de informações
      - Cores por status aplicadas ao card externo
      - Informações empilhadas verticalmente sem quebra de linha
    - Lista detalhada com miniaturas, IDs e localização
  - Atualização manual via botão "Atualizar"

#### `server/Server.tsx`
- **Rota**: `/server`
- **Descrição**: Controle do servidor SCUM
- **Funcionalidades**:
  - Botões Start/Stop/Restart
  - Status em tempo real
  - Informações do serviço
  - Polling automático

#### `map/Map.tsx`
- **Rota**: `/map`
- **Descrição**: Mapa interativo do jogo
- **Funcionalidades**:
  - Visualização do mapa (Map.webp)
  - Zoom (mouse wheel, botões)
  - Pan (arrastar)
  - Botão de reset
  - Indicador de zoom

#### `settings/Settings.tsx`
- **Rota**: `/settings`
- **Descrição**: Gerenciamento completo de configurações do servidor
- **Funcionalidades**:
  - **Aba ServerSettings.ini**: Edição de configurações do servidor SCUM
    - Seções: General, World, Respawn, Vehicles, Damage, Features
    - Busca por chave ou valor
    - Adicionar/remover campos customizados
    - Salvar alterações com backup automático
  - **Aba Config.json**: Gerenciamento de configuração da aplicação
    - Edição de seções: server, updates, weather_scheduler, squad_sync, etc.
    - Sistema de backups e restauração
    - Validação de campos
  - **Aba Discord**: Gerenciamento de webhooks do Discord
    - Lista de webhooks disponíveis
    - Edição de URLs
    - Teste de webhooks
    - Validação de URLs do Discord

#### `errors/NotFound.tsx`
- **Rota**: `*` (catch-all)
- **Descrição**: Página 404 para rotas não encontradas

---

### `/src/components/`

Componentes reutilizáveis da aplicação.

#### `layout/AppShell.tsx`
- Componente principal de layout
- Contém:
  - Cabeçalho com logo interativa
    - Logo clicável que leva à home
    - Hover effects (scale, background)
    - Título "SCUM Server Manager"
    - Estado ativo quando na home
  - Navegação principal (Home, Map, Server, Players, Settings)
  - Seletor de idioma
  - Seletor de background
  - NavigationLoadingProvider para gerenciar transições
  - Outlet para renderizar rotas filhas

#### `ui/BackgroundSelector.tsx`
- Componente para selecionar background
- Permite escolher entre diferentes imagens de fundo

#### `ui/LanguageSwitcher.tsx`
- Componente para alternar idioma
- Suporta pt-BR e en

#### `ui/NavigationLoader.tsx`
- Sistema de transição entre páginas
- Provider que gerencia estado de loading durante navegação
- Overlay fullscreen com logo animada
- Timer configurável (padrão: 2 segundos)
- Animação de pulsação na logo
- Hook `useNavigationLoading()` para acesso ao estado

#### `ui/TopMenu.tsx`
- Menu superior (se aplicável)

---

### `/src/services/`

Serviços de integração com APIs externas.

#### `server.ts`
- **Cliente Axios**: Configurado com baseURL e timeout
- **Interfaces TypeScript**: Todas as interfaces de resposta da API
- **Funções de API**: 
  - `getServerStatus()`
  - `startServer()`, `stopServer()`, `restartServer()`
  - `getServerTime()`
  - `getPlayersOnlineStats()`
  - `getPlayersOnlineList()`
  - `getAllPlayers()`
  - `getPlayerPermissions()`
  - `activatePermission()`, `deactivatePermission()`
  - `updatePlayerPermissao()`
- **Tratamento de Erros**: Interceptors para erros de rede

#### `config.ts`
- Serviços para gerenciamento de `config.json`
- `getConfigSection()`: Obter seção específica
- `updateConfigSection()`: Atualizar seção
- `getConfigBackups()`: Listar backups
- `restoreConfigBackup()`: Restaurar backup

#### `settings.ts`
- Serviços para gerenciamento de `ServerSettings.ini`
- `getServerSettings()`: Obter configurações por seção
- `updateServerSettings()`: Atualizar configurações
- `addCustomField()`: Adicionar campo customizado
- `removeCustomField()`: Remover campo customizado

#### `webhooks.ts`
- Serviços para gerenciamento de webhooks do Discord
- `getWebhooks()`: Listar webhooks configurados
- `getWebhookNames()`: Listar nomes disponíveis
- `updateWebhook()`: Atualizar URL de webhook
- `testWebhook()`: Testar webhook configurado
- `testWebhookByUrl()`: Testar URL antes de salvar

---

### `/src/i18n/`

Configuração de internacionalização (i18n).

#### `index.ts`
- Configuração do i18next
- Detecção de idioma
- Carregamento de traduções

#### `locales/{locale}/translation.json`
- Arquivos JSON com traduções
- Estrutura hierárquica por seção
- Chaves: `app`, `home`, `players`, `server`, etc.

---

### `/src/lib/`

Utilitários e helpers reutilizáveis.

#### `alert.ts`
- Helpers para exibir alertas
- Integração com SweetAlert2

#### `cn.ts`
- Utilitário para combinar classes CSS
- Integração com Tailwind

#### `motion.ts`
- Configurações de animação Framer Motion
- Variantes de animação reutilizáveis

#### `storage.ts`
- Helpers para localStorage
- Funções para salvar/carregar dados

---

### `/src/assets/`

Recursos estáticos (imagens, logos, etc.).

#### `backgrounds/`
- Imagens de fundo do jogo SCUM
- Formatos: JPG, PNG
- Resoluções variadas

#### `logo/`
- Logos da aplicação SSM
- Formatos: GIF, PNG, SVG

#### `maps/`
- Mapas do jogo
- `Map.webp`: Mapa principal do jogo SCUM

---

### `/prompts/`

Documentação e prompts relacionados ao backend.

#### `GUIA_CONFIGURACAO_BACKEND.md`
- Guia de configuração do backend
- URLs e endpoints
- Troubleshooting

#### `PROMPT_BACKEND_DEV.md`
- Prompts para desenvolvedores do backend

---

## 📄 Arquivos de Configuração Raiz

### `package.json`
- Dependências do projeto
- Scripts npm (dev, build, preview)
- Metadados do projeto

### `vite.config.ts`
- Configuração do Vite
- Plugins (React, TypeScript paths)
- Configuração do servidor de desenvolvimento
- Configuração de HMR

### `tsconfig.json`
- Configuração do TypeScript
- Paths aliases (@/ para src/)
- Opções de compilação

### `tailwind.config.js`
- Configuração do Tailwind CSS
- Cores customizadas (scum-*)
- Plugins e extensões

### `postcss.config.js`
- Configuração do PostCSS
- Plugins (Tailwind, Autoprefixer)

### `src/config.json`
- Configurações de backend e frontend
- URLs e portas
- Timeouts

---

## 🔄 Fluxo de Dados

```
src/app/main.tsx
    ↓
src/app/routes.tsx
    ↓
src/components/layout/AppShell.tsx
    ↓
src/pages/{Page}/
    ↓
src/services/server.ts
    ↓
Backend API
```

---

## 📦 Build e Distribuição

### Estrutura de Build (`dist/`)

```
dist/
├── index.html          # HTML principal
├── assets/
│   ├── *.js           # JavaScript bundle
│   ├── *.css          # CSS bundle
│   └── *.png/jpg/webp # Assets otimizados
```

### Como é Gerado

```bash
npm run build
```

O Vite:
1. Compila TypeScript
2. Processa CSS (Tailwind, PostCSS)
3. Otimiza assets
4. Code splitting
5. Minificação
6. Gera `dist/`

---

## 🔍 Convenções de Nomenclatura

### Arquivos
- **Componentes React**: PascalCase (ex: `Home.tsx`, `AppShell.tsx`)
- **Utilitários**: camelCase (ex: `alert.ts`, `storage.ts`)
- **Configuração**: kebab-case ou camelCase (ex: `config.json`, `vite.config.ts`)

### Diretórios
- **Páginas**: lowercase (ex: `home/`, `players/`)
- **Componentes**: lowercase (ex: `layout/`, `ui/`)
- **Utilitários**: lowercase (ex: `lib/`, `services/`)

### Imports
- **Path Aliases**: `@/` aponta para `src/`
- **Exemplo**: `import { Home } from '@/pages/home/Home'`

---

## 🎨 Estilos e Assets

### Tailwind CSS
- Framework CSS utilitário
- Classes diretas no JSX
- Customização em `tailwind.config.js`

### Assets
- Imagens: `/src/assets/`
- Referência: `import Map from '@/assets/maps/Map.webp'`

---

## 📝 Notas Importantes

1. **Lazy Loading**: Todas as páginas usam `lazy()` para code splitting
2. **TypeScript**: Tipagem estrita em todos os arquivos
3. **i18n**: Todas as strings devem usar traduções
4. **Responsividade**: UI deve funcionar em mobile e desktop
5. **Error Handling**: Sempre tratar erros de API

---

## 📚 Referências

- [Documentação Principal](./README.md)
- [Documentação de API](./API.md)
- [Guia de Configuração](./CONFIGURACAO.md)

---

**Última atualização**: 2025-12-03

