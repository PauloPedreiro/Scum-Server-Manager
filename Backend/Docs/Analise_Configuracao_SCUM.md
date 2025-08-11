# Análise dos Arquivos de Configuração do Servidor SCUM

## Visão Geral
Esta análise foi realizada nos arquivos localizados em `C:\Servers\scum\SCUM\Saved\Config\WindowsServer` e identifica as principais configurações e possibilidades de automação e integração com o sistema de gerenciamento.

## Arquivos Analisados

### 1. ServerSettings.ini
**Arquivo principal de configuração do servidor**

#### Configurações Gerais Importantes:
- **Nome do Servidor**: "BLUE SECTOR BRASIL PVE [LOOT 3X SKILL 4X]"
- **Descrição**: "BLUE SECTOR BRASIL PVE[LOOT 3X SKILL 4X]"
- **Máximo de Jogadores**: 64
- **Tipo de Servidor**: PVE
- **Mensagem de Boas-vindas**: "Seja Bem-Vindo ao Melhor Servidor PVE discord.gg/thGphdRYJv"
- **MOTD**: "Servidor PVE Leia as Regras discord.gg/thGphdRYJv, Reset 01:00 05:00 09:00 13:00 17:00 21:00"

#### Configurações de Fame Points:
- **Multiplicador de Fame**: 2.5x
- **Penalidade por Morte**: 10%
- **Penalidade por Ser Morto**: 25%
- **Recompensa por Kill**: 50%

#### Configurações de Skills (4x):
- Todas as skills configuradas com multiplicador 4.0x
- **Skills Incluídas**: Archery, Aviation, Awareness, Brawling, Camouflage, Cooking, Demolition, Driving, Endurance, Engineering, Farming, Handgun, Medical, MeleeWeapons, Motorcycle, Rifles, Running, Sniping, Stealth, Survival, Thievery

#### Configurações de Veículos:
- **Dreno de Combustível**: 0.8x (reduzido)
- **Dreno de Bateria**: 0.0x (desabilitado)
- **Dreno de Bateria por Dispositivos**: 0.8x
- **Dreno de Bateria por Inatividade**: 0.0x (desabilitado)
- **Carregamento por Alternador**: 1.0x
- **Carregamento por Dínamo**: 1.0x

#### Limites de Veículos:
- **Kinglet Duster**: 15 máx, 20 funcional
- **Dirtbike**: 15 máx, 25 funcional
- **Laika**: 30 máx, 50 funcional
- **Motorboat**: 8 máx, 12 funcional
- **Wolfswagen**: 20 máx, 40 funcional
- **Bicycle**: 10 máx, 0 funcional
- **Rager**: 40 máx, 60 funcional
- **Cruiser**: 15 máx, 25 funcional
- **Ris**: 15 máx, 25 funcional
- **Kinglet Mariner**: 10 máx, 15 funcional
- **Tractor**: 15 máx, 25 funcional

#### Configurações de Dano:
- **Dano Humano vs Humano**: 1.0x
- **Dano de Sentry**: 0.8x
- **Dano de Dropship**: 0.5x
- **Dano de Zombie**: 2.0x
- **Dano de Item Decay**: 0.5x
- **Dano de Food Decay**: 0.5x

#### Configurações de Respawn:
- **Respawn por Setor**: 200 pontos
- **Respawn por Shelter**: 500 pontos
- **Respawn por Squad**: 3000 pontos
- **Cooldown por Setor**: 30 segundos
- **Cooldown por Shelter**: 30 segundos
- **Cooldown por Squad**: 60 segundos

### 2. Game.ini
**Configurações específicas do jogo**

- **Perda de Constituição**: 0.2x (reduzida)
- **Dreno de Stamina**: 0.1x (reduzido)
- **Peso de Carregamento**: 5.0x (aumentado)
- **Verificação de Spawn no Oceano**: Habilitado
- **Feed de Kills**: Habilitado

### 3. GameUserSettings.ini
**Configurações de usuário do servidor**

#### Configurações de Tempo:
- **Velocidade do Tempo**: 3.0x (mais rápido que ServerSettings.ini que tem 9.0x)
- **Início do Dia**: 06:00
- **Amanhecer**: 05:30
- **Pôr do Sol**: 23:30
- **Escuridão Noturna**: -0.3

#### Configurações de Clima:
- **Frequência de Chuva**: 0.25x
- **Duração de Chuva**: 0.20x

#### Configurações de Cargo Drops:
- **Cooldown Mínimo**: 720 segundos (12 minutos)
- **Cooldown Máximo**: 720 segundos
- **Delay de Queda**: 180 segundos
- **Duração de Queda**: 20 segundos
- **Tempo de Auto-destruição**: 900 segundos

### 4. EconomyOverride.json
**Configurações de economia personalizadas**

Arquivo extenso com configurações de preços para itens específicos em diferentes traders:
- **Z_1_General**: Trader geral
- **Z_2_Weapons**: Trader de armas
- **Z_3_Saloon**: Saloon
- **Z_3_Hospital**: Hospital (inclui serviços de cirurgia plástica e upgrade BCU)

### 5. RaidTimes.json
**Horários de raid configurados**

- **Segunda a Quarta**: 10:00-11:30
- **Segunda, Quarta, Sexta**: 07:12-09:01
- **Quinta**: 21:00-23:45
- **Fim de Semana**: 12:00-15:00

### 6. AdminUsers.ini
**Lista de administradores**

Três Steam IDs configurados como administradores com permissão `[setgodmode]`:
- 76561198040636105
- 76561198398160339
- 76561197963358180

### 7. Pasta Loot/
**Configurações de loot personalizadas**

Estrutura de pastas:
- **Items/**: Configurações de itens
- **Nodes/**: Configurações de nós de loot
- **Spawners/**: Configurações de spawners

## Possibilidades de Automação e Integração

### 1. **Sistema de Backup Automático**
- Backup automático das configurações antes de alterações
- Versionamento das configurações
- Restauração rápida em caso de problemas

### 2. **Interface Web para Configuração**
- Interface para alterar configurações sem editar arquivos manualmente
- Validação de configurações antes de aplicar
- Preview das mudanças

### 3. **Monitoramento de Performance**
- Monitoramento de tick rate (10-40 configurado)
- Alertas quando performance cai
- Logs de performance

### 4. **Sistema de Whitelist/Blacklist**
- Interface para gerenciar usuários banidos
- Sistema de whitelist para eventos
- Integração com Discord para notificações

### 5. **Gerenciamento de Horários de Raid**
- Interface para configurar horários de raid
- Notificações automáticas no Discord
- Integração com sistema de proteção

### 6. **Sistema de Fame Points**
- Interface para adicionar/remover fame points
- Logs de transações
- Integração com sistema de recompensas

### 7. **Monitoramento de Veículos**
- Rastreamento de veículos no servidor
- Alertas para veículos em zonas proibidas
- Sistema de limpeza automática

### 8. **Configurações de Loot**
- Interface para configurar spawners
- Sistema de rotação de loot
- Monitoramento de economia

### 9. **Sistema de Restart Automático**
- Restarts programados baseados nas configurações
- Notificações antes do restart
- Backup automático antes do restart

### 10. **Integração com Discord**
- Notificações de eventos importantes
- Comandos para administradores
- Sistema de tickets

## Recomendações

### Prioridade Alta:
1. **Sistema de Backup Automático** - Proteger configurações
2. **Interface Web para Configuração** - Facilitar administração
3. **Monitoramento de Performance** - Manter servidor estável
4. **Sistema de Fame Points** - Integrar com sistema existente

### Prioridade Média:
5. **Gerenciamento de Horários de Raid** - Melhorar experiência
6. **Sistema de Whitelist/Blacklist** - Controle de acesso
7. **Monitoramento de Veículos** - Manter ordem no servidor

### Prioridade Baixa:
8. **Configurações de Loot** - Otimizar economia
9. **Sistema de Restart Automático** - Automação
10. **Integração com Discord** - Comunicação

## Conclusão

O servidor SCUM está bem configurado com multiplicadores de loot 3x e skills 4x, configurado como PVE. As configurações mostram um servidor bem estruturado com sistema de fame points, horários de raid definidos e economia personalizada.

O sistema de gerenciamento atual pode ser expandido significativamente para incluir automação de configurações, monitoramento avançado e integração com sistemas externos, melhorando a experiência tanto para administradores quanto para jogadores. 