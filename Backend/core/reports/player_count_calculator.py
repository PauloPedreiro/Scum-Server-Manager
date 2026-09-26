"""
Calculadora de Contagem de Jogadores Online
Usa dados de player_logins para reconstruir histórico
"""
from core.database.connector import DatabaseConnector

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class PlayerCountCalculator:
    """Calcula jogadores online usando dados de player_logins"""

    def __init__(self, db_path: str):
        """
        Inicializar calculadora
        
        Args:
            db_path: Caminho para o banco SSM.db
        """
        self.db_path = db_path

    def get_online_players_at_timestamp(self, conn: sqlite3.Connection, timestamp: datetime) -> set:
        """
        Retorna o conjunto (set) de SteamIDs online em um momento específico.
        """
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

    def _load_initial_state_and_events(
        self, start_date: datetime, end_date: datetime
    ) -> Tuple[set, List[Tuple[str, str, datetime]]]:
        """
        Retorna o conjunto de steam_ids online no início e os eventos no período.
        """
        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0) as conn:
                online_set = self.get_online_players_at_timestamp(conn, start_date)
                
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
                return online_set, events
        except Exception as e:
            raise Exception(f"Erro ao ler banco de dados para período: {e}")

    def _get_all_events_in_period(
        self, start_date: datetime, end_date: datetime
    ) -> List[Tuple[str, str, datetime]]:
        """
        Busca todos os eventos de login/logout até o final do período.
        Mantido para retrocompatibilidade.
        """
        query = """
        SELECT steam_id, action, timestamp
        FROM player_logins
        WHERE timestamp <= ?
        ORDER BY timestamp ASC, steam_id ASC
        """
        
        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute(query, [end_date.isoformat()])
                results = cursor.fetchall()
                
                events = []
                for row in results:
                    steam_id, action, timestamp_str = row
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        events.append((steam_id, action, timestamp))
                    except (ValueError, AttributeError):
                        continue
                
                return events
        except Exception as e:
            raise Exception(f"Erro ao buscar eventos: {e}")

    def _calculate_online_count_at(
        self, events: List[Tuple[str, str, datetime]], timestamp: datetime
    ) -> int:
        """
        Calcula quantos jogadores estavam online em um timestamp específico
        usando eventos já carregados em memória.
        Mantido para retrocompatibilidade.
        """
        last_events = {}
        for steam_id, action, event_time in events:
            if event_time > timestamp:
                break
            if steam_id not in last_events or event_time > last_events[steam_id][1]:
                last_events[steam_id] = (action, event_time)
        return sum(1 for action, _ in last_events.values() if action == "login")

    def get_players_online_at(self, timestamp: datetime) -> int:
        """
        Calcula quantos jogadores estavam online em um timestamp específico.
        """
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
        SELECT COUNT(*) 
        FROM last_events
        WHERE action = 'login';
        """

        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute(query, [timestamp.isoformat()])
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            raise Exception(f"Erro ao calcular jogadores online: {e}")

    def get_hourly_average(
        self, start_date: datetime, end_date: datetime, snapshots_per_hour: int = 4
    ) -> List[Dict]:
        """
        Calcula média de jogadores por hora do dia no período.
        Usa múltiplos snapshots por hora para maior precisão com algoritmo de replay linear.
        """
        # Carregar estado inicial e eventos do período
        online_set, events = self._load_initial_state_and_events(start_date, end_date)

        # Gerar a lista de timestamps dos snapshots em ordem cronológica
        snapshots = []
        interval_minutes = 60 // snapshots_per_hour
        
        current = start_date
        while current <= end_date:
            snapshots.append(current)
            current += timedelta(minutes=interval_minutes)

        # Replay linear dos eventos nos snapshots
        event_idx = 0
        num_events = len(events)
        snapshot_counts = {h: [] for h in range(24)}

        for snap_time in snapshots:
            while event_idx < num_events and events[event_idx][2] <= snap_time:
                steam_id, action, _ = events[event_idx]
                if action == "login":
                    online_set.add(steam_id)
                elif action == "logout":
                    online_set.discard(steam_id)
                event_idx += 1
            
            snapshot_counts[snap_time.hour].append(len(online_set))

        # Formatar o resultado final
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

    def get_daily_average(
        self,
        start_date: datetime,
        end_date: datetime,
        interval_minutes: int = 15,
    ) -> List[Dict]:
        """
        Calcula média de jogadores por dia com snapshots a cada X minutos.
        Usa algoritmo de replay linear para alta performance.
        """
        # Carregar estado inicial e eventos do período
        online_set, events = self._load_initial_state_and_events(start_date, end_date)

        # Gerar a lista de timestamps dos snapshots
        snapshots = []
        interval = timedelta(minutes=interval_minutes)
        current = start_date
        while current <= end_date:
            snapshots.append(current)
            current += interval

        # Replay linear dos eventos nos snapshots
        event_idx = 0
        num_events = len(events)
        daily_data = {}

        for snap_time in snapshots:
            while event_idx < num_events and events[event_idx][2] <= snap_time:
                steam_id, action, _ = events[event_idx]
                if action == "login":
                    online_set.add(steam_id)
                elif action == "logout":
                    online_set.discard(steam_id)
                event_idx += 1
            
            date_key = snap_time.date()
            if date_key not in daily_data:
                daily_data[date_key] = []
            daily_data[date_key].append(len(online_set))

        # Formatar o resultado final
        results = []
        for date, counts in sorted(daily_data.items()):
            if counts and len(counts) > 0:
                results.append(
                    {
                        "date": date.isoformat(),
                        "average": round(sum(counts) / len(counts), 2),
                        "min": min(counts),
                        "max": max(counts),
                        "peak": max(counts),
                        "lowest": min(counts),
                        "samples": len(counts),
                    }
                )

        return sorted(results, key=lambda x: x["date"])

    def get_chart_data(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "hour",
    ) -> Dict:
        """
        Retorna dados formatados para gráfico.
        """
        if granularity == "hour":
            data = self.get_hourly_average(start_date, end_date)
            labels = [f"{h['hour']:02d}:00" for h in data]
            values = [h["average"] for h in data]
        else:  # 'day'
            data = self.get_daily_average(start_date, end_date)
            labels = [d["date"] for d in data]
            values = [d["average"] for d in data]

        if not values:
            return {
                "labels": [],
                "datasets": [
                    {
                        "label": "Jogadores Online",
                        "data": [],
                        "average": 0,
                        "peak": 0,
                        "lowest": 0,
                    }
                ],
            }

        # Calcular estatísticas
        average = round(sum(values) / len(values), 2) if values else 0
        peak = max(values) if values else 0
        lowest = min(values) if values else 0

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Jogadores Online",
                    "data": values,
                    "average": average,
                    "peak": peak,
                    "lowest": lowest,
                }
            ],
        }

    def get_absolute_peak(
        self,
        start_date: datetime,
        end_date: datetime,
        interval_minutes: int = 15,
    ) -> Optional[Dict]:
        """
        Encontra o timestamp exato (dia + hora) com o maior número de jogadores online.
        """
        # Carregar estado inicial e eventos do período
        online_set, events = self._load_initial_state_and_events(start_date, end_date)

        # Gerar a lista de timestamps dos snapshots
        snapshots = []
        interval = timedelta(minutes=interval_minutes)
        current = start_date
        while current <= end_date:
            snapshots.append(current)
            current += interval

        # Replay linear dos eventos nos snapshots
        event_idx = 0
        num_events = len(events)
        
        peak_timestamp = None
        peak_count = -1

        for snap_time in snapshots:
            while event_idx < num_events and events[event_idx][2] <= snap_time:
                steam_id, action, _ = events[event_idx]
                if action == "login":
                    online_set.add(steam_id)
                elif action == "logout":
                    online_set.discard(steam_id)
                event_idx += 1
            
            count = len(online_set)
            if count > peak_count:
                peak_count = count
                peak_timestamp = snap_time

        if peak_timestamp is None:
            return None

        return {
            "timestamp": peak_timestamp.isoformat(),
            "date": peak_timestamp.date().isoformat(),
            "hour": peak_timestamp.hour,
            "minute": peak_timestamp.minute,
            "players_count": peak_count,
            "formatted": peak_timestamp.strftime("%Y-%m-%d %H:%M"),
        }
