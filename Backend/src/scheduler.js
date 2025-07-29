const fs = require('fs');
const path = require('path');
const axios = require('axios');
const { DateTime } = require('luxon');

// Importar configurações e logger
const config = require('./data/server/config.json');
const logger = require('./logger');

class Scheduler {
    constructor() {
        this.isRunning = false;
        this.interval = null;
        this.lastExecution = null;
        this.executionSource = null;
        this.stats = {
            totalExecutions: 0,
            successfulExecutions: 0,
            failedExecutions: 0,
            lastError: null,
            lastSuccess: null
        };
        this.config = config.scheduler;
        this.endpoints = this.config.endpoints;
        this.stateFile = path.join(__dirname, 'data', 'scheduler_state.json');
        this.loadState();
    }

    // Carregar estado salvo
    loadState() {
        try {
            if (fs.existsSync(this.stateFile)) {
                const state = JSON.parse(fs.readFileSync(this.stateFile, 'utf8'));
                this.lastExecution = state.lastExecution;
                this.executionSource = state.executionSource;
                this.stats = { ...this.stats, ...state.stats };
                logger.info('Estado do scheduler carregado', { state });
            }
        } catch (error) {
            logger.error('Erro ao carregar estado do scheduler', { error: error.message });
        }
    }

    // Salvar estado
    saveState() {
        try {
            const state = {
                lastExecution: this.lastExecution,
                executionSource: this.executionSource,
                stats: this.stats,
                timestamp: new Date().toISOString()
            };
            fs.writeFileSync(this.stateFile, JSON.stringify(state, null, 2), 'utf8');
        } catch (error) {
            logger.error('Erro ao salvar estado do scheduler', { error: error.message });
        }
    }

    // Verificar se pode executar (evitar conflitos)
    canExecute(source) {
        if (!this.lastExecution) return true;
        
        const now = Date.now();
        const timeSinceLastExecution = now - this.lastExecution;
        const minInterval = this.config.interval * 0.8; // 80% do intervalo
        
        if (timeSinceLastExecution < minInterval) {
            logger.info(`Execução bloqueada: ${Math.round(timeSinceLastExecution/1000)}s desde última execução`, {
                source,
                timeSinceLastExecution,
                minInterval
            });
            return false;
        }
        
        return true;
    }

    // Executar um endpoint específico
    async executeEndpoint(endpoint) {
        try {
            const url = `http://127.0.0.1:3000${endpoint}`;
            const response = await axios.get(url, {
                timeout: this.config.timeout
            });
            
            logger.info(`Endpoint executado com sucesso: ${endpoint}`, {
                status: response.status,
                endpoint
            });
            
            return { success: true, status: response.status, endpoint };
        } catch (error) {
            logger.error(`Erro ao executar endpoint: ${endpoint}`, {
                error: error.message,
                endpoint
            });
            
            return { 
                success: false, 
                error: error.message, 
                endpoint 
            };
        }
    }

    // Executar sequência de endpoints
    async executeSequence(source = 'backend') {
        if (!this.canExecute(source)) {
            return { success: false, reason: 'execution_blocked' };
        }

        const startTime = Date.now();
        this.lastExecution = startTime;
        this.executionSource = source;
        this.stats.totalExecutions++;

        logger.info('Iniciando execução do scheduler', {
            source,
            endpoints: this.endpoints,
            timestamp: new Date().toISOString()
        });

        const results = [];
        let successCount = 0;
        let failureCount = 0;

        // Executar endpoints sequencialmente
        for (const endpoint of this.endpoints) {
            const result = await this.executeEndpoint(endpoint);
            results.push(result);
            
            if (result.success) {
                successCount++;
            } else {
                failureCount++;
            }

            // Pequena pausa entre endpoints
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        const executionTime = Date.now() - startTime;
        const overallSuccess = successCount > 0;

        if (overallSuccess) {
            this.stats.successfulExecutions++;
            this.stats.lastSuccess = new Date().toISOString();
        } else {
            this.stats.failedExecutions++;
            this.stats.lastError = new Date().toISOString();
        }

        this.saveState();

        logger.info('Execução do scheduler concluída', {
            source,
            executionTime,
            successCount,
            failureCount,
            overallSuccess,
            results: results.map(r => ({ endpoint: r.endpoint, success: r.success }))
        });

        return {
            success: overallSuccess,
            executionTime,
            successCount,
            failureCount,
            results,
            source
        };
    }

    // Iniciar scheduler
    start() {
        if (this.isRunning) {
            logger.warn('Scheduler já está rodando');
            return false;
        }

        if (!this.config.enabled) {
            logger.info('Scheduler desabilitado na configuração');
            return false;
        }

        this.isRunning = true;
        this.interval = setInterval(async () => {
            await this.executeSequence('backend');
        }, this.config.interval);

        logger.info('Scheduler iniciado', {
            interval: this.config.interval,
            endpoints: this.endpoints
        });

        return true;
    }

    // Parar scheduler
    stop() {
        if (!this.isRunning) {
            logger.warn('Scheduler não está rodando');
            return false;
        }

        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }

        this.isRunning = false;
        logger.info('Scheduler parado');
        return true;
    }

    // Execução manual
    async executeManual() {
        return await this.executeSequence('manual');
    }

    // Obter status
    getStatus() {
        const now = Date.now();
        const timeSinceLastExecution = this.lastExecution ? now - this.lastExecution : null;
        
        return {
            isRunning: this.isRunning,
            enabled: this.config.enabled,
            interval: this.config.interval,
            lastExecution: this.lastExecution,
            executionSource: this.executionSource,
            timeSinceLastExecution,
            stats: this.stats,
            endpoints: this.endpoints,
            nextExecution: this.isRunning ? this.lastExecution + this.config.interval : null
        };
    }

    // Verificar se frontend pode executar
    canFrontendExecute() {
        if (!this.config.frontend_fallback) return false;
        if (!this.isRunning) return true;
        return !this.canExecute('frontend');
    }
}

// Instância global do scheduler
const scheduler = new Scheduler();

module.exports = scheduler; 