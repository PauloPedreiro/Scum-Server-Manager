const sqlite3 = require('sqlite3').verbose();

const dbPath = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';
const raw = process.argv[2];
if (!raw) {
  console.log('Uso: node scripts/find_locks_for_id_live.js <ENTITY_ID>');
  process.exit(1);
}
const targetId = String(raw);

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

    const lockKeywords = ['lock','locked','padlock','code','combination','trava','tranca'];

    for (const { name } of tables) {
      const cols = await all(db, `PRAGMA table_info(${name});`);
      if (!cols || cols.length === 0) continue;

      const colNames = cols.map(c => String(c.name));
      const hasLockCols = colNames.some(n => lockKeywords.some(k => n.toLowerCase().includes(k)));
      if (!hasLockCols) continue;

      // tentar relacionar pelo entity_id, vehicle_entity_id, target_entity_id, owner_entity_id etc.
      const idCols = colNames.filter(n => /(^|_)entity_id$/.test(n.toLowerCase()) || n.toLowerCase().includes('entity_id') || n.toLowerCase().includes('vehicle_entity_id') || /(^|_)owner.*id$/.test(n.toLowerCase()));
      for (const idCol of idCols) {
        const rows = await all(db, `SELECT * FROM ${name} WHERE CAST(${idCol} AS TEXT) = ? LIMIT 10`, [targetId]);
        if (rows.length > 0) {
          hits.push({ table: name, by: idCol, rows });
        }
      }

      // fallback: procurar o próprio valor do ID em quaisquer colunas lock-related
      for (const c of cols) {
        const cn = String(c.name);
        if (!lockKeywords.some(k => cn.toLowerCase().includes(k))) continue;
        const rows2 = await all(db, `SELECT * FROM ${name} WHERE CAST(${cn} AS TEXT) = ? LIMIT 5`, [targetId]);
        if (rows2.length > 0) {
          hits.push({ table: name, by: cn, rows: rows2 });
        }
      }
    }

    if (hits.length === 0) {
      console.log('NAO_ENCONTRADO_TRAVAS');
    } else {
      console.log(JSON.stringify(hits, null, 2));
    }
  } catch (e) {
    console.error('Erro na busca de travas:', e.message);
    process.exit(1);
  } finally {
    db.close();
  }
})();
