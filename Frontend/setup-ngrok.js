import { execSync } from 'child_process';
import fs from 'fs';

console.log('🌐 Configurando ngrok para HTTPS externo...');

try {
  // Verificar se ngrok está instalado
  try {
    execSync('ngrok --version', { stdio: 'ignore' });
    console.log('✅ ngrok já está instalado');
  } catch (error) {
    console.log('📦 Instalando ngrok...');
    execSync('npm install -g ngrok', { stdio: 'inherit' });
  }

  console.log('\n🚀 Configuração completa!');
  console.log('📱 Para usar PWA com HTTPS:');
  console.log('1. Execute: npm run dev');
  console.log('2. Em outro terminal: ngrok http 5173');
  console.log('3. Use a URL HTTPS fornecida pelo ngrok');
  console.log('\n💡 Exemplo: https://abc123.ngrok.io');

} catch (error) {
  console.error('❌ Erro ao configurar ngrok:', error.message);
  console.log('\n🔧 Solução alternativa:');
  console.log('1. Instale ngrok manualmente: npm install -g ngrok');
  console.log('2. Execute: ngrok http 5173');
  console.log('3. Use a URL HTTPS fornecida');
}