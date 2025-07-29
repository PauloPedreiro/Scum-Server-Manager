// Script para limpar localStorage e testar autenticação
console.log('=== LIMPEZA DO LOCALSTORAGE ===');

// Verificar localStorage atual
console.log('localStorage atual:');
console.log('scum_auth_token:', localStorage.getItem('scum_auth_token'));
console.log('scum_user_data:', localStorage.getItem('scum_user_data'));
console.log('token:', localStorage.getItem('token'));

// Limpar dados de autenticação
localStorage.removeItem('scum_auth_token');
localStorage.removeItem('scum_user_data');
localStorage.removeItem('token');

console.log('\n=== APÓS LIMPEZA ===');
console.log('scum_auth_token:', localStorage.getItem('scum_auth_token'));
console.log('scum_user_data:', localStorage.getItem('scum_user_data'));
console.log('token:', localStorage.getItem('token'));

console.log('\n✅ localStorage limpo! Recarregue a página para testar o login.'); 