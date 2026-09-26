# 📋 Plano do Projeto SCUM Backend

## 🎯 Objetivo Final

Criar um backend Python que será distribuído para proprietários de servidores SCUM, com funcionalidades locais e preparado para comunicação bidirecional com o frontend central.

## 🏗️ Fases de Implementação

### **FASE 1: FUNDAÇÃO (Semana 1-2)**

#### 1.1 Estrutura Base do Projeto
```
scum_backend/
├── core/
├── communication/
├── utils/
├── data/
├── scripts/
├── main.py
├── requirements.txt
└── README.md
```

#### 1.2 Sistema de Identificação
- [ ] Geração de Backend ID único
- [ ] Sistema de Owner ID
- [ ] Preparação para License Key
- [ ] Arquivo de identificação persistente

#### 1.3 Sistema de Configuração
- [ ] Configuração centralizada (JSON)
- [ ] Validação de arquivos críticos
- [ ] Criação automática de diretórios
- [ ] Sistema de backup

#### 1.4 Sistema de Logs
- [ ] Logger estruturado
- [ ] Rotação de logs
- [ ] Diferentes níveis de log
- [ ] Armazenamento local

---

### **FASE 2: CONTROLE DO SERVIDOR (Semana 3-4)**

#### 2.1 Controle Básico do Servidor SCUM
- [ ] Iniciar servidor SCUM
- [ ] Parar servidor SCUM
- [ ] Reiniciar servidor SCUM
- [ ] Verificar status do servidor

#### 2.2 Scripts de Controle
- [ ] Script PowerShell para reiniciar
- [ ] Script Batch para parar
- [ ] Script Batch para iniciar
- [ ] Validação de scripts

#### 2.3 Integração com SteamCMD
- [ ] Atualização automática do servidor
- [ ] Verificação de atualizações
- [ ] Logs de atualização

#### 2.4 Monitoramento de Processos
- [ ] Verificação de processos SCUMServer
- [ ] Detecção de falhas
- [ ] Restart automático em caso de falha

---

### **FASE 3: SISTEMA DE AGENDAMENTO (Semana 5-6)**

#### 3.1 Scheduler Base
- [ ] Sistema de agendamento
- [ ] Execução de tarefas
- [ ] Estado persistente
- [ ] Configuração de intervalos

#### 3.2 Restart Automático
- [ ] Horários programados
- [ ] Notificações progressivas
- [ ] Sistema de timezone
- [ ] Validação de horários

#### 3.3 Tarefas Personalizadas
- [ ] Execução de comandos
- [ ] Limpeza de logs
- [ ] Backup automático
- [ ] Verificações de saúde

---

### **FASE 4: COMUNICAÇÃO (Semana 7-8)**

#### 4.1 API Client
- [ ] Cliente HTTP para comunicação
- [ ] Autenticação com frontend
- [ ] Envio de dados
- [ ] Recebimento de comandos

#### 4.2 Sistema de Mensagens
- [ ] Recebimento de mensagens globais
- [ ] Execução de comandos no jogo
- [ ] Confirmação de execução
- [ ] Logs de comunicação

#### 4.3 Sincronização
- [ ] Envio de status
- [ ] Sincronização de configurações
- [ ] Upload de logs
- [ ] Download de atualizações

---

### **FASE 5: FUNCIONALIDADES AVANÇADAS (Semana 9-10)**

#### 5.1 Sistema de Backup
- [ ] Backup automático de configurações
- [ ] Backup de dados do servidor
- [ ] Restauração de backups
- [ ] Limpeza de backups antigos

#### 5.2 Sistema de Notificações
- [ ] Notificações locais
- [ ] Integração com webhooks
- [ ] Alertas de sistema
- [ ] Notificações para proprietário

#### 5.3 Monitoramento Avançado
- [ ] Métricas de performance
- [ ] Alertas de falha
- [ ] Relatórios de status
- [ ] Análise de logs

---

### **FASE 6: FINALIZAÇÃO E EMPACOTAMENTO (Semana 11-12)**

#### 6.1 Preparação para Empacotamento
- [ ] Otimização de dependências
- [ ] Configuração do PyInstaller
- [ ] Testes de empacotamento
- [ ] Validação do executável

#### 6.2 Sistema de Instalação
- [ ] Instalador Windows
- [ ] Instalação automática de dependências
- [ ] Criação de atalhos
- [ ] Configuração de serviço Windows (opcional)

#### 6.3 Sistema de Atualização
- [ ] Verificação de atualizações
- [ ] Download de novas versões
- [ ] Atualização automática
- [ ] Rollback em caso de falha

#### 6.4 Testes e Validação
- [ ] Testes unitários
- [ ] Testes de integração
- [ ] Testes de carga
- [ ] Validação de funcionalidades

#### 6.5 Documentação
- [ ] README completo
- [ ] Documentação de API
- [ ] Guia de instalação
- [ ] Exemplos de uso

---

## 📊 Cronograma Detalhado

### **SEMANA 1-2: FUNDAÇÃO**
- [ ] Estrutura do projeto
- [ ] Sistema de identificação
- [ ] Configuração básica
- [ ] Sistema de logs

### **SEMANA 3-4: CONTROLE DO SERVIDOR**
- [ ] Controle básico do SCUM
- [ ] Scripts de controle
- [ ] Integração SteamCMD
- [ ] Monitoramento de processos

### **SEMANA 5-6: AGENDAMENTO**
- [ ] Scheduler base
- [ ] Restart automático
- [ ] Tarefas personalizadas
- [ ] Sistema de notificações

### **SEMANA 7-8: COMUNICAÇÃO**
- [ ] API Client
- [ ] Sistema de mensagens
- [ ] Sincronização
- [ ] Autenticação

### **SEMANA 9-10: FUNCIONALIDADES AVANÇADAS**
- [ ] Sistema de backup
- [ ] Notificações avançadas
- [ ] Monitoramento avançado
- [ ] Relatórios

### **SEMANA 11-12: FINALIZAÇÃO**
- [ ] Testes completos
- [ ] Documentação
- [ ] Empacotamento
- [ ] Preparação para distribuição

---

## 🎯 Marcos Importantes

### **MARCO 1 (Semana 2)**
✅ Backend funcional com identificação única

### **MARCO 2 (Semana 4)**
✅ Controle completo do servidor SCUM

### **MARCO 3 (Semana 6)**
✅ Sistema de agendamento funcionando

### **MARCO 4 (Semana 8)**
✅ Comunicação bidirecional com frontend

### **MARCO 5 (Semana 10)**
✅ Backend completo e funcional

### **MARCO 6 (Semana 12)**
✅ Backend pronto para distribuição

---

## 🚀 Funcionalidades Core

### **1. Controle do Servidor:**
- ✅ Iniciar servidor SCUM
- ✅ Parar servidor SCUM  
- ✅ Reiniciar servidor SCUM
- ✅ Verificar status do servidor
- ✅ Atualizar servidor via SteamCMD
- ✅ Notificações via webhook

### **2. Sistema de Agendamento:**
- ✅ Restart automático em horários programados
- ✅ Notificações progressivas
- ✅ Configuração de timezone
- ✅ Estado persistente

### **3. Sistema de Configuração:**
- ✅ Configuração centralizada
- ✅ Validação de arquivos críticos
- ✅ Backup automático
- ✅ Criação de diretórios

### **4. Sistema de Webhooks:**
- ✅ Notificações Discord
- ✅ Status do servidor
- ✅ Fallback HTTP

### **5. Sistema de Atualizações:**
- ✅ Verificação automática (24h)
- ✅ Atualizações obrigatórias
- ✅ Controle do proprietário
- ✅ Rollback manual
- ✅ Notificações Painel + Discord

---

## 💡 Vantagens da Abordagem

### **PARA O PROPRIETÁRIO:**
- ✅ Controle total do servidor local
- ✅ Funcionalidades offline
- ✅ Instalação simples (.exe)
- ✅ Configuração local
- ✅ Atualizações automáticas

### **PARA VOCÊ (DONO DA PLATAFORMA):**
- ✅ Controle centralizado
- ✅ Identificação única de cada backend
- ✅ Coleta de dados
- ✅ Comandos globais
- ✅ Sistema de licenciamento

---

**Última atualização**: 15/01/2025
**Versão**: 1.0.0
