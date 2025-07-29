const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const fs = require('fs').promises;
const path = require('path');
const { 
  requireAuth, 
  findUser, 
  createSession, 
  invalidateSession, 
  logAccess, 
  getClientIP,
  JWT_SECRET 
} = require('../src/middleware/auth');

const router = express.Router();

// Rate limiting simples
const loginAttempts = new Map();

const checkRateLimit = (ip) => {
  const now = Date.now();
  const attempts = loginAttempts.get(ip) || [];
  
  // Manter apenas tentativas dos últimos 15 minutos
  const recentAttempts = attempts.filter(time => now - time < 15 * 60 * 1000);
  
  if (recentAttempts.length >= 5) {
    return false; // Bloqueado
  }
  
  recentAttempts.push(now);
  loginAttempts.set(ip, recentAttempts);
  return true; // Permitido
};

// POST /api/auth/login
router.post('/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    const clientIP = getClientIP(req);
    const userAgent = req.headers['user-agent'];
    
    // Validar dados
    if (!username || !password) {
      await logAccess(username, 'login_failed_missing_data', clientIP, userAgent, false);
      return res.status(400).json({
        success: false,
        message: 'Username e password são obrigatórios'
      });
    }
    
    // Verificar rate limiting
    if (!checkRateLimit(clientIP)) {
      await logAccess(username, 'login_blocked_rate_limit', clientIP, userAgent, false);
      return res.status(429).json({
        success: false,
        message: 'Muitas tentativas de login. Tente novamente em 15 minutos.'
      });
    }
    
    // Buscar usuário
    const user = await findUser(username);
    if (!user) {
      await logAccess(username, 'login_failed_user_not_found', clientIP, userAgent, false);
      return res.status(401).json({
        success: false,
        message: 'Usuário ou senha inválidos'
      });
    }
    
    // Verificar senha
    const isValidPassword = await bcrypt.compare(password, user.password);
    if (!isValidPassword) {
      await logAccess(username, 'login_failed_invalid_password', clientIP, userAgent, false);
      return res.status(401).json({
        success: false,
        message: 'Usuário ou senha inválidos'
      });
    }
    
    // Gerar JWT
    const token = jwt.sign(
      {
        id: user.id,
        username: user.username,
        role: user.role
      },
      JWT_SECRET,
      { expiresIn: '24h' }
    );
    
    // Criar sessão
    const session = await createSession(user, token, req);
    if (!session) {
      await logAccess(username, 'login_failed_session_creation', clientIP, userAgent, false);
      return res.status(500).json({
        success: false,
        message: 'Erro ao criar sessão'
      });
    }
    
    // Atualizar último login
    const usersPath = path.join(__dirname, '../src/data/auth/users.json');
    const usersData = await fs.readFile(usersPath, 'utf8');
    const users = JSON.parse(usersData);
    
    const userIndex = users.users.findIndex(u => u.id === user.id);
    if (userIndex !== -1) {
      users.users[userIndex].last_login = new Date().toISOString();
      await fs.writeFile(usersPath, JSON.stringify(users, null, 2));
    }
    
    // Log de sucesso
    await logAccess(username, 'login_success', clientIP, userAgent, true);
    
    res.json({
      success: true,
      message: 'Login realizado com sucesso',
      data: {
        token: token,
        user: {
          id: user.id,
          username: user.username,
          role: user.role
        }
      }
    });
    
  } catch (error) {
    console.error('Erro no login:', error);
    const clientIP = getClientIP(req);
    const userAgent = req.headers['user-agent'];
    await logAccess(req.body?.username, 'login_error', clientIP, userAgent, false);
    
    res.status(500).json({
      success: false,
      message: 'Erro interno do servidor'
    });
  }
});

// POST /api/auth/logout
router.post('/logout', requireAuth, async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const clientIP = getClientIP(req);
    const userAgent = req.headers['user-agent'];
    
    if (token) {
      await invalidateSession(token);
      await logAccess(req.user.username, 'logout_success', clientIP, userAgent, true);
    }
    
    res.json({
      success: true,
      message: 'Logout realizado com sucesso'
    });
    
  } catch (error) {
    console.error('Erro no logout:', error);
    res.status(500).json({
      success: false,
      message: 'Erro interno do servidor'
    });
  }
});

// GET /api/auth/me
router.get('/me', requireAuth, async (req, res) => {
  try {
    res.json({
      success: true,
      data: {
        id: req.user.id,
        username: req.user.username,
        role: req.user.role
      }
    });
  } catch (error) {
    console.error('Erro ao buscar dados do usuário:', error);
    res.status(500).json({
      success: false,
      message: 'Erro interno do servidor'
    });
  }
});

// GET /api/auth/logs (apenas admin)
router.get('/logs', requireAuth, async (req, res) => {
  try {
    // Verificar se é admin
    if (req.user.role !== 'admin') {
      return res.status(403).json({
        success: false,
        message: 'Acesso negado'
      });
    }
    
    const logsPath = path.join(__dirname, '../src/data/auth/access_logs.json');
    const logsData = await fs.readFile(logsPath, 'utf8');
    const logs = JSON.parse(logsData);
    
    // Filtrar logs dos últimos 7 dias por padrão
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    
    const recentLogs = logs.logs.filter(log => 
      new Date(log.timestamp) > sevenDaysAgo
    );
    
    res.json({
      success: true,
      data: {
        logs: recentLogs,
        total: recentLogs.length
      }
    });
    
  } catch (error) {
    console.error('Erro ao buscar logs:', error);
    res.status(500).json({
      success: false,
      message: 'Erro interno do servidor'
    });
  }
});

// POST /api/auth/change-password
router.post('/change-password', requireAuth, async (req, res) => {
  try {
    const { currentPassword, newPassword } = req.body;
    const clientIP = getClientIP(req);
    const userAgent = req.headers['user-agent'];
    
    if (!currentPassword || !newPassword) {
      return res.status(400).json({
        success: false,
        message: 'Senha atual e nova senha são obrigatórias'
      });
    }
    
    // Buscar usuário atual
    const usersPath = path.join(__dirname, '../src/data/auth/users.json');
    const usersData = await fs.readFile(usersPath, 'utf8');
    const users = JSON.parse(usersData);
    
    const user = users.users.find(u => u.id === req.user.id);
    if (!user) {
      return res.status(404).json({
        success: false,
        message: 'Usuário não encontrado'
      });
    }
    
    // Verificar senha atual
    const isValidCurrentPassword = await bcrypt.compare(currentPassword, user.password);
    if (!isValidCurrentPassword) {
      await logAccess(req.user.username, 'change_password_failed', clientIP, userAgent, false);
      return res.status(401).json({
        success: false,
        message: 'Senha atual incorreta'
      });
    }
    
    // Hash da nova senha
    const hashedNewPassword = await bcrypt.hash(newPassword, 10);
    
    // Atualizar senha
    const userIndex = users.users.findIndex(u => u.id === req.user.id);
    users.users[userIndex].password = hashedNewPassword;
    
    await fs.writeFile(usersPath, JSON.stringify(users, null, 2));
    
    await logAccess(req.user.username, 'change_password_success', clientIP, userAgent, true);
    
    res.json({
      success: true,
      message: 'Senha alterada com sucesso'
    });
    
  } catch (error) {
    console.error('Erro ao alterar senha:', error);
    res.status(500).json({
      success: false,
      message: 'Erro interno do servidor'
    });
  }
});

module.exports = router; 