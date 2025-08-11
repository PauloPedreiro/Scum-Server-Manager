const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

// Caminho do banco live
const DB_PATH = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';
const OUTPUT = path.resolve('vehicle_ids.txt');

function openDbLive(dbPath) {
  const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
    if (err) {
      console.error('Erro ao abrir DB em read-only:', err.message);
    }
  });
  try { db.configure('busyTimeout', 10000); } catch (_) {}
  return db;
}

(async () => {
  try {
    console.log('🔍 Lendo banco live (read-only):', DB_PATH);

    const db = openDbLive(DB_PATH);

    const sql = "SELECT DISTINCT id FROM (SELECT entity_id AS id FROM vehicle_entity UNION SELECT vehicle_entity_id AS id FROM vehicle_spawner UNION SELECT id FROM entity WHERE class LIKE '%Vehicle%') t ORDER BY id;";

    const writeStream = fs.createWriteStream(OUTPUT, { encoding: 'utf8' });
    let count = 0;

    await new Promise((resolve, reject) => {
      db.each(sql,
        (err, row) => {
          if (err) return reject(err);
          count += 1;
          writeStream.write(String(row.id) + '\r\n');
        },
        (err, rows) => {
          if (err) return reject(err);
          writeStream.end(() => resolve(rows));
        }
      );
    });

    db.close();
    console.log(`✅ ${OUTPUT} gerado com ${count} IDs`);
  } catch (error) {
    console.error('❌ Falha ao gerar vehicle_ids.txt:', error.message);
    process.exit(1);
  }
})();
