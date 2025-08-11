const sqlite3 = require('sqlite3').verbose();

const dbPath = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';
const raw = process.argv[2];
if (!raw) {
  console.log('Uso: node scripts/trace_vehicle_links_live.js <ID>');
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
    const result = { id: Number(id) };

    // entity principal e relações diretas
    result.entity = await all(db, `SELECT id, class, owning_entity_id, parent_entity_id FROM entity WHERE id = ?`, [id]);
    result.entity_refs = await all(db, `SELECT id, class, owning_entity_id, parent_entity_id FROM entity WHERE owning_entity_id = ? OR parent_entity_id = ? LIMIT 50`, [id, id]);

    // vehicle_entity
    result.vehicle_entity = await all(db, `SELECT entity_id, item_container_entity_id, data FROM vehicle_entity WHERE entity_id = ? OR item_container_entity_id = ?`, [id, id]);

    // vehicle_spawner
    result.vehicle_spawner = await all(db, `SELECT vehicle_entity_id, vehicle_asset_id, vehicle_alias, is_vehicle_automatically_created, is_vehicle_functional FROM vehicle_spawner WHERE vehicle_entity_id = ?`, [id]);

    // vehicle_service (vincula veículo a perfil de usuário)
    result.vehicle_service = await all(db, `SELECT user_profile_id, vehicle_id FROM vehicle_service WHERE vehicle_id = ?`, [id]);

    // user_profile e user associados (se houver)
    if (result.vehicle_service.length > 0) {
      const upIds = [...new Set(result.vehicle_service.map(r => r.user_profile_id).filter(Boolean))];
      if (upIds.length > 0) {
        // descobrir colunas de user_profile
        const upCols = await all(db, `PRAGMA table_info(user_profile);`);
        const hasUserId = upCols.some(c => String(c.name).toLowerCase() === 'user_id');
        result.user_profile = await all(db, `SELECT * FROM user_profile WHERE id IN (${upIds.map(()=>'?').join(',')})`, upIds);
        if (hasUserId) {
          const userIds = [...new Set(result.user_profile.map(r => r.user_id).filter(Boolean))];
          if (userIds.length > 0) {
            result.user = await all(db, `SELECT * FROM user WHERE id IN (${userIds.map(()=>'?').join(',')})`, userIds);
          }
        }
      }
    }

    console.log(JSON.stringify(result, null, 2));
  } catch (e) {
    console.error('Erro na análise de vínculos:', e.message);
    process.exit(1);
  } finally {
    db.close();
  }
})();
