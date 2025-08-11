const VehicleControl = require('./vehicle_control');

class VehicleControlIntegration {
    constructor() {
        this.vehicleControl = new VehicleControl();
        this.isRunning = false;
        this.interval = null;
    }

    start() {
        if (this.isRunning) {
            console.log('Controle de veículos já está rodando');
            return;
        }

        console.log('Iniciando integração do controle de veículos...');
        this.isRunning = true;

        // Executar uma vez imediatamente
        this.vehicleControl.run();

        // Configurar execução periódica (a cada 5 minutos)
        this.interval = setInterval(() => {
            if (this.isRunning) {
                console.log('Executando verificação periódica de veículos...');
                this.vehicleControl.run();
            }
        }, 5 * 60 * 1000); // 5 minutos

        console.log('Integração do controle de veículos iniciada');
    }

    stop() {
        if (!this.isRunning) {
            console.log('Controle de veículos não está rodando');
            return;
        }

        console.log('Parando integração do controle de veículos...');
        this.isRunning = false;

        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }

        console.log('Integração do controle de veículos parada');
    }

    // Método para forçar atualização
    forceUpdate() {
        console.log('Forçando atualização do controle de veículos...');
        this.vehicleControl.run();
    }

    // Método para obter status atual
    getStatus() {
        return {
            isRunning: this.isRunning,
            playerCount: Object.keys(this.vehicleControl.playerVehicles).length,
            lastUpdate: this.vehicleControl.playerVehicles ? 
                Object.values(this.vehicleControl.playerVehicles).map(p => p.lastUpdated).sort().pop() : null
        };
    }
}

module.exports = VehicleControlIntegration; 