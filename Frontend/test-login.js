// Script para testar o login
console.log('🧪 Testando Login...\n');

// Simular login
const testLogin = async () => {
  try {
    console.log('📝 Fazendo login...');
    
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username: 'admin', password: 'admin123' })
    });

    const data = await response.json();
    console.log('✅ Resposta do login:', data);

    if (data.success) {
      console.log('🎉 Login bem-sucedido!');
      console.log('Token:', data.data.token);
      console.log('User:', data.data.user);
      
      // Testar verificação do token
      console.log('\n🔍 Testando verificação do token...');
      const verifyResponse = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${data.data.token}`
        }
      });
      
      const verifyData = await verifyResponse.json();
      console.log('✅ Verificação do token:', verifyData);
      
    } else {
      console.log('❌ Login falhou:', data.message);
    }
    
  } catch (error) {
    console.error('❌ Erro no teste:', error);
  }
};

// Executar teste
testLogin(); 