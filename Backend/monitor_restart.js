const { DateTime } = require('luxon');
const fs = require('fs');

// Monitor de restart automático
function monitorRestart() {
    console.log('=== MONITOR DE RESTART AUTOMÁTICO ===');
    console.log('Horário atual:', DateTime.local().toFormat('HH:mm:ss'));
    
    // Carregar configurações
    const schedules = JSON.parse(fs.readFileSync('src/data/server/scheduled-restarts.json', 'utf8'));
    
    console.log('\n=== CONFIGURAÇÕES ===');
    console.log('Sistema habilitado:', schedules.enabled);
    console.log('Horários configurados:', schedules.restartTimes.join(', '));
    console.log('Último restart:', schedules.lastRestart);
    console.log('Próximo restart:', schedules.nextRestart);
    console.log('Última notificação:', schedules.lastNotification);
    
    // Verificar próximas notificações
    const now = DateTime.local();
    const notifyTimes = [10, 5, 4, 3, 2, 1];
    
    console.log('\n=== PRÓXIMAS NOTIFICAÇÕES ===');
    for (const min of notifyTimes) {
        const notifyMoment = now.plus({ minutes: min });
        const notifyStr = notifyMoment.toFormat('HH:mm');
        
        if (schedules.restartTimes.includes(notifyStr)) {
            const timeUntilNotification = notifyMoment.diff(now, 'minutes').minutes;
            console.log(`⚠️  Notificação de ${min} minuto(s) às ${notifyStr} (em ${Math.round(timeUntilNotification)} min)`);
        }
    }
    
    // Verificar próximo restart
    const nextRestart = schedules.restartTimes.find(time => {
        const [hours, minutes] = time.split(':').map(Number);
        const restartTime = now.set({ hour: hours, minute: minutes, second: 0, millisecond: 0 });
        return restartTime > now;
    });
    
    if (nextRestart) {
        const [hours, minutes] = nextRestart.split(':').map(Number);
        const restartTime = now.set({ hour: hours, minute: minutes, second: 0, millisecond: 0 });
        const timeUntilRestart = restartTime.diff(now, 'minutes').minutes;
        
        console.log(`\n🔄 PRÓXIMO RESTART: ${nextRestart} (em ${Math.round(timeUntilRestart)} minutos)`);
    }
    
    console.log('\n=== STATUS DOS SERVIÇOS ===');
    
    // Verificar se o backend está rodando
    const { exec } = require('child_process');
    exec('tasklist /FI "IMAGENAME eq node.exe" /FO CSV', (error, stdout) => {
        if (stdout.includes('node.exe')) {
            console.log('✅ Backend Node.js: RODANDO');
        } else {
            console.log('❌ Backend Node.js: PARADO');
        }
        
        // Verificar se o SCUM está rodando
        exec('tasklist /FI "IMAGENAME eq SCUMServer.exe" /FO CSV', (error, stdout) => {
            if (stdout.includes('SCUMServer.exe')) {
                console.log('✅ Servidor SCUM: RODANDO');
            } else {
                console.log('❌ Servidor SCUM: PARADO');
            }
            
            console.log('\n=== MONITORAMENTO ATIVO ===');
            console.log('Pressione Ctrl+C para parar o monitoramento');
            console.log('Aguardando próximas notificações...\n');
        });
    });
}

// Executar monitoramento
monitorRestart();

// Atualizar a cada 30 segundos
setInterval(monitorRestart, 30000); 