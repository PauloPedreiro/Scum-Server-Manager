# Sistema de Ranking de Pescadores

## 📋 Visão Geral

O Sistema de Ranking de Pescadores é um módulo completo que extrai dados de pesca do banco `SCUM.db`, gera rankings detalhados e os envia automaticamente para o Discord via webhook. O sistema executa uma vez por dia no horário configurado e armazena os dados no banco `SSM.db`.

## 🏗️ Arquitetura

### Componentes Principais

- **`FishingRankingExtractor`**: Extrai dados de pesca do SCUM.db
- **`FishingRankingGenerator`**: Gera rankings formatados em texto
- **`FishingRankingNotifier`**: Envia rankings para Discord via webhook
- **`FishingRankingManager`**: Coordena todo o processo
- **`FishingRankingScheduler`**: Gerencia execução automática

### Fluxo de Funcionamento

```
1. Scheduler executa diariamente no horário configurado
   ↓
2. Extractor conecta ao SCUM.db e extrai dados de pesca
   ↓
3. Generator processa dados e cria ranking em 7 partes
   ↓
4. Notifier envia cada parte para Discord via webhook
   ↓
5. Manager salva dados no SSM.db para histórico
```

## 📊 Estrutura de Dados

### Tabela `fishing_rankings` (SSM.db)

```sql
CREATE TABLE IF NOT EXISTS fishing_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ranking_date TEXT NOT NULL,
    total_players INTEGER NOT NULL,
    active_fishers INTEGER NOT NULL,
    total_fish_caught INTEGER NOT NULL,
    water_temperature REAL NOT NULL,
    ranking_data TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Índices para Performance

```sql
CREATE INDEX IF NOT EXISTS idx_fishing_rankings_date ON fishing_rankings(ranking_date);
CREATE INDEX IF NOT EXISTS idx_fishing_rankings_created_at ON fishing_rankings(created_at);
```

## ⚙️ Configuração

### Arquivo `config.json`

```json
{
  "fishing_ranking": {
    "enabled": true,
    "schedule_time": "15:32",
    "scum_db_path": "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
    "max_players": 20,
    "send_parts": true,
    "description": "Sistema de ranking diário de pescadores - executa uma vez por dia no horário configurado"
  }
}
```

### Arquivo `webhooks.json`

```json
{
  "fishing_ranking": "https://discord.com/api/webhooks/1432384151675469835/vUqHwztYRHRzKFzgZ7fBc-UrNkU4pjM4MyYk27eTD4y3txFqnuGP7eqla3hkkosntKHZ"
}
```

## 🎯 Formato do Ranking

O sistema gera **7 partes** distintas enviadas para o Discord:

### Parte 1: Cabeçalho e Estatísticas Gerais
```
RANKING DE PESCADORES - SERVIDOR SCUM

Data: 27/10/2025 - 16:06:51
Temperatura da Agua: 25.0°C
Atualizado: Dados extraidos do SCUM.db

ESTATISTICAS GERAIS DO SERVIDOR

Total de jogadores no servidor: 350
Jogadores que pescaram: 22 (6.3%)
Jogadores que nunca pescaram: 328
Total de peixes capturados: 481 peixes
```

### Parte 2: TOP 20 Pescadores Mais Ativos
```
TOP 20 PESCADORES MAIS ATIVOS

Pos | Player          | Fish   | kg       | Length
----|-----------------|--------|----------|--------
  1 | Til4toxico      |    208 |   48.6kg |  165.5cm
  2 | Reav            |     65 |   42.5kg |  149.0cm
```

### Parte 3: Estatísticas Detalhadas dos Pescadores
```
ESTATISTICAS DETALHADAS DOS PESCADORES

Pos | Player          | Mantidos | Soltos | L Quebradas
----|-----------------|----------|--------|------------
  1 | Til4toxico      |      121 |     87 |         123
  2 | Reav            |       62 |      3 |          73
```

### Parte 4: Ranking por Espécie de Peixe
```
RANKING POR ESPECIE DE PEIXE

Bass:
Pos | Player       | Qtd | Kg     | cm
----|--------------|-----|--------|--------
  1 | Reav         |  15 | 42.5kg | 149.0cm
  2 | El Barto     |   4 |  2.8kg |  36.1cm
```

### Parte 5: Recordes Especiais
```
RECORDES ESPECIAIS

PEIXE MAIS PESADO CAPTURADO:
Jogador: Til4toxico
Peso: 48.6 kg
Comprimento: 165.5 cm
```

### Parte 6: Análise de Dados
```
ANALISE DE DADOS

DISTRIBUICAO POR ESPECIE:
Bass: 41 peixes (24.6%)
Catfish: 10 peixes (6.0%)

PADROES DE COMPORTAMENTO:
• Til4toxico: Pesca agressiva (muitas linhas quebradas)
• Reav: Pesca agressiva (muitas linhas quebradas)
```

### Parte 7: Rodapé e Dicas
```
PROXIMA ATUALIZACAO: 28/10/2025 - 16:06:51

DICAS DE PESCA BASEADAS NOS DADOS:
- Foque em uma especie especifica para dominar o ranking
- Cuidado com linhas quebradas - pesque com eficiencia
- Experimente diferentes tipos de iscas para cada especie
- Melhor horario: 06:00 - 08:00 e 18:00 - 20:00
- Temperatura ideal da agua: 20-25°C
```

## 🚀 API Endpoints

### POST `/api/fishing-ranking/test`
Executa manualmente a geração e envio do ranking.

**Resposta de Sucesso:**
```json
{
  "message": "Ranking de pescadores executado com sucesso",
  "success": true
}
```

**Resposta de Erro:**
```json
{
  "error": "Falha ao executar ranking de pescadores",
  "success": false
}
```

### GET `/api/fishing-ranking/status`
Obtém o status e configuração atual do sistema.

**Resposta de Sucesso:**
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "schedule_time": "15:32",
    "scum_db_path": "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
    "max_players": 20,
    "webhook_configured": true
  }
}
```

## 🔧 Migração Automática

O sistema está integrado ao `DatabaseManager` e cria automaticamente a tabela `fishing_rankings` quando necessário:

- ✅ **Criação automática** da tabela se não existir
- ✅ **Índices otimizados** para performance
- ✅ **Compatibilidade** com bancos existentes
- ✅ **Sem intervenção manual** necessária

## 📈 Monitoramento

### Logs do Sistema
- ✅ Inicialização do sistema
- ✅ Execução diária agendada
- ✅ Extração de dados do SCUM.db
- ✅ Geração de rankings
- ✅ Envio para Discord
- ✅ Salvamento no banco

### Métricas Disponíveis
- Total de jogadores no servidor
- Jogadores que pescaram
- Total de peixes capturados
- Temperatura da água
- Histórico de rankings gerados

## 🛠️ Manutenção

### Limpeza de Dados Antigos
```python
# Exemplo de limpeza (implementar conforme necessário)
def cleanup_old_rankings(days_to_keep=30):
    """Limpar rankings antigos"""
    # Implementar lógica de limpeza
```

### Backup de Dados
- ✅ Dados salvos no `SSM.db`
- ✅ Histórico completo de rankings
- ✅ Possibilidade de análise temporal

## 🎯 Próximas Funcionalidades

### Funcionalidades Planejadas
- 📊 **Gráficos de evolução** dos rankings
- 🏆 **Sistema de conquistas** para pescadores
- 📈 **Estatísticas avançadas** por período
- 🔔 **Notificações personalizadas** para recordes
- 📱 **Dashboard web** para visualização

### Melhorias Técnicas
- ⚡ **Cache de dados** para performance
- 🔄 **Sincronização incremental** de dados
- 📊 **Métricas de performance** do sistema
- 🛡️ **Validação robusta** de dados

## 📚 Exemplos de Uso

### Teste Manual via API
```bash
curl -X POST http://localhost:3000/api/fishing-ranking/test
```

### Verificação de Status
```bash
curl -X GET http://localhost:3000/api/fishing-ranking/status
```

### Consulta de Histórico
```sql
-- Últimos 10 rankings
SELECT * FROM fishing_rankings 
ORDER BY created_at DESC 
LIMIT 10;

-- Ranking por data específica
SELECT * FROM fishing_rankings 
WHERE ranking_date = '2025-10-27';
```

## 🔍 Troubleshooting

### Problemas Comuns

1. **Webhook não configurado**
   - Verificar `webhooks.json`
   - Confirmar URL do webhook

2. **SCUM.db não encontrado**
   - Verificar caminho em `config.json`
   - Confirmar permissões de acesso

3. **Erro de encoding**
   - Sistema remove emojis automaticamente
   - Verificar logs para detalhes

4. **Falha na execução**
   - Verificar logs do sistema
   - Testar via endpoint `/test`

### Logs Importantes
- `FishingRankingManager inicializado`
- `Ranking gerado e enviado com sucesso`
- `Dados salvos no banco SSM.db`
- `Parte X/7 do ranking enviada com sucesso`

## 📝 Changelog

### v1.0.0 (27/10/2025)
- ✅ Sistema completo implementado
- ✅ Extração de dados do SCUM.db
- ✅ Geração de rankings em 7 partes
- ✅ Envio automático para Discord
- ✅ Armazenamento no SSM.db
- ✅ Execução diária agendada
- ✅ API endpoints para teste e status
- ✅ Migração automática de banco
- ✅ Formatação otimizada e alinhada
- ✅ Sistema robusto e testado