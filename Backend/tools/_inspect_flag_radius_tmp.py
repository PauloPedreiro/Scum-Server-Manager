import sqlite3

DB = "C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db"
FLAG_ID = 5

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

flag = cur.execute("SELECT * FROM base_element_flag WHERE element_id=?", (FLAG_ID,)).fetchone()
print("base_element_flag row:")
print(dict(flag) if flag else None)

be = cur.execute("SELECT * FROM base_element WHERE element_id=?", (FLAG_ID,)).fetchone()
print("base_element row:")
print(dict(be) if be else None)

if be and be["base_id"] is not None:
    base = cur.execute("SELECT * FROM base WHERE id=?", (be["base_id"],)).fetchone()
    print("base row:")
    print(dict(base) if base else None)

print("\n-- columns in key tables --")
for t in ("base_element_flag", "base_element", "base"):
    cols = [r["name"] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()]
    print(t, cols)

print("\n-- tables whose DDL mentions radius/range --")
rows = cur.execute(
    "SELECT name, sql FROM sqlite_master WHERE type='table' AND (lower(sql) LIKE '%radius%' OR lower(sql) LIKE '%range%')"
).fetchall()
print([r["name"] for r in rows])

print("\n-- columns containing radius/range --")
tables = [r["name"] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
hits = []
for t in tables:
    try:
        info = cur.execute(f"PRAGMA table_info({t})").fetchall()
    except Exception:
        continue
    for c in info:
        nm = c["name"]
        if "radius" in nm.lower() or "range" in nm.lower():
            hits.append((t, nm))
print(hits)

conn.close()
