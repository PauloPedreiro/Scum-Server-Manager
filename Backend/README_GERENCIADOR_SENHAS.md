# 🔐 Gerenciador de Senhas - SCUM Server Manager

## 📁 Arquivos Disponíveis

### 1. `alterar_senha_rapido.bat` - **Recomendado para uso diário**
- Interface simples e direta
- Alterar senha de qualquer usuário
- Validação de confirmação de senha
- Mostra usuários disponíveis

### 2. `alterar_senha.bat` - **Gerenciador completo**
- Menu interativo com múltiplas opções
- Listar usuários cadastrados
- Criar novos usuários
- Ativar/desativar usuários
- Alterar senhas

## 🚀 Como Usar

### **Método Rápido (Recomendado):**
1. Clique duplo em `alterar_senha_rapido.bat`
2. Digite o nome do usuário (ex: `admin`)
3. Digite a nova senha
4. Confirme a nova senha
5. Pronto! ✅

### **Método Completo:**
1. Clique duplo em `alterar_senha.bat`
2. Escolha a opção desejada no menu
3. Siga as instruções na tela

## 📋 Funcionalidades

### **alterar_senha_rapido.bat:**
- ✅ Lista usuários disponíveis
- ✅ Validação de senha
- ✅ Confirmação de senha
- ✅ Feedback visual
- ✅ Interface limpa

### **alterar_senha.bat:**
- ✅ Menu interativo completo
- ✅ Gerenciar usuários (CRUD)
- ✅ Visualizar status dos usuários
- ✅ Ativar/desativar usuários
- ✅ Criar novos usuários
- ✅ Listar detalhes completos

## 🔧 Requisitos

- Node.js instalado
- Dependências do projeto instaladas (`npm install`)
- Arquivo `src/data/auth/users.json` existente

## ⚠️ Importante

- **Nunca** edite o arquivo `users.json` manualmente
- **Sempre** use os arquivos .bat para alterações
- As senhas são automaticamente criptografadas
- Backup automático antes de alterações

## 🎯 Exemplo de Uso

```
Usuários disponíveis:
  - admin (Ativo)

Digite o nome do usuário: admin
Digite a nova senha: minhasenha123
Confirme a nova senha: minhasenha123

🔧 Gerando nova senha para: admin

✅ Senha alterada com sucesso!
📝 Nova senha: minhasenha123
```

## 🛡️ Segurança

- Senhas sempre criptografadas com bcrypt
- Validação de entrada do usuário
- Confirmação obrigatória de senha
- Logs de alterações automáticos
- Verificação de usuário existente

## 📞 Suporte

Se houver problemas:
1. Verifique se o Node.js está instalado
2. Execute `npm install` na pasta do projeto
3. Verifique se o arquivo `users.json` existe
4. Teste com o usuário `admin` primeiro

---

**Desenvolvido para SCUM Server Manager 2.0** 🎮 