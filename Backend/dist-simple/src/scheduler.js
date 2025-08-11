const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const url = require('url');
const { DateTime } = require('luxon');

// Função para fazer requisições HTTP (substitui axios)
function makeRequest(options) {
    return new Promise((resolve, reject) => {
        const parsedUrl = url.parse(options.url);
        const requestOptions = {
            hostname: parsedUrl.hostname,
            port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
            path: parsedUrl.path,
            method: options.method || 'GET',
            headers: options.headers || {}
        };

        const client = parsedUrl.protocol === 'https:' ? https : http;
        const req = client.request(requestOptions, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                resolve({
                    status: res.statusCode,
                    data: data,
                    headers: res.headers
                });
            });
        });

        req.on('error', (err) => {
            reject(err);
        });

        if (options.data) {
            req.write(JSON.stringify(options.data));
        }

        req.end();
    });
}

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
        
        // Processar endpoints para suportar configuração antiga e nova
        this.endpoints = this.processEndpoints();
        
        // Controle individual de tempo para cada endpoint
        this.endpointTimers = new Map();
        this.endpointLastExecution = new Map();
        
        this.stateFile = path.join(__dirname, 'data', 'scheduler_state.json');
        this.loadState();
    }

    // Processar endpoints para suportar configuração antiga e nova
    processEndpoints() {
        const endpoints = this.config.endpoints || [];
        
        return endpoints.map(endpoint => {
            // Se é string (configuração antiga), converter para objeto
            if (typeof endpoint === 'string') {
                return {
                    path: endpoint,
                    interval: this.config.default_interval || this.config.interval || 30000,
                    enabled: true
                };
            }
            
            // Se já é objeto (configuração nova), usar como está
            return {
                path: endpoint.path,
                interval: endpoint.interval || this.config.default_interval || 30000,
                enabled: endpoint.enabled !== false
            };
        });
    }

    // Verificar se um endpoint específico pode executar
    canExecuteEndpoint(endpointPath) {
        const endpoint = this.endpoints.find(ep => ep.path === endpointPath);
        if (!endpoint || !endpoint.enabled) return false;
        
        const lastExecution = this.endpointLastExecution.get(endpointPath);
        if (!lastExecution) return true;
        
        const now = Date.now();
        const timeSinceLastExecution = now - lastExecution;
        const minInterval = endpoint.interval * 0.8; // 80% do intervalo
        
        return timeSinceLastExecution >= minInterval;
    }

    // Marcar execução de um endpoint específico
    markEndpointExecution(endpointPath) {
        this.endpointLastExecution.set(endpointPath, Date.now());
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

    // Executar um endpoint específico
    async executeEndpoint(endpoint) {
        try {
            const url = `http://127.0.0.1:3000${endpoint.path}`;
            const response = await makeRequest({ url });
            
            logger.info(`Endpoint executado com sucesso: ${endpoint.path}`, {
                status: response.status,
                endpoint: endpoint.path
            });
            
            return { success: true, status: response.status, endpoint };
        } catch (error) {
            logger.error(`Erro ao executar endpoint: ${endpoint.path}`, {
                error: error.message,
                endpoint: endpoint.path
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
        if (!this.config.enabled) {
            logger.info('Scheduler desabilitado na configuração');
            return { success: false, reason: 'scheduler_disabled' };
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
            if (!this.canExecuteEndpoint(endpoint.path)) {
                logger.info(`Execução bloqueada para endpoint: ${endpoint.path}`, {
                    endpoint: endpoint.path,
                    timeSinceLastExecution: Date.now() - this.endpointLastExecution.get(endpoint.path)
                });
                results.push({ success: false, error: 'execution_blocked', endpoint });
                failureCount++;
                continue;
            }

            const result = await this.executeEndpoint(endpoint);
            results.push(result);
            
            if (result.success) {
                successCount++;
            } else {
                failureCount++;
            }

            this.markEndpointExecution(endpoint.path); // Marcar execução

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
        const defaultInterval = this.config.default_interval || this.config.interval || 30000;
        
        this.interval = setInterval(async () => {
            await this.executeSequence('backend');
        }, defaultInterval);

        logger.info('Scheduler iniciado', {
            defaultInterval,
            endpoints: this.endpoints.map(ep => ({
                path: ep.path,
                interval: ep.interval,
                enabled: ep.enabled
            }))
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
        const defaultInterval = this.config.default_interval || this.config.interval || 30000;
        
        // Status individual de cada endpoint
        const endpointStatus = this.endpoints.map(endpoint => {
            const lastExec = this.endpointLastExecution.get(endpoint.path);
            const timeSinceLast = lastExec ? now - lastExec : null;
            const canExecute = this.canExecuteEndpoint(endpoint.path);
            
            return {
                path: endpoint.path,
                interval: endpoint.interval,
                enabled: endpoint.enabled,
                lastExecution: lastExec,
                timeSinceLastExecution: timeSinceLast,
                canExecute,
                nextExecution: lastExec ? lastExec + endpoint.interval : null
            };
        });
        
        return {
            isRunning: this.isRunning,
            enabled: this.config.enabled,
            defaultInterval,
            lastExecution: this.lastExecution,
            executionSource: this.executionSource,
            timeSinceLastExecution,
            stats: this.stats,
            endpoints: endpointStatus,
            nextExecution: this.isRunning ? this.lastExecution + defaultInterval : null
        };
    }

    // Verificar se frontend pode executar
    canFrontendExecute() {
        if (!this.config.frontend_fallback) return false;
        if (!this.isRunning) return true;
        return !this.canExecuteEndpoint('frontend'); // Usar canExecuteEndpoint
    }
}

// Instância global do scheduler
const scheduler = new Scheduler();

module.exports = scheduler; 