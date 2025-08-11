const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

// Caminhos dos bancos
const ORIGINAL_DB_PATH = 'C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db';
const TEMP_DB_PATH = path.join(__dirname, '..', 'src', 'data', 'vehicles', 'SCUM_temp.db');

// Função para copiar banco de dados
function copyDatabase() {
    try {
        if (!fs.existsSync(ORIGINAL_DB_PATH)) {
            throw new Error('Banco original não encontrado');
        }
        
        // Criar diretório se não existir
        const tempDir = path.dirname(TEMP_DB_PATH);
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true });
        }
        
        // Copiar arquivo
        fs.copyFileSync(ORIGINAL_DB_PATH, TEMP_DB_PATH);
        console.log('✅ Banco copiado com sucesso');
        return true;
    } catch (error) {
        console.error('❌ Erro ao copiar banco:', error.message);
        return false;
    }
}

// Função para consultar veículo por ID
function queryVehicleById(vehicleId) {
    return new Promise((resolve, reject) => {
        if (!fs.existsSync(TEMP_DB_PATH)) {
            reject(new Error('Banco temporário não encontrado'));
            return;
        }
        
        const db = new sqlite3.Database(TEMP_DB_PATH, sqlite3.OPEN_READONLY, (err) => {
            if (err) {
                reject(err);
                return;
            }
            
            // Buscar nas tabelas de veículos
            const queries = [
                `SELECT * FROM vehicle_entity WHERE entity_id = ${vehicleId}`,
                `SELECT * FROM vehicle_spawner WHERE vehicle_entity_id = ${vehicleId}`,
                `SELECT * FROM entity WHERE id = ${vehicleId} AND class LIKE '%Vehicle%'`,
                `SELECT * FROM vehicle_entity WHERE id = ${vehicleId}`,
                `SELECT * FROM vehicle_spawner WHERE id = ${vehicleId}`,
                `SELECT * FROM entity WHERE id = ${vehicleId}`
            ];
            
            let results = [];
            let completedQueries = 0;
            
            queries.forEach((query, index) => {
                db.all(query, (err, rows) => {
                    if (!err && rows && rows.length > 0) {
                        results.push({
                            query: query,
                            data: rows
                        });
                    }
                    
                    completedQueries++;
                    if (completedQueries === queries.length) {
                        db.close();
                        
                        if (results.length > 0) {
                            // Extrair informações do veículo
                            const vehicleInfo = extractVehicleInfo(results, vehicleId);
                            resolve(vehicleInfo);
                        } else {
                            reject(new Error(`Veículo com ID ${vehicleId} não encontrado`));
                        }
                    }
                });
            });
        });
    });
}

// Consulta o veículo diretamente no banco ORIGINAL (sem copiar)
function queryVehicleByIdLive(vehicleId) {
    return new Promise((resolve, reject) => {
        const db = new sqlite3.Database(ORIGINAL_DB_PATH, sqlite3.OPEN_READONLY, (err) => {
            if (err) {
                reject(err);
                return;
            }
            try { db.configure && db.configure('busyTimeout', 8000); } catch (_) {}

            const queries = [
                `SELECT * FROM vehicle_entity WHERE entity_id = ${vehicleId}`,
                `SELECT * FROM vehicle_spawner WHERE vehicle_entity_id = ${vehicleId}`,
                `SELECT * FROM entity WHERE id = ${vehicleId} AND class LIKE '%Vehicle%'`,
                `SELECT * FROM vehicle_entity WHERE id = ${vehicleId}`,
                `SELECT * FROM vehicle_spawner WHERE id = ${vehicleId}`,
                `SELECT * FROM entity WHERE id = ${vehicleId}`
            ];

            let results = [];
            let completedQueries = 0;

            queries.forEach((query) => {
                db.all(query, (qErr, rows) => {
                    if (!qErr && rows && rows.length > 0) {
                        results.push({ query, data: rows });
                    }
                    completedQueries++;
                    if (completedQueries === queries.length) {
                        db.close();
                        if (results.length > 0) {
                            const vehicleInfo = extractVehicleInfo(results, vehicleId);
                            resolve(vehicleInfo);
                        } else {
                            reject(new Error(`Veículo com ID ${vehicleId} não encontrado`));
                        }
                    }
                });
            });
        });
    });
}

// Função para extrair informações do veículo
function extractVehicleInfo(results, vehicleId) {
    let vehicleInfo = {
        id: vehicleId,
        name: null,
        type: null,
        assetId: null,
        class: null
    };
    
    results.forEach(result => {
        if (result.data && result.data.length > 0) {
            const data = result.data[0];
            
            // Extrair informações do vehicle_spawner
            if (data.vehicle_asset_id) {
                vehicleInfo.assetId = data.vehicle_asset_id;
                // Extrair nome do asset ID (ex: Vehicle:BPC_Kinglet_Mariner -> BPC_Kinglet_Mariner)
                const assetMatch = data.vehicle_asset_id.match(/Vehicle:(.+)/);
                if (assetMatch) {
                    vehicleInfo.name = assetMatch[1];
                    vehicleInfo.type = assetMatch[1].replace(/^BPC_/, '').replace(/_/g, ' ');
                }
            }
            
            // Extrair informações do entity
            if (data.class) {
                vehicleInfo.class = data.class;
                if (!vehicleInfo.name) {
                    // Tentar extrair nome da classe
                    const classMatch = data.class.match(/(.+)_ES$/);
                    if (classMatch) {
                        vehicleInfo.name = classMatch[1];
                        vehicleInfo.type = classMatch[1].replace(/^BPC_/, '').replace(/_/g, ' ');
                    }
                }
            }
        }
    });
    
    return vehicleInfo;
}

// Função para mapear nome do veículo para imagem
function mapVehicleToImage(vehicleName) {
    if (!vehicleName) return null;
    
    // Normalizar nome do veículo
    const normalizedName = vehicleName
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_|_$/g, '');
    
    // Mapeamento de nomes para arquivos de imagem
    const imageMapping = {
        'kinglet_mariner': 'kinglet_mariner.png',
        'cruiser': 'cruiser.png',
        'wolfswagen': 'wolfswagen_es.png',
        'wolfsvagen': 'wolfswagen_es.png',
        'rager': 'rager_es.png',
        'tractor': 'tractor_es.png',
        'laika': 'laika_es.png',
        'kinglet_duster': 'kinglet_duster_es.png',
        'dirtbike': 'dirtbike_es.png',
        'quad': 'dirtbike_es.png',
        'ranger': 'dirtbike_es.png',
        'helicopter': 'dirtbike_es.png',
        'airplane': 'dirtbike_es.png',
        'car': 'wolfswagen_es.png',
        'truck': 'tractor_es.png',
        'boat': 'kinglet_mariner.png'
    };
    
    // Procurar por correspondência exata ou parcial
    for (const [key, image] of Object.entries(imageMapping)) {
        if (normalizedName.includes(key) || key.includes(normalizedName)) {
            return image;
        }
    }
    
    // Retornar imagem padrão se não encontrar
    return 'dirtbike_es.png';
}

// Função para deletar banco temporário
function deleteTempDatabase() {
    try {
        if (fs.existsSync(TEMP_DB_PATH)) {
            fs.unlinkSync(TEMP_DB_PATH);
            console.log('✅ Banco temporário deletado');
            return true;
        }
        return true;
    } catch (error) {
        console.error('❌ Erro ao deletar banco temporário:', error.message);
        return false;
    }
}

// Versão live (sem cópia do banco)
async function getVehicleInfoLive(vehicleId) {
    const vehicleInfo = await queryVehicleByIdLive(vehicleId);
    vehicleInfo.imageFile = mapVehicleToImage(vehicleInfo.name);
    return vehicleInfo;
}

/**
 * Valida em lote uma lista de IDs de veículos consultando o banco SCUM.db
 * Retorna um mapa { [vehicleId: string]: boolean } indicando se o veículo existe no banco
 */
async function validateVehicleIds(vehicleIds) {
    if (!Array.isArray(vehicleIds) || vehicleIds.length === 0) {
        return {};
    }

    const result = {};
    try {
        // Garantir cópia do banco para leitura
        if (!copyDatabase()) {
            throw new Error('Falha ao copiar banco');
        }

        // Abrir conexão única
        await new Promise((resolve, reject) => {
            const db = new sqlite3.Database(TEMP_DB_PATH, sqlite3.OPEN_READONLY, (err) => {
                if (err) return reject(err);

                let processed = 0;
                const total = vehicleIds.length;

                vehicleIds.forEach((id) => {
                    // Verificar existência nas tabelas mais confiáveis
                    const queries = [
                        `SELECT id FROM entity WHERE id = ${id} AND class LIKE '%Vehicle%' LIMIT 1`,
                        `SELECT id FROM vehicle_entity WHERE id = ${id} LIMIT 1`,
                        `SELECT vehicle_entity_id as id FROM vehicle_spawner WHERE vehicle_entity_id = ${id} LIMIT 1`
                    ];

                    let found = false;

                    const runNext = (qIndex) => {
                        if (qIndex >= queries.length) {
                            result[id] = found;
                            processed++;
                            if (processed === total) {
                                db.close();
                                resolve();
                            }
                            return;
                        }

                        db.all(queries[qIndex], (errQ, rows) => {
                            if (!errQ && Array.isArray(rows) && rows.length > 0) {
                                found = true;
                                result[id] = true;
                                processed++;
                                if (processed === total) {
                                    db.close();
                                    resolve();
                                }
                            } else {
                                runNext(qIndex + 1);
                            }
                        });
                    };

                    runNext(0);
                });
            });
        });
    } catch (error) {
        console.error('❌ Erro ao validar IDs de veículos:', error.message);
    } finally {
        // Sempre remover banco temporário
        deleteTempDatabase();
    }

    return result;
}

// Função principal para consultar veículo
async function getVehicleInfo(vehicleId) {
    try {
        console.log(`🔍 Consultando veículo ID: ${vehicleId}`);
        
        // 1. Copiar banco
        if (!copyDatabase()) {
            throw new Error('Falha ao copiar banco');
        }
        
        // 2. Consultar veículo
        const vehicleInfo = await queryVehicleById(vehicleId);
        
        // 3. Mapear imagem
        vehicleInfo.imageFile = mapVehicleToImage(vehicleInfo.name);
        
        // 4. Deletar banco temporário
        deleteTempDatabase();
        
        console.log('✅ Consulta concluída:', vehicleInfo);
        return vehicleInfo;
        
    } catch (error) {
        console.error('❌ Erro na consulta:', error.message);
        deleteTempDatabase();
        throw error;
    }
}

// Função para listar imagens disponíveis
function listAvailableImages() {
    const imagesPath = path.join(__dirname, '..', 'src', 'data', 'imagens', 'carros');
    
    if (!fs.existsSync(imagesPath)) {
        console.log('📁 Criando pasta de imagens...');
        fs.mkdirSync(imagesPath, { recursive: true });
        return [];
    }
    
    const files = fs.readdirSync(imagesPath);
    const imageFiles = files.filter(file => 
        file.toLowerCase().endsWith('.png') || 
        file.toLowerCase().endsWith('.jpg') || 
        file.toLowerCase().endsWith('.jpeg')
    );
    
    console.log('🖼️ Imagens disponíveis:');
    imageFiles.forEach(file => console.log(`   - ${file}`));
    
    return imageFiles;
}

// Executar se chamado diretamente
if (require.main === module) {
    const vehicleId = process.argv[2];
    
    if (!vehicleId) {
        console.log('❌ Uso: node vehicle_database_query.js <ID_DO_VEICULO>');
        console.log('📋 Exemplo: node vehicle_database_query.js 3911111');
        process.exit(1);
    }
    
    getVehicleInfo(vehicleId)
        .then(info => {
            console.log('\n📊 Informações do Veículo:');
            console.log('========================');
            console.log(`ID: ${info.id}`);
            console.log(`Nome: ${info.name}`);
            console.log(`Tipo: ${info.type}`);
            console.log(`Asset ID: ${info.assetId}`);
            console.log(`Classe: ${info.class}`);
            console.log(`Imagem: ${info.imageFile}`);
        })
        .catch(error => {
            console.error('❌ Erro:', error.message);
        })
        .finally(() => {
            listAvailableImages();
        });
}

module.exports = { 
    getVehicleInfo, 
    getVehicleInfoLive,
    copyDatabase, 
    queryVehicleById, 
    queryVehicleByIdLive,
    extractVehicleInfo, 
    mapVehicleToImage, 
    deleteTempDatabase,
    listAvailableImages,
    validateVehicleIds
}; 