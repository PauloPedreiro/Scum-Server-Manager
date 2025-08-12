const fs = require('fs');
const path = require('path');
const logger = require('./logger');

class ConfigMigrator {
    constructor() {
        this.configPath = path.join(__dirname, 'data', 'server', 'config.json');
        this.backupPath = path.join(__dirname, 'data', 'server', 'config.backup.json');
    }

    // Verificar se precisa migrar
    needsMigration(config) {
        if (!config.scheduler || !config.scheduler.endpoints) {
            return false;
        }

        // Verificar se algum endpoint já está no novo formato (objeto)
        return config.scheduler.endpoints.some(endpoint => typeof endpoint === 'string');
    }

    // Fazer backup do config atual
    createBackup(config) {
        try {
            fs.writeFileSync(this.backupPath, JSON.stringify(config, null, 2), 'utf8');
            logger.info('Backup do config.json criado', { backupPath: this.backupPath });
            return true;
        } catch (error) {
            logger.error('Erro ao criar backup do config.json', { error: error.message });
            return false;
        }
    }

    // Migrar endpoints para o novo formato
    migrateEndpoints(endpoints) {
        const migratedEndpoints = [];
        
        for (const endpoint of endpoints) {
            if (typeof endpoint === 'string') {
                // Endpoint antigo (string) - migrar para objeto
                if (endpoint === '/api/bunkers/status') {
                    // Bunkers com intervalo de 30 minutos
                    migratedEndpoints.push({
                        path: endpoint,
                        interval: 1800000, // 30 minutos
                        enabled: true
                    });
                    logger.info('Endpoint migrado para novo formato', { 
                        endpoint, 
                        interval: '30 minutos' 
                    });
                } else {
                    // Outros endpoints com intervalo padrão de 30 segundos
                    migratedEndpoints.push({
                        path: endpoint,
                        interval: 30000, // 30 segundos
                        enabled: true
                    });
                    logger.info('Endpoint migrado para novo formato', { 
                        endpoint, 
                        interval: '30 segundos' 
                    });
                }
            } else {
                // Endpoint já está no novo formato (objeto)
                migratedEndpoints.push(endpoint);
            }
        }

        return migratedEndpoints;
    }

    // Executar migração
    migrate() {
        try {
            // Verificar se o arquivo existe
            if (!fs.existsSync(this.configPath)) {
                logger.warn('Arquivo config.json não encontrado, pulando migração');
                return false;
            }

            // Ler configuração atual
            const configContent = fs.readFileSync(this.configPath, 'utf8');
            const config = JSON.parse(configContent);

            // Verificar se precisa migrar
            if (!this.needsMigration(config)) {
                logger.info('Config.json já está no formato atual, pulando migração');
                return false;
            }

            logger.info('Iniciando migração do config.json para novo formato');

            // Criar backup
            if (!this.createBackup(config)) {
                logger.error('Falha ao criar backup, abortando migração');
                return false;
            }

            // Migrar endpoints
            const migratedEndpoints = this.migrateEndpoints(config.scheduler.endpoints);

            // Atualizar configuração
            const migratedConfig = {
                ...config,
                scheduler: {
                    ...config.scheduler,
                    interval: 30000, // Intervalo padrão de 30 segundos
                    endpoints: migratedEndpoints
                }
            };

            // Salvar configuração migrada
            fs.writeFileSync(this.configPath, JSON.stringify(migratedConfig, null, 2), 'utf8');

            logger.info('Migração do config.json concluída com sucesso', {
                endpointsMigrados: migratedEndpoints.length,
                backupCriado: this.backupPath
            });

            return true;

        } catch (error) {
            logger.error('Erro durante migração do config.json', { error: error.message });
            return false;
        }
    }

    // Verificar se existe backup
    hasBackup() {
        return fs.existsSync(this.backupPath);
    }

    // Restaurar backup
    restoreBackup() {
        try {
            if (!this.hasBackup()) {
                logger.warn('Backup não encontrado para restauração');
                return false;
            }

            const backupContent = fs.readFileSync(this.backupPath, 'utf8');
            const backupConfig = JSON.parse(backupContent);

            fs.writeFileSync(this.configPath, JSON.stringify(backupConfig, null, 2), 'utf8');

            logger.info('Backup do config.json restaurado com sucesso');
            return true;

        } catch (error) {
            logger.error('Erro ao restaurar backup do config.json', { error: error.message });
            return false;
        }
    }

    // Obter status da migração
    getMigrationStatus() {
        try {
            if (!fs.existsSync(this.configPath)) {
                return { needsMigration: false, hasBackup: false, reason: 'config_not_found' };
            }

            const configContent = fs.readFileSync(this.configPath, 'utf8');
            const config = JSON.parse(configContent);

            const needsMigration = this.needsMigration(config);
            const hasBackup = this.hasBackup();

            return {
                needsMigration,
                hasBackup,
                currentFormat: needsMigration ? 'old' : 'new',
                backupPath: hasBackup ? this.backupPath : null
            };

        } catch (error) {
            logger.error('Erro ao verificar status da migração', { error: error.message });
            return { needsMigration: false, hasBackup: false, error: error.message };
        }
    }
}

// Instância global do migrator
const configMigrator = new ConfigMigrator();

module.exports = configMigrator;
