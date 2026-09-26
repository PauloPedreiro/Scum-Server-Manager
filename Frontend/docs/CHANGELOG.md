# 📝 Changelog - SSM 3.0 Frontend

Registro de mudanças e versões do projeto.

## [1.4.1] - 2025-12-03

### 🐛 Corrigido
- **Correção de chave duplicada em traduções**: Removida chave duplicada `"save"` nos arquivos de tradução (pt-BR e en)
  - Linha 1608: Removida chave `"save": "Save"` duplicada no objeto `discord`
  - Mantida apenas a chave `"save"` como objeto com mensagens de sucesso
  - Corrigido em `src/i18n/locales/en/translation.json` e `src/i18n/locales/pt-BR/translation.json`

### 📚 Documentação
- Atualizada toda a documentação do projeto
- Corrigidas referências de versão e datas
- Atualizada estrutura do projeto com novas funcionalidades de Settings

---

## [1.4.0] - 2025-11-09

### ✨ Adicionado
- **Filtro de Baús no Mapa**:
  - Painel lateral de filtros com opção “Baús” consumindo `GET /api/chests`
  - Marcadores simultâneos para todos os baús com coordenadas válidas
  - Resumo de baús armazenados em veículos (com estado e contagem)
  - Mini painel exibindo quantidade sincronizada, itens em veículos e tipos encontrados
- **Busca Dinâmica no Campo de Coordenadas**:
  - Aceita coordenadas no formato do jogo, realizando o posicionamento tradicional
  - Também aceita nome, apelido ou Steam ID do jogador para filtrar os baús exibidos no mapa/lateral
  - Chip de filtro ativo com opção “Limpar” diretamente no painel
- **Aba “Baús” nos Players**:
  - Novo tab ao lado de Permissões e Veículos
  - Resumo com total sincronizado, distribuído entre “Com coordenadas” e “Em veículos”, além de contagem por tipo
  - Cards compactos responsivos (até 4 por linha) com miniatura por tipo de baú, localização, última visualização e veículo associado
  - Botão para atualizar baús do jogador e tratamento elegante de loading/erros

### 🔧 Modificado
- Cards de baús agora usam miniaturas vindas de `src/assets/Baus/`
- Resumo passou a destacar explicitamente os itens que estão “Em veículos”
- Layout dos cards foi compactado para caber mais itens por linha sem perder responsividade

### 📚 Documentação
- Atualizados `docs/README.md` e `README.md` com o novo fluxo de filtros de mapa e a aba de baús dos players
- Registrada esta versão no `docs/CHANGELOG.md`

---

## [1.3.0] - 2025-11-07

### ✨ Adicionado
- **Mapa Interativo Integrado**:
  - Entrada única para colar coordenadas no formato do jogo
  - Conversão automática para posição em pixels com marcador pulsante
  - Exibição do quadrante correspondente (ex.: C2, Z1)
- **Controles de Zoom Aprimorados**:
  - Toggle para habilitar/desabilitar zoom via scroll do mouse
  - Restrições de zoom mínimo (100%) para manter referência visual
  - Bloqueio de arraste quando zoom está desativado ou em 100%
  - Indicadores visuais quando arraste está indisponível

### 🔧 Modificado
- Substituída a antiga seção de informações de calibração por uma interface limpa focada em coordenadas
- Marcador acompanha corretamente o mapa durante zoom/pan
- Ajustado cursor e feedback visual conforme estado do zoom

### 📚 Documentação
- Atualizados `README.md` e `docs/README.md` com as novas capacidades do mapa
- Registrada esta versão no `docs/CHANGELOG.md`

---

## [1.2.0] - 2025-11-02

### ✨ Adicionado
- **Sistema de Transição Visual**: Transição entre páginas com logo animada
  - Logo aparece centralizada por 2 segundos ao mudar de página
  - Animação de pulsação contínua durante a transição
  - Overlay fullscreen com background escuro e blur
  - Tamanhos responsivos: 208px (mobile), 256px (tablet), 288px (desktop), 320px (telas grandes)
- **Logo Interativa no Header**: 
  - Logo clicável que leva para a home
  - Hover effects com scale e mudança de background
  - Estado ativo quando na página home (background destacado)
  - Tamanho aumentado: 32px (mobile), 36px (desktop)
- **Layout Responsivo de Veículos**:
  - Veículos agrupados 2 por card
  - Grid responsivo: 1 coluna (mobile), 2 colunas (desktop)
  - Cards mais largos para melhor visualização
  - Cores por status aplicadas ao card externo
  - Informações sem quebra de linha (whitespace-nowrap)

### 🔧 Modificado
- **Título da Aplicação**: Mudado de "SSM" para "SCUM Server Manager"
  - Atualizado em pt-BR e en
  - Título mais descritivo e profissional
- **Layout de Veículos**: 
  - Removido grid separado por status
  - Agora agrupa todos os veículos em pares independente do status
  - Cor do card baseada no status do primeiro veículo do par
  - Informações empilhadas verticalmente com prevenção de quebra de linha
- **Header**:
  - Logo maior e mais visível
  - Container próprio com padding e hover effects
  - Melhor espaçamento entre logo e título

### 🐛 Corrigido
- Cards de veículos agora sempre exibem cor baseada no status
- Informações de localização não quebram mais no meio da linha
- Transições de página mais suaves e visíveis

### 📚 Documentação
- Atualizada `docs/ESTRUTURA.md` com NavigationLoader e melhorias do AppShell
- Atualizada `docs/VEICULOS.md` com novo layout de 2 veículos por card
- Atualizado `docs/README.md` com novas características e seção de novidades
- Atualizado `README.md` principal com novas features
- Atualizado CHANGELOG com versão 1.2.0

---

## [1.1.0] - 2025-10-31

### ✨ Adicionado
- Sistema completo de gerenciamento de veículos por player
- Coluna "Veículos" na tabela de players mostrando quantidade de veículos ativos
- Ordenação por quantidade de veículos (maior para menor) com indicador visual (seta verde)
- Aba "Veículos" no painel colapsável de players com:
  - Resumo de veículos por status (Ativo, Inativo, Desaparecido, Destruído)
  - Filtros por status de veículo
  - Lista detalhada com miniaturas de veículos
  - Informações completas: ID Veículo, ID Container, Localização, Status, Funcionalidade
- Miniaturas de veículos usando imagens de `src/assets/vehicle-log/`
- Busca por nome de player ou Steam ID
- Filtros por permissões (mostrar apenas players com permissão ativa)
- Botão "Atualizar" para refresh manual dos dados
- Tratamento especial de erro 404 para players sem veículos (não mostra erro)

### 🔧 Modificado
- Removida atualização automática (polling a cada 30s)
- Atualização agora é apenas manual via botão "Atualizar"
- Removida coluna "Permission updated" (redundante)
- Painel colapsável agora possui abas: "Permissões" e "Veículos"
- Coluna "Veículos" mostra número em verde se > 0, vermelho se = 0
- Melhorada responsividade da tabela de players
- Ordenação secundária: mesma quantidade de veículos → online primeiro → alfabético

### 🐛 Corrigido
- Erro 404 ao verificar veículos de players sem veículos não aparece mais no console
- Sincronização correta de permissões após atualizações
- Tratamento de casos onde player não possui veículos

### 📚 Documentação
- Criado arquivo `docs/VEICULOS.md` com documentação completa do sistema de veículos
- Atualizada documentação da API com endpoints de veículos
- Atualizada estrutura do projeto com informações de veículos
- Atualizado CHANGELOG com versão 1.1.0

---

## [1.0.0] - 2025-01-31

### ✨ Adicionado
- Interface de gerenciamento completa para servidores SCUM
- Página Home (Dashboard) com status do servidor, horário e players online
- Página Players com lista completa e gerenciamento de permissões
- Página Server com controles Start/Stop/Restart
- Página Map com mapa interativo (zoom e pan)
- Sistema de internacionalização (pt-BR e en)
- Integração completa com backend SSM 3.0
- Gerenciamento de permissões avançadas (Admin, Banned, Config, Silenced, Whitelist)
- Gerenciamento de permissão do comando /tm
- Atualização em tempo real (polling) para status e players
- Sistema de notificações com SweetAlert2
- Design responsivo com Tailwind CSS
- Animações com Framer Motion
- Seletor de background
- Seletor de idioma

### 🔧 Configuração
- Arquivo `src/config.json` para configurações de backend e frontend
- Suporte a variáveis de ambiente (`VITE_*`)
- Configuração de HMR para desenvolvimento

### 🐛 Corrigido
- Erro de conexão com backend melhorado (mensagens mais claras)
- Sincronização de permissões entre frontend e backend
- Exibição correta de permissões ativas (aceita boolean ou número)
- Problemas de HMR com `0.0.0.0` como host

### 📚 Documentação
- README completo com visão geral
- Guia de instalação detalhado
- Guia de configuração
- Documentação da API
- Documentação da estrutura do projeto
- Changelog

---

## Versões Futuras

### Planejado
- [ ] Autenticação e autorização
- [ ] Página de configurações funcional
- [ ] Logs do servidor em tempo real
- [ ] Chat do servidor
- [ ] Estatísticas detalhadas
- [ ] Exportação de relatórios
- [ ] Temas personalizados
- [ ] Mais idiomas (es, fr, etc.)
- [ ] Notificações push
- [ ] Modo escuro/claro

---

**Formato**: [Versão] - Data
**Tipos**: ✨ Adicionado, 🔧 Configuração, 🐛 Corrigido, ⚠️ Quebrado, 📚 Documentação

