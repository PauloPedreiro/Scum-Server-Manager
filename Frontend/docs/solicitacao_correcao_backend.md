# Solicitação de Ajuste: Otimização de Performance no Relatório de Jogadores Online

## 1. Descrição do Problema
O frontend está exibindo erros de timeout de rede genéricos no console (ex: `Não foi possível conectar ao servidor backend. Verifique se o backend está rodando e acessível.`) ao carregar os gráficos e estatísticas da página inicial (Home). 

O problema ocorre porque as consultas de agregação de contagem de jogadores online demoram mais de 15 segundos para responder (estourando o timeout configurado no proxy e no cliente Axios).

---

## 2. Componentes e Endpoints Impactados no Backend
* **Endpoints:**
  * `GET /api/reports/players/chart-data`
  * `GET /api/reports/players/hourly-average`
  * `GET /api/reports/players/daily-average`
* **Arquivo do Blueprint:** `app/routes/reports.py`
* **Classe Responsável:** `PlayerCountCalculator` em `core/reports/player_count_calculator.py`

---

## 3. Causa Raiz da Lentidão
No arquivo `core/reports/player_count_calculator.py`, a função `_get_all_events_in_period` realiza a seguinte query:
```sql
SELECT steam_id, action, timestamp
FROM player_logins
WHERE timestamp <= ?
ORDER BY timestamp ASC, steam_id ASC
```
Como o parâmetro é a data final (`end_date` = momento atual), a consulta retorna **todo o histórico da tabela `player_logins` desde o início dos tempos**. Em servidores ativos, essa tabela cresce rapidamente (atualmente possui **77.032 registros**).

Em seguida, o método `get_hourly_average` (e semelhantes) calcula o total de jogadores online em diversos momentos (snapshots):
* Para um relatório de 7 dias com snapshots a cada 15 min, são calculados **672 pontos no tempo**.
* Em cada ponto, o método `_calculate_online_count_at` percorre a lista completa de eventos na memória (`events`) em Python puro.
* **Cálculo da complexidade:** `672 snapshots * 77.032 eventos = ~51.765.500 iterações` em um loop Python por requisição. Isso consome 100% de uma thread de CPU por vários segundos.

---

## 4. Solução Proposta (Refatoração do `PlayerCountCalculator`)
Podemos reduzir o processamento a frações de segundo se evitarmos ler e iterar sobre o histórico completo do banco. A lógica ideal é:

1. **Obter o Estado Inicial (Jogadores Online no início do período):**
   Fazer uma única consulta rápida para saber quem estava online exatamente no momento `start_date` (ex: há 7 dias).
2. **Consultar Apenas Eventos do Período:**
   Buscar no banco somente os registros de `player_logins` criados **entre** `start_date` e `end_date`.
3. **Simular em Memória (Replay local):**
   Percorrer em ordem cronológica apenas os eventos do período selecionado para atualizar o conjunto de jogadores online.

### Exemplo de Implementação Otimizada:

```python
class PlayerCountCalculator:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_online_players_at_timestamp(self, conn: sqlite3.Connection, timestamp: datetime) -> set:
        """Retorna o conjunto (set) de SteamIDs online em um momento específico."""
        query = """
        WITH last_events AS (
            SELECT 
                steam_id,
                action,
                MAX(timestamp) as last_timestamp
            FROM player_logins
            WHERE timestamp <= ?
            GROUP BY steam_id
        )
        SELECT steam_id 
        FROM last_events
        WHERE action = 'login';
        """
        cursor = conn.cursor()
        cursor.execute(query, [timestamp.isoformat()])
        return {row[0] for row in cursor.fetchall()}

    def get_hourly_average(
        self, start_date: datetime, end_date: datetime, snapshots_per_hour: int = 4
    ) -> List[Dict]:
        
        # 1. Carregar quem já estava online no início do período
        from core.database.connector import DatabaseConnector
        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0) as conn:
                online_set = self.get_online_players_at_timestamp(conn, start_date)
                
                # 2. Carregar apenas os eventos ocorridos DENTRO do período de análise
                query_events = """
                SELECT steam_id, action, timestamp
                FROM player_logins
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                """
                cursor = conn.cursor()
                cursor.execute(query_events, [start_date.isoformat(), end_date.isoformat()])
                events = []
                for row in cursor.fetchall():
                    try:
                        events.append((row[0], row[1], datetime.fromisoformat(row[2])))
                    except ValueError:
                        continue
        except Exception as e:
            raise Exception(f"Erro ao ler banco de dados: {e}")

        # 3. Gerar a lista de timestamps dos snapshots
        snapshots = []
        interval_minutes = 60 // snapshots_per_hour
        
        current = start_date
        while current <= end_date:
            snapshots.append(current)
            current += timedelta(minutes=interval_minutes)

        # 4. Replay linear dos eventos nos snapshots (O(N) de iterações em vez de O(N * M))
        event_idx = 0
        num_events = len(events)
        snapshot_counts = {h: [] for h in range(24)}

        for snap_time in snapshots:
            # Avançar os eventos cronologicamente até o momento do snapshot atual
            while event_idx < num_events and events[event_idx][2] <= snap_time:
                steam_id, action, _ = events[event_idx]
                if action == "login":
                    online_set.add(steam_id)
                elif action == "logout":
                    online_set.discard(steam_id)
                event_idx += 1
            
            # Guardar a contagem para a hora deste snapshot
            snapshot_counts[snap_time.hour].append(len(online_set))

        # 5. Formatar o resultado final
        results = []
        for hour in range(24):
            counts = snapshot_counts[hour]
            if counts:
                results.append({
                    "hour": hour,
                    "average": round(sum(counts) / len(counts), 2),
                    "min": min(counts),
                    "max": max(counts),
                    "samples": len(counts)
                })
            else:
                results.append({
                    "hour": hour, "average": 0.0, "min": 0, "max": 0, "samples": 0
                })
                
        return results
```

---

## 5. Resultados Esperados
* O tempo de resposta para carregar os gráficos na Home deve cair de **15~20 segundos** para **menos de 200 milissegundos**.
* Fim dos travamentos de thread de CPU no backend e eliminação total dos erros de `Não foi possível conectar ao servidor backend` no console do frontend.
