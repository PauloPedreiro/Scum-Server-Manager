# 📚 Documentação do Projeto SCUM Backend

## 📋 Visão Geral

Este projeto consiste em um **backend Python** que será distribuído para proprietários de servidores SCUM, com funcionalidades locais e preparado para comunicação bidirecional com o frontend central.

## 🎯 Objetivo

Criar uma plataforma SaaS (Software as a Service) onde:
- **Backend**: Distribuído para proprietários de servidores SCUM
- **Frontend**: Centralizado em servidor próprio
- **Controle**: Sistema centralizado de gerenciamento
- **Monetização**: Licenciamento/assinatura dos proprietários

## 📁 Estrutura da Documentação

- [📋 Plano do Projeto](./project-plan.md) - Plano completo de implementação
- [🏗️ Arquitetura do Sistema](./architecture.md) - Arquitetura técnica detalhada
- [🔄 Sistema de Atualizações](./update-system.md) - Sistema de atualizações automáticas
- [📅 Cronograma de Implementação](./implementation-schedule.md) - Cronograma detalhado
- [🔧 Especificações Técnicas](./technical-specs.md) - Especificações técnicas
- [📡 Sistema de Webhooks](./webhooks/README.md) - Notificações automáticas para Discord
- [📢 Sistema de Notificações](./notifications/README.md) - Notificações in-game para jogadores
- [🚗 Sistema de Auto-Registro de Veículos](./VEHICLE_REGISTRATION_SYSTEM.md) - Monitoramento automático de veículos trancados
- [💥 Sistema de Monitoramento de Destruição de Veículos](./VEHICLE_DESTRUCTION_SYSTEM.md) - Monitoramento de eventos de destruição de veículos
- [⚔️ Sistema de Monitoramento de Kill Logs](./KILL_LOGS_SYSTEM.md) - Monitoramento de eventos de morte/kill com sistema de imagens
- [👨‍💼 Sistema de Monitoramento de Comandos Admin](./ADMIN_LOGS_SYSTEM.md) - Monitoramento de comandos de administradores
- [📋 Exemplos de Admin Logs](./notifications/admin-examples.md) - Exemplos práticos de uso
- [🔧 Troubleshooting Admin Logs](./TROUBLESHOOTING_ADMIN_LOGS.md) - Guia de solução de problemas
- [🚫 Sistema de Deduplicação](./DEDUPLICATION_SYSTEM.md) - Sistema anti-duplicação de notificações
- [🔐 Sistema de Permissões de Jogadores](./PERMISSIONS_SYSTEM.md) - Gerenciamento de permissões de jogadores
- [🛒 Shop + 💰 Economy + 📦 Mailbox](./SHOP_ECONOMY_SYSTEM.md) - Sistema de loja, economia e entrega de itens via baú
- [🌐 API Endpoints](./endpoints/README.md) - Documentação completa da API
- [🎯 Sistema de Rankings de Snipers](./SNIPERS_RANKING_SYSTEM.md) - Top 20 snipers (maior distância de tiro)
- [⚔️ Sistema de Rankings de Kills](./KILLS_RANKING_SYSTEM.md) - Top Killers e Shame Rank (deaths by NPC)
- [🔓 Sistema de Rankings de Lockpicking](./LOCKPICKING_RANKING_SYSTEM.md) - Top 20 lockpicking por tipo de fechadura

## 🚀 Funcionalidades Principais

### Backend (Distribuído)
- ✅ Controle do servidor SCUM (iniciar, parar, reiniciar)
- ✅ Sistema de agendamento com restart automático
- ✅ Sistema de configuração centralizada
- ✅ Sistema de identificação única
- ✅ Comunicação bidirecional com frontend
- ✅ Sistema de atualizações automáticas
- ✅ Sistema de webhooks para Discord
- ✅ Sistema de notificações in-game
- ✅ Sistema de auto-registro de veículos
- ✅ Sistema de monitoramento de destruição de veículos
- ✅ Sistema de monitoramento de kill logs (PvP, NPC, Suicídios)
- ✅ Sistema de monitoramento de comandos admin
- ✅ Sistema de deduplicação de notificações Discord
- ✅ Sistema de permissões de jogadores (Admin, Banned, Exclusive, etc.)
- ✅ Empacotamento como .exe

### Frontend (Central)
- ✅ Painel para proprietários de servidores
- ✅ Painel administrativo central
- ✅ Sistema de mensagens globais
- ✅ Controle de licenças
- ✅ Análise de dados agregados

## 🔧 Correções Recentes (v1.2.0)

### ✅ Sistema de Admin Logs Completamente Corrigido
- **Problema 1**: Erro `'AdminLogProcessor' object has no attribute '_get_last_processed_command'`
- **Problema 2**: Arquivos temporários não removidos após processamento
- **Problema 3**: Tabela `log_files_processed` não usada para admin logs
- **Soluções**: 
  - Método `_get_last_processed_command()` implementado
  - Limpeza de arquivos temporários movida para bloco `finally`
  - Registro de arquivos admin na tabela `log_files_processed`
- **Melhorias**: 
  - Sistema migrado para banco SQLite
  - Controle de estado melhorado
  - Processamento mais confiável
  - Não acumula arquivos órfãos
  - Estatísticas completas de processamento
- **Status**: ✅ Completamente corrigido e funcionando

### 📊 Novos Endpoints de Monitoramento
- `/api/admin-logs/processing-status` - Status do processamento
- Melhor rastreamento de erros
- Estatísticas em tempo real
- Controle de arquivos processados

## 🎮 Controle do Servidor SCUM

- **Iniciar servidor**: Scripts PowerShell robustos
- **Parar servidor**: Scripts batch com verificação de múltiplas instâncias
- **Reiniciar servidor**: Sistema completo com validação de processos
- **Verificação de status**: Monitoramento contínuo via `sc query SCUMServer`
- **Controle via NSSM**: Gerenciamento de serviço Windows
- **Atualização automática**: Integração com SteamCMD

## 🔄 Sistema de Atualizações

- **Verificação**: A cada 24 horas
- **Tipo**: Obrigatória (proprietário escolhe quando)
- **Rollback**: Manual
- **Notificações**: Painel + Discord
- **Controle**: Centralizado via API

## 📡 Sistema de Webhooks Discord

- **Notificações automáticas** para todos os eventos importantes
- **Eventos suportados**: Iniciar, parar, reiniciar servidor
- **Agendador**: Notificações de restart automático
- **Rate limiting**: 30 requisições/minuto com retry automático
- **Configuração simples**: Arquivo JSON com URLs dos webhooks

## 🚗 Sistema de Auto-Registro de Veículos

- **Monitoramento automático** de logs `chest_ownership_*.log`
- **Detecção de eventos**: Veículos trancados e transferências de propriedade
- **Duplo identificador**: Container ID + Vehicle Entity ID para rastreamento completo
- **Notificações Discord**: Embeds ricos com imagem do veículo
- **Banco de dados**: Histórico completo e propriedade atual
- **API completa**: Endpoints para consulta e estatísticas
- **Processamento incremental**: Evita duplicatas e processa apenas novos eventos

## 👨‍💼 Sistema de Monitoramento de Comandos Admin

- **Monitoramento automático** de logs `admin_*.log`
- **Detecção de eventos**: Todos os comandos executados por administradores
- **Categorização inteligente**: Comandos organizados por tipo (Teleport, Spawn, God Mode, etc.)
- **Notificações Discord**: Embeds coloridos com emojis específicos por categoria
- **Controle de duplicatas**: Sistema baseado em timestamp + steam_id para evitar reprocessamento
- **Tempo real**: Detecção e envio imediato de novos comandos
- **Processamento incremental**: Processa apenas comandos novos, não reprocessa antigos

## 📦 Empacotamento

- **Formato**: Executável .exe
- **Distribuição**: Download direto
- **Instalação**: Automática
- **Atualização**: Automática com controle do proprietário

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND CENTRAL                        │
│  👤 Painel Proprietário  │  🎛️ Painel Administrativo     │
└─────────────────────────────────────────────────────────────┘
                              ↕️
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND LOCAL                           │
│  🆔 Identificação  │  🎮 Controle Servidor  │  🔄 Updates  │
└─────────────────────────────────────────────────────────────┘
                              ↕️
┌─────────────────────────────────────────────────────────────┐
│                    SERVIDOR SCUM                           │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Modelo de Negócio

- **Distribuição**: Backend para proprietários
- **Licenciamento**: Sistema de assinatura
- **Controle**: Centralizado via frontend
- **Monetização**: Licenciamento/assinatura

## 🎯 Próximos Passos

1. Implementar FASE 1: Fundação do Backend
2. Desenvolver sistema de identificação única
3. Implementar controle do servidor SCUM
4. Criar sistema de comunicação com frontend
5. Desenvolver sistema de atualizações

---

**Última atualização**: 16/10/2025
**Versão**: 1.1.0
