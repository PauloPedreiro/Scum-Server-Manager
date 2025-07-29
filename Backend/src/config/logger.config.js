module.exports = {
    // Nível de log padrão (debug, info, warn, error)
    level: process.env.LOG_LEVEL || 'info',
    
    // Habilitar cores no console
    colors: true,
    
    // Configurações por módulo
    modules: {
        server: 'info',
        bot: 'info',
        webhook: 'info',
        vehicles: 'info',
        players: 'info',
        bunkers: 'info',
        famepoints: 'info',
        adminlog: 'info'
    },
    
    // Configurações de arquivo
    file: {
        enabled: true,
        maxSize: 10 * 1024 * 1024, // 10MB
        maxFiles: 5,
        directory: 'src/data/logs'
    }
}; 