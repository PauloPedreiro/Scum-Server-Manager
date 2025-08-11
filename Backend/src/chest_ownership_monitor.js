const fs = require('fs');
const path = require('path');
const url = require('url');
const http = require('http');
const https = require('https');
const sqlite3 = require('sqlite3').verbose();
const logger = require('./logger');

class ChestOwnershipMonitor {
  constructor() {
    this.logsDir = process.env.SCUM_LOG_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/Logs';
    this.dbPath = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';
    this.statePath = path.join(__dirname, 'data', 'bot', 'processed_auto_registrations.json');
    this.webhooksPath = path.join(__dirname, 'data', 'webhooks.json');
    this.intervalMs = 15000; // 15s
    this.timer = null;
    this.webhookUrl = null;
    this.processed = {};
    this.imagesDir = path.join(__dirname, 'data', 'imagens', 'carros');
    this.autoRecordPath = path.join(__dirname, 'data', 'players', 'vehicle-record-auto.json');
    this.tempDir = path.join(__dirname, 'data', 'temp');
  }

  loadWebhooks() {
    try {
      const data = fs.readFileSync(this.webhooksPath, 'utf8');
      const json = JSON.parse(data);
      this.webhookUrl = json['auto-vehicle-registrations'] || null;
    } catch {
      this.webhookUrl = null;
    }
  }

  loadState() {
    try {
      const data = fs.readFileSync(this.statePath, 'utf8');
      this.processed = JSON.parse(data);
    } catch {
      this.processed = {};
    }
  }

  saveState() {
    try {
      const dir = path.dirname(this.statePath);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(this.statePath, JSON.stringify(this.processed, null, 2));
    } catch (e) {
      // ignore
    }
  }

  latestLog() {
    if (!fs.existsSync(this.logsDir)) return null;
    const files = fs.readdirSync(this.logsDir).filter(f => /^chest_ownership_\d+\.log$/i.test(f));
    if (files.length === 0) return null;
    return files.map(f => ({ f, t: fs.statSync(path.join(this.logsDir, f)).mtime.getTime() }))
      .sort((a, b) => b.t - a.t)[0].f;
  }

  postJson(webhookUrl, payload) {
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
        res.on('data', c => data += c);
        res.on('end', () => resolve({ status: res.statusCode, data }));
      });
      req.on('error', reject);
      req.write(body);
      req.end();
    });
  }

  postWebhookWithFile(webhookUrl, embed, filePath, fileName) {
    return new Promise((resolve, reject) => {
      const parsed = url.parse(webhookUrl);
      const boundary = '----DiscordFormBoundary' + Math.random().toString(16).slice(2);
      const header = `--${boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n`;
      const payload = JSON.stringify({ embeds: [embed] });
      const middle = `\r\n--${boundary}\r\nContent-Disposition: form-data; name="files[0]"; filename="${fileName}"\r\nContent-Type: application/octet-stream\r\n\r\n`;
      const footer = `\r\n--${boundary}--\r\n`;

      let fileBuffer;
      try {
        fileBuffer = fs.readFileSync(filePath);
      } catch (e) {
        return reject(e);
      }

      const bodyBuffer = Buffer.concat([
        Buffer.from(header, 'utf8'),
        Buffer.from(payload, 'utf8'),
        Buffer.from(middle, 'utf8'),
        fileBuffer,
        Buffer.from(footer, 'utf8')
      ]);

      const opts = {
        method: 'POST',
        hostname: parsed.hostname,
        path: parsed.path,
        port: parsed.protocol === 'https:' ? 443 : 80,
        headers: {
          'Content-Type': `multipart/form-data; boundary=${boundary}`,
          'Content-Length': bodyBuffer.length
        }
      };
      const client = parsed.protocol === 'https:' ? https : http;
      const req = client.request(opts, (res) => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => resolve({ status: res.statusCode, data }));
      });
      req.on('error', reject);
      req.write(bodyBuffer);
      req.end();
    });
  }

  findDiscordLink(steamId) {
    try {
      const linkedPath = path.join(__dirname, 'data', 'bot', 'linked_users.json');
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

  normalizeVehicleName(clsOrAsset) {
    if (!clsOrAsset) return 'Desconhecido';
    let s = String(clsOrAsset);
    s = s.replace('Vehicle:BPC_', '');
    s = s.replace(/_ES$/i, '');
    s = s.replace(/^BPC_/i, '');
    return s.replace(/_/g, ' ');
  }

  mapVehicleToImage(vehicleName) {
    if (!vehicleName) return null;
    const name = String(vehicleName).toLowerCase();
    const candidates = [
      // Veículos comuns
      { keys: ['tractor'], file: 'Tractor_ES.png' },
      { keys: ['wolfswagen', 'wolf'], file: 'wolfswagen_es.png' },
      { keys: ['rager'], file: 'rager_es.png' },
      { keys: ['laika'], file: 'laika_es.png' },
      { keys: ['cruiser'], file: 'Cruiser_ES.png' },
      { keys: ['ris'], file: 'RIS_ES.png' },
      { keys: ['kinglet', 'duster'], file: 'kinglet_duster_es.png' },
      { keys: ['kinglet', 'mariner'], file: 'Kinglet_Mariner.png' },
      { keys: ['dirt', 'bike', 'dirtbike'], file: 'dirtbike_es.png' },
      { keys: ['city', 'bike'], file: 'City_Bike.png' },
      { keys: ['wooden', 'motorboat'], file: 'Wooden_Motorboat.png' },
      { keys: ['sup'], file: 'SUP.png' },
      // Barba
      { keys: ['barba'], file: 'BPC_Barba.png' },
      // Wheelbarrows
      { keys: ['wheelbarrow', 'metal'], file: 'Metal_Wheelbarrow.png' },
      { keys: ['wheelbarrow', 'improvised'], file: 'Improvised_Wheelbarrow.png' }
    ];
    for (const c of candidates) {
      if (c.keys.every(k => name.includes(k))) {
        const full = path.join(this.imagesDir, c.file);
        if (fs.existsSync(full)) return { fileName: c.file, fullPath: full };
      }
    }
    // fallback: dirtbike image if exists
    const fallback = path.join(this.imagesDir, 'dirtbike_es.png');
    if (fs.existsSync(fallback)) return { fileName: 'dirtbike_es.png', fullPath: fallback };
    return null;
  }

  // Converte timestamp do log (YYYY.MM.DD-HH.mm.ss) para formato brasileiro DD/MM/YYYY HH:MM:SS
  formatBrazilianDateTimeFromLog(ts) {
    try {
      if (!ts || typeof ts !== 'string' || !ts.includes('-')) return ts;
      const [datePart, timePart] = ts.split('-');
      const [year, month, day] = datePart.split('.').map(n => parseInt(n, 10));
      const [hour, minute, second] = timePart.split('.').map(n => parseInt(n, 10));
      const pad = (n) => String(n).padStart(2, '0');
      if ([year, month, day, hour, minute, second].some(v => Number.isNaN(v))) return ts;
      return `${pad(day)}/${pad(month)}/${year} ${pad(hour)}:${pad(minute)}:${pad(second)}`;
    } catch (_) {
      return ts;
    }
  }

  openDb() {
    const db = new sqlite3.Database(this.dbPath, sqlite3.OPEN_READONLY, (err) => {
      if (err) {
        logger.error('Erro ao abrir DB live', { error: err.message });
      }
    });
    try { db.configure('busyTimeout', 8000); } catch (_) {}
    return db;
  }

  async mapContainer(db, containerId) {
    const sql = `SELECT e.id as container_id, e.class as container_class, e.parent_entity_id as vehicle_id,
                        v.class as vehicle_class, vs.vehicle_asset_id
                 FROM entity e
                 LEFT JOIN entity v ON v.id = e.parent_entity_id
                 LEFT JOIN vehicle_spawner vs ON vs.vehicle_entity_id = e.parent_entity_id
                 WHERE e.id = ?`;
    return new Promise((resolve) => {
      db.all(sql, [containerId], (e, rows) => {
        if (e || !rows || rows.length === 0) return resolve(null);
        resolve(rows[0]);
      });
    });
  }

  async getVehicleRealId(containerId) {
    try {
      const sqlite3 = require('sqlite3').verbose();
      const dbPath = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';
      const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY);

      return new Promise((resolve) => {
        db.all(`SELECT e.id as container_id, e.parent_entity_id as vehicle_id
                FROM entity e
                WHERE e.id = ?`, [containerId], (err, rows) => {
          db.close();
          if (err || !rows || rows.length === 0) {
            resolve(containerId); // Se não encontrar, retorna o ID original
          } else {
            const row = rows[0];
            // Se tem vehicle_id, retorna o ID do veículo real
            if (row.vehicle_id) {
              resolve(row.vehicle_id);
            } else {
              resolve(containerId); // Se não tem veículo vinculado, retorna o container
            }
          }
        });
      });
    } catch (error) {
      console.error('Erro ao buscar ID real do veículo:', error);
      return containerId;
    }
  }

  async getVehicleRealName(vehicleId) {
    try {
      const sqlite3 = require('sqlite3').verbose();
      const dbPath = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';
      const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY);

      return new Promise((resolve) => {
        db.all(`SELECT e.id as container_id, e.class as container_class, e.parent_entity_id as vehicle_id,
                        v.class as vehicle_class, vs.vehicle_asset_id
                        FROM entity e
                        LEFT JOIN entity v ON v.id = e.parent_entity_id
                        LEFT JOIN vehicle_spawner vs ON vs.vehicle_entity_id = e.parent_entity_id
                        WHERE e.id = ?`, [vehicleId], (err, rows) => {
          db.close();
          if (err || !rows || rows.length === 0) {
            resolve(null);
          } else {
            const row = rows[0];
            // Se tem vehicle_id, é um container vinculado a um veículo
            if (row.vehicle_id) {
                resolve({
                    name: this.normalizeVehicleDisplayName(row.vehicle_class || row.vehicle_asset_id),
                    vehicleId: row.vehicle_id
                });
            } else {
                // É um container sem veículo vinculado
                resolve({
                    name: this.normalizeVehicleDisplayName(row.container_class),
                    vehicleId: row.container_id
                });
            }
          }
        });
      });
    } catch (error) {
      console.error('Erro ao buscar nome real do veículo:', error);
      return null;
    }
  }

  async tick() {
    try {
      this.loadWebhooks();
      if (!this.webhookUrl) return;

      const file = this.latestLog();
      if (!file) return;
      // Copiar o arquivo de log para a pasta temporária antes de ler
      try { if (!fs.existsSync(this.tempDir)) fs.mkdirSync(this.tempDir, { recursive: true }); } catch (_) {}
      const sourcePath = path.join(this.logsDir, file);
      const tempPath = path.join(this.tempDir, file);
      try { fs.copyFileSync(sourcePath, tempPath); } catch (e) { logger.error('Falha ao copiar chest log para temp', { error: e.message }); return; }
      const content = fs.readFileSync(tempPath, 'utf16le');
      const re = /(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*\w*Chest\w*\s*\(entity id:\s*(\d+)\)\s*ownership\s+claimed\.?\s*Owner:\s*(\d+)\s*\([^,]+,\s*([^\)]+)\)/ig;

      let m;
      const db = this.openDb();
      const events = [];

      while ((m = re.exec(content)) !== null) {
        const key = `${m[1]}_${m[2]}`;
        if (this.processed[key]) continue;
        const ts = m[1];
        const containerId = Number(m[2]);
        const steamId = m[3];
        const playerName = m[4];

        const link = await this.mapContainer(db, containerId);
        if (!link || !link.vehicle_id) {
          this.processed[key] = { status: 'no_vehicle', ts };
          continue;
        }

        const vehicleId = link.vehicle_id;
        const vehicleName = this.normalizeVehicleName(link.vehicle_class || link.vehicle_asset_id);
        const linked = this.findDiscordLink(steamId);
        const discordRef = linked ? `<@${linked.discordId}>` : 'Não vinculado';

        // Criar embed básico (será atualizado no loop com informações reais)
        const embed = {
            title: '🚗 Registro Automático de Veículo',
            color: 0x00cc66,
            author: { name: playerName },
            fields: [
                { name: 'Nome do Veículo', value: vehicleName, inline: true },
                { name: 'ID do Veículo', value: String(vehicleId), inline: true },
                { name: 'Proprietário', value: playerName, inline: false },
                { name: 'Discord', value: discordRef, inline: true },
                { name: 'Data/Hora', value: `\`${this.formatBrazilianDateTimeFromLog(ts)}\``, inline: false }
            ]
        };

        const img = this.mapVehicleToImage(vehicleName);
        if (img) {
          // usar attachment para thumbnail
          embed.thumbnail = { url: `attachment://${img.fileName}` };
        }

        events.push({ key, embed, vehicleName, vehicleId, playerName, image: img, steamId });
      }

      // send embeds
      for (const ev of events) {
        try {
          // Buscar o ID do veículo real
          const realVehicleId = await this.getVehicleRealId(ev.vehicleId);
          
          // Buscar o nome do veículo real
          const vehicleInfo = await this.getVehicleRealName(ev.vehicleId);
          const displayVehicleName = vehicleInfo ? vehicleInfo.name : ev.vehicleName;

          // Atualizar o embed com as informações corretas
          ev.embed.fields[0].value = displayVehicleName; // Nome do Veículo
          ev.embed.fields[1].value = String(realVehicleId); // ID do Veículo

          let res;
          if (ev.image) {
            res = await this.postWebhookWithFile(this.webhookUrl, ev.embed, ev.image.fullPath, ev.image.fileName);
          } else {
            res = await this.postJson(this.webhookUrl, { embeds: [ev.embed] });
          }
          if (res.status >= 200 && res.status < 300) {
            logger.info('Auto registro enviado', { vehicleId: realVehicleId, player: ev.playerName });
            this.processed[ev.key] = { status: 'sent', vehicleId: realVehicleId };

            // Atualizar banco automático local (vehicle-record-auto.json)
            await this.addToAutoRecord(ev.steamId, ev.playerName, realVehicleId, displayVehicleName);
          } else {
            logger.error('Falha ao enviar auto registro', { status: res.status, data: res.data });
          }
        } catch (e) {
          logger.error('Erro ao enviar webhook auto registro', { error: e.message });
        }
      }

      db.close();

      // Remover arquivo temporário após processamento
      try { if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath); } catch (_) {}

      if (events.length > 0) this.saveState();
    } catch (e) {
      logger.error('Erro no monitor Chest Ownership', { error: e.message });
    }
  }

  addToAutoRecord(steamId, playerName, vehicleId, vehicleType) {
    return new Promise((resolve) => {
      try {
        const dir = path.dirname(this.autoRecordPath);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        let record = {};
        if (fs.existsSync(this.autoRecordPath)) {
          try { record = JSON.parse(fs.readFileSync(this.autoRecordPath, 'utf8')); } catch (_) { record = {}; }
        }
        if (!record[steamId]) {
          record[steamId] = {
            playerName,
            steamId,
            activeVehicles: [],
            lastUpdated: new Date().toISOString()
          };
        }
        const exists = record[steamId].activeVehicles.find(v => String(v.vehicleId) === String(vehicleId));
        if (!exists) {
          record[steamId].activeVehicles.push({
            vehicleId: String(vehicleId),
            vehicleType: vehicleType || 'DESCONHECIDO',
            registeredAt: new Date().toISOString()
          });
        }
        record[steamId].lastUpdated = new Date().toISOString();
        fs.writeFileSync(this.autoRecordPath, JSON.stringify(record, null, 2));
      } catch (e) {
        logger.error('Erro ao atualizar vehicle-record-auto.json', { error: e.message });
      }
      resolve();
    });
  }

  start() {
    this.loadState();
    this.loadWebhooks();
    if (!this.webhookUrl) {
      logger.error('Webhook auto-vehicle-registrations não configurado');
      return;
    }
    if (this.timer) return;
    this.timer = setInterval(() => this.tick(), this.intervalMs);
    logger.server('ChestOwnershipMonitor iniciado');
  }

  stop() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }
}

module.exports = ChestOwnershipMonitor;
