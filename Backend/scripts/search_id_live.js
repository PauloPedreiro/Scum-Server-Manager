const sqlite3 = require('sqlite3').verbose();

const dbPath = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';
const raw = process.argv[2];
if (!raw) {
  console.log('Uso: node scripts/search_id_live.js <ID_NUMERICO>');
  process.exit(1);
}
const id = String(raw);

function openDb(path) {
  const db = new sqlite3.Database(path, sqlite3.OPEN_READONLY, (err) => {
    if (err) {
      console.error('Erro ao abrir DB:', err.message);
      process.exit(1);
    }
  });
  try { db.configure('busyTimeout', 8000); } catch (_) {}
  return db;
}

function all(db, sql, params = []) {
  return new Promise((resolve, reject) => db.all(sql, params, (e, rows) => e ? reject(e) : resolve(rows)));
}

(async () => {
  const db = openDb(dbPath);
  try {
    const tables = await all(db, "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;");
    const hits = [];

    for (const { name } of tables) {
      const cols = await all(db, `PRAGMA table_info(${name});`);
      if (!cols || cols.length === 0) continue;

      for (const c of cols) {
        const colName = String(c.name);
        const lc = colName.toLowerCase();
        const isIdLike = lc.includes('id');
        if (!isIdLike) continue;

        // tentar match exato como texto
        const rows = await all(db, `SELECT * FROM ${name} WHERE CAST(${colName} AS TEXT) = ? LIMIT 3`, [id]);
        if (rows.length > 0) {
          hits.push({ table: name, column: colName, sample: rows });
        }
      }
    }

    if (hits.length === 0) {
      console.log('NAO_ENCONTRADO');
    } else {
      console.log(JSON.stringify(hits, null, 2));
    }
  } catch (e) {
    console.error('Erro na busca:', e.message);
    process.exit(1);
  } finally {
    db.close();
  }
})();
