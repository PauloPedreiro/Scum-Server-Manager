const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const url = require('url');
const sqlite3 = require('sqlite3').verbose();

const LOG_DIR = process.env.SCUM_LOG_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/Logs';
const DB_PATH = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';
const DATA_DIR = path.join(__dirname, '..', 'src', 'data', 'bot');
const PROCESSED_PATH = path.join(DATA_DIR, 'processed_auto_registrations.json');
const WEBHOOKS_PATH = path.join(__dirname, '..', 'src', 'data', 'webhooks.json');

function readWebhooks() {
  if (!fs.existsSync(WEBHOOKS_PATH)) return {};
  try { return JSON.parse(fs.readFileSync(WEBHOOKS_PATH, 'utf8')); } catch { return {}; }
}

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

function latestChestLog(dir) {
  const files = fs.readdirSync(dir).filter(f => /^chest_ownership_\d+\.log$/i.test(f));
  if (files.length === 0) return null;
  return files.map(f => ({ f, t: fs.statSync(path.join(dir, f)).mtime.getTime() }))
              .sort((a, b) => b.t - a.t)[0].f;
}

function loadProcessed() {
  try { return JSON.parse(fs.readFileSync(PROCESSED_PATH, 'utf8')); } catch { return {}; }
}

function saveProcessed(map) {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(PROCESSED_PATH, JSON.stringify(map, null, 2));
}

function postJson(webhookUrl, payload) {
  return new Promise((resolve, reject) => {
    const parsed = url.parse(webhookUrl);
    const body = JSON.stringify(payload);
    const opts = {
      method: 'POST',
      hostname: parsed.hostname,
      path: parsed.path,
      port: parsed.protocol === 'https:' ? 443 : 80,
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
    };
    const client = parsed.protocol === 'https:' ? https : http;
    const req = client.request(opts, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, data }));
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

function findLinkedDiscord(steamId) {
  try {
    const linkedPath = path.join(__dirname, '..', 'src', 'data', 'bot', 'linked_users.json');
    if (!fs.existsSync(linkedPath)) return null;
    const linked = JSON.parse(fs.readFileSync(linkedPath, 'utf8'));
    for (const [discordId, info] of Object.entries(linked)) {
      if (String(info.steam_id) === String(steamId)) {
        return { discordId, username: info.username || null };
      }
    }
    return null;
  } catch {
    return null;
  }
}

function normalizeVehicleName(cls) {
  if (!cls) return 'Desconhecido';
  return String(cls).replace(/_ES$/i, '').replace(/^BPC_/i, '').replace(/_/g, ' ');
}

(async () => {
  try {
    const webhooks = readWebhooks();
    const webhookUrl = webhooks['auto-vehicle-registrations'];
    if (!webhookUrl) {
      console.error('Webhook auto-vehicle-registrations não configurado em webhooks.json');
      process.exit(1);
    }

    const logFile = latestChestLog(LOG_DIR);
    if (!logFile) {
      console.log('Nenhum log chest_ownership encontrado.');
      process.exit(0);
    }

    const content = fs.readFileSync(path.join(LOG_DIR, logFile), 'utf16le');
    const re = /(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*\w*Chest\w*\s*\(entity id:\s*(\d+)\)\s*ownership\s+claimed\.?\s*Owner:\s*(\d+)\s*\([^,]+,\s*([^\)]+)\)/ig;

    const claims = [];
    let m;
    while ((m = re.exec(content)) !== null) {
      claims.push({ ts: m[1], containerId: Number(m[2]), steamId: m[3], playerName: m[4] });
    }
    if (claims.length === 0) {
      console.log('Nenhuma linha compatível encontrada no log:', logFile);
      process.exit(0);
    }

    const processed = loadProcessed();
    const db = openDb(DB_PATH);

    for (const c of claims) {
      const key = String(c.containerId);
      if (processed[key]) continue; // já enviado

      // mapear container -> veículo
      const rows = await all(db, `SELECT e.id as container_id, e.class as container_class, e.parent_entity_id as vehicle_id,
                                          v.class as vehicle_class, vs.vehicle_asset_id
                                  FROM entity e
                                  LEFT JOIN entity v ON v.id = e.parent_entity_id
                                  LEFT JOIN vehicle_spawner vs ON vs.vehicle_entity_id = e.parent_entity_id
                                  WHERE e.id = ?`, [c.containerId]);
      if (!rows || rows.length === 0 || !rows[0].vehicle_id) {
        processed[key] = { status: 'no_vehicle', ts: c.ts };
        continue;
      }
      const row = rows[0];
      const vehicleId = row.vehicle_id;
      const vehicleName = normalizeVehicleName(row.vehicle_class || (row.vehicle_asset_id || '').replace('Vehicle:BPC_', ''));

      // vinculo discord
      const linked = findLinkedDiscord(c.steamId);
      const discordRef = linked ? `<@${linked.discordId}>` : 'Não vinculado';

      // montar embed
      const embed = {
        title: '🚗 Registro Automático de Veículo',
        description: 'Gerado a partir de Chest Ownership',
        color: 0x00cc66,
        fields: [
          { name: 'Nome do Veículo', value: vehicleName, inline: true },
          { name: 'ID do Veículo', value: String(vehicleId), inline: true },
          { name: 'Proprietário', value: `${c.playerName} (Steam: ${c.steamId})`, inline: false },
          { name: 'Discord', value: discordRef, inline: true },
          { name: 'Container', value: `${row.container_class || 'N/A'} • ID ${c.containerId}`, inline: true },
          { name: 'Data/Hora', value: `\`${c.ts}\``, inline: false }
        ]
      };

      const payload = { embeds: [embed] };
      try {
        const r = await postJson(webhookUrl, payload);
        if (r.status >= 200 && r.status < 300) {
          processed[key] = { status: 'sent', ts: c.ts, vehicleId };
          console.log(`✅ Enviado: ${vehicleName} (${vehicleId}) para ${c.playerName}`);
        } else {
          console.error('Falha ao enviar webhook:', r.status, r.data);
        }
      } catch (err) {
        console.error('Erro ao enviar webhook:', err.message);
      }
    }

    saveProcessed(processed);
    db.close();
  } catch (e) {
    console.error('Erro geral:', e.message);
    process.exit(1);
  }
})();
