const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

const LOG_DIR = process.argv[2] || 'C:/Servers/scum/SCUM/Saved/SaveFiles/Logs';
const DB_PATH = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';

function openDb(dbPath) {
  const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
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

async function mapContainersToVehicles(db, containerIds) {
  if (containerIds.length === 0) return new Map();
  const out = new Map();
  const batchSize = 400;
  for (let i = 0; i < containerIds.length; i += batchSize) {
    const batch = containerIds.slice(i, i + batchSize);
    const sql = `SELECT e.id as container_id, e.class as container_class, e.parent_entity_id as vehicle_id,
                        v.class as vehicle_class, vs.vehicle_asset_id, vs.is_vehicle_functional
                 FROM entity e
                 LEFT JOIN entity v ON v.id = e.parent_entity_id
                 LEFT JOIN vehicle_spawner vs ON vs.vehicle_entity_id = e.parent_entity_id
                 WHERE e.id IN (${batch.map(() => '?').join(',')})`;
    const rows = await all(db, sql, batch);
    rows.forEach(r => out.set(r.container_id, r));
  }
  return out;
}

(async () => {
  try {
    // Listar logs chest_ownership_*.log
    const files = fs.readdirSync(LOG_DIR)
      .filter(f => /^chest_ownership_\d+\.log$/i.test(f))
      .sort();

    if (files.length === 0) {
      console.log('Nenhum log chest_ownership encontrado.');
      process.exit(0);
    }

    // Regex flexível
    const re = /(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*\w*Chest\w*\s*\(entity id:\s*(\d+)\)\s*ownership\s+claimed\.?\s*Owner:\s*(\d+)\s*\([^,]+,\s*([^\)]+)\)/ig;

    const claims = [];
    for (const f of files) {
      const content = fs.readFileSync(path.join(LOG_DIR, f), 'utf8');
      let m;
      while ((m = re.exec(content)) !== null) {
        claims.push({ ts: m[1], containerId: Number(m[2]), steamId: m[3], playerName: m[4], file: f });
      }
    }

    if (claims.length === 0) {
      console.log('Nenhuma linha de ownership encontrada nos logs.');
      process.exit(0);
    }

    // Consultar DB
    const db = openDb(DB_PATH);
    const uniqueContainerIds = [...new Set(claims.map(c => c.containerId))];
    const map = await mapContainersToVehicles(db, uniqueContainerIds);
    db.close();

    const linked = claims.map(c => ({
      timestamp: c.ts,
      log_file: c.file,
      owner_steam: c.steamId,
      owner_name: c.playerName,
      container_entity_id: c.containerId,
      container_class: map.get(c.containerId)?.container_class || null,
      vehicle_entity_id: map.get(c.containerId)?.vehicle_id || null,
      vehicle_class: map.get(c.containerId)?.vehicle_class || null,
      vehicle_asset_id: map.get(c.containerId)?.vehicle_asset_id || null,
      vehicle_functional: map.get(c.containerId)?.is_vehicle_functional ?? null
    })).filter(r => r.vehicle_entity_id);

    console.log(JSON.stringify(linked, null, 2));
  } catch (e) {
    console.error('Erro:', e.message);
    process.exit(1);
  }
})();
