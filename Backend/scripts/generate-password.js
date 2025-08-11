const bcrypt = require('bcrypt');
const fs = require('fs').promises;
const path = require('path');

const generatePasswordHash = async (password) => {
  try {
    const saltRounds = 10;
    const hash = await bcrypt.hash(password, saltRounds);
    return hash;
  } catch (error) {
    console.error('Erro ao gerar hash:', error);
    return null;
  }
};

const updateUserPassword = async (username, newPassword) => {
  try {
    const usersPath = path.join(__dirname, '../src/data/auth/users.json');
    const usersData = await fs.readFile(usersPath, 'utf8');
    const users = JSON.parse(usersData);
    
    const hash = await generatePasswordHash(newPassword);
    if (!hash) {
      console.error('Erro ao gerar hash da senha');
      return false;
    }
    
    const userIndex = users.users.findIndex(user => user.username === username);
    if (userIndex === -1) {
      console.error(`Usuário '${username}' não encontrado`);
      return false;
    }
    
    users.users[userIndex].password = hash;
    users.users[userIndex].last_login = null;
    
    await fs.writeFile(usersPath, JSON.stringify(users, null, 2));
    
    console.log(`✅ Senha do usuário '${username}' atualizada com sucesso!`);
    console.log(`🔐 Hash gerado: ${hash}`);
    return true;
    
  } catch (error) {
    console.error('Erro ao atualizar senha:', error);
    return false;
  }
};

// Executar se chamado diretamente
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length !== 2) {
    console.log('Uso: node scripts/generate-password.js <username> <password>');
    console.log('Exemplo: node scripts/generate-password.js admin minhasenha123');
    process.exit(1);
  }
  
  const [username, password] = args;
  
  console.log(`🔧 Gerando hash para usuário: ${username}`);
  console.log(`🔑 Senha fornecida: ${password}`);
  console.log('');
  
  updateUserPassword(username, password)
    .then(success => {
      if (success) {
        console.log('');
        console.log('🎉 Senha configurada com sucesso!');
        console.log('💡 Agora você pode fazer login no sistema.');
      } else {
        console.log('');
        console.log('❌ Erro ao configurar senha.');
        process.exit(1);
      }
    })
    .catch(error => {
      console.error('Erro:', error);
      process.exit(1);
    });
}

module.exports = {
  generatePasswordHash,
  updateUserPassword
}; 