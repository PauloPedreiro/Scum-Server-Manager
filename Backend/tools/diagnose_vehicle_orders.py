import argparse
import sqlite3
from datetime import datetime


def _print_rows(rows, limit=None):
    c = 0
    for r in rows:
        if limit is not None and c >= limit:
            break
        print(r)
        c += 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/SSM.db")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--days", type=int, default=1)
    p.add_argument("--steam-id", default=None)
    p.add_argument("--vehicle-code", default=None)
    args = p.parse_args()

    conn = sqlite3.connect(args.db, timeout=30.0)
    conn.row_factory = sqlite3.Row

    try:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='vehicle_order' LIMIT 1"
        ).fetchone()
        if not table_exists:
            print("vehicle_order exists: False")
            return
        print("vehicle_order exists: True")

        q_last = """
        SELECT
          order_id,
          idempotency_key,
          status,
          attempt_count,
          locked_by,
          locked_at,
          restart_cycle_id,
          requested_steam_id,
          requested_player_name,
          requested_vehicle_code,
          requested_vehicle_name,
          spawned_vehicle_entity_id,
          created_at,
          updated_at
        FROM vehicle_order
        ORDER BY datetime(created_at) DESC
        LIMIT ?
        """
        rows = conn.execute(q_last, (int(args.limit),)).fetchall()
        print("\n== last_orders ==")
        print(f"count={len(rows)}")
        for r in rows:
            print(
                " | ".join(
                    [
                        str(r["created_at"]),
                        str(r["status"]),
                        str(r["requested_steam_id"]),
                        str(r["requested_vehicle_code"]),
                        "order_id=" + str(r["order_id"]),
                        "spawned=" + str(r["spawned_vehicle_entity_id"]),
                        "attempts=" + str(r["attempt_count"]),
                    ]
                )
            )

        q_dupes = """
        SELECT
          requested_steam_id,
          requested_vehicle_code,
          COUNT(*) AS cnt,
          MIN(created_at) AS first_created_at,
          MAX(created_at) AS last_created_at
        FROM vehicle_order
        WHERE datetime(created_at) >= datetime('now', ?)
        GROUP BY requested_steam_id, requested_vehicle_code
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC, last_created_at DESC
        LIMIT 100
        """
        since_expr = f"-{int(args.days)} day"
        dupes = conn.execute(q_dupes, (since_expr,)).fetchall()
        print("\n== dupes_by_player_vehicle ==")
        print(f"days={args.days} count={len(dupes)}")
        for r in dupes:
            print(
                " | ".join(
                    [
                        str(r["requested_steam_id"]),
                        str(r["requested_vehicle_code"]),
                        "cnt=" + str(r["cnt"]),
                        "first=" + str(r["first_created_at"]),
                        "last=" + str(r["last_created_at"]),
                    ]
                )
            )

        q_processing = """
        SELECT order_id, status, attempt_count, locked_by, locked_at, created_at, updated_at
        FROM vehicle_order
        WHERE status = 'processing'
        ORDER BY datetime(updated_at) DESC
        LIMIT 200
        """
        processing = conn.execute(q_processing).fetchall()
        print("\n== processing ==")
        print(f"count={len(processing)}")
        for r in processing:
            print(
                " | ".join(
                    [
                        "order_id=" + str(r["order_id"]),
                        "attempts=" + str(r["attempt_count"]),
                        "locked_by=" + str(r["locked_by"]),
                        "locked_at=" + str(r["locked_at"]),
                        "created_at=" + str(r["created_at"]),
                        "updated_at=" + str(r["updated_at"]),
                    ]
                )
            )

        if args.steam_id and args.vehicle_code is not None:
            q_detail = """
            SELECT order_id, idempotency_key, status, attempt_count, spawned_vehicle_entity_id, created_at, updated_at
            FROM vehicle_order
            WHERE requested_steam_id = ?
              AND requested_vehicle_code = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 200
            """
            details = conn.execute(q_detail, (str(args.steam_id), int(args.vehicle_code))).fetchall()
            print("\n== details ==")
            print(f"steam_id={args.steam_id} vehicle_code={args.vehicle_code} count={len(details)}")
            for r in details:
                print(
                    " | ".join(
                        [
                            str(r["created_at"]),
                            str(r["status"]),
                            "order_id=" + str(r["order_id"]),
                            "idem=" + str(r["idempotency_key"]),
                            "spawned=" + str(r["spawned_vehicle_entity_id"]),
                            "attempts=" + str(r["attempt_count"]),
                        ]
                    )
                )

        print("\nDone at", datetime.now().isoformat(timespec="seconds"))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
