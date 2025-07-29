const jwt = require('jsonwebtoken');
const fs = require('fs').promises;
const path = require('path');
const bcrypt = require('bcrypt');

// Configurações
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';
const AUTH_DATA_PATH = path.join(__dirname, '../data/auth');

// Função para capturar IP real
const getClientIP = (req) => {
  return req.headers['x-forwarded-for'] || 
         req.headers['x-real-ip'] || 
         req.connection.remoteAddress || 
         req.socket.remoteAddress || 
         req.ip || 
         'unknown';
};

// Função para log de acesso
const logAccess = async (username, action, ip, userAgent, success = true) => {
  try {
    const logsPath = path.join(AUTH_DATA_PATH, 'access_logs.json');
    const logsData = await fs.readFile(logsPath, 'utf8');
    const logs = JSON.parse(logsData);
    
    const logEntry = {
      id: Date.now().toString(),
      username: username || 'unknown',
      action: action,
      ip: ip,
      user_agent: userAgent || 'unknown',
      timestamp: new Date().toISOString(),
      success: success
    };
    
    logs.logs.push(logEntry);
    
    // Manter apenas últimos 1000 logs
    if (logs.logs.length > 1000) {
      logs.logs = logs.logs.slice(-1000);
    }
    
    await fs.writeFile(logsPath, JSON.stringify(logs, null, 2));
  } catch (error) {
    console.error('Erro ao salvar log de acesso:', error);
  }
};

// Middleware para verificar autenticação
const requireAuth = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const clientIP = getClientIP(req);
    const userAgent = req.headers['user-agent'];
    
    if (!token) {
      await logAccess(null, 'auth_failed', clientIP, userAgent, false);
      return res.status(401).json({ 
        success: false, 
        message: 'Token não fornecido' 
      });
    }
    
    // Verificar JWT
    const decoded = jwt.verify(token, JWT_SECRET);
    
    // Verificar se sessão existe
    const sessionsPath = path.join(AUTH_DATA_PATH, 'sessions.json');
    const sessionsData = await fs.readFile(sessionsPath, 'utf8');
    const sessions = JSON.parse(sessionsData);
    
    const session = sessions.sessions.find(s => s.token === token);
    if (!session) {
      await logAccess(decoded.username, 'session_invalid', clientIP, userAgent, false);
      return res.status(401).json({ 
        success: false, 
        message: 'Sessão inválida' 
      });
    }
    
    // Verificar se sessão expirou
    if (new Date() > new Date(session.expires_at)) {
      // Remover sessão expirada
      sessions.sessions = sessions.sessions.filter(s => s.token !== token);
      await fs.writeFile(sessionsPath, JSON.stringify(sessions, null, 2));
      
      await logAccess(decoded.username, 'session_expired', clientIP, userAgent, false);
      return res.status(401).json({ 
        success: false, 
        message: 'Sessão expirada' 
      });
    }
    
    // Adicionar dados do usuário ao request
    req.user = {
      id: decoded.id,
      username: decoded.username,
      role: decoded.role
    };
    
    await logAccess(decoded.username, 'auth_success', clientIP, userAgent, true);
    next();
    
  } catch (error) {
    const clientIP = getClientIP(req);
    const userAgent = req.headers['user-agent'];
    
    await logAccess(null, 'auth_error', clientIP, userAgent, false);
    
    return res.status(401).json({ 
      success: false, 
      message: 'Token inválido' 
    });
  }
};

// Função para verificar se usuário existe
const findUser = async (username) => {
  try {
    const usersPath = path.join(AUTH_DATA_PATH, 'users.json');
    const usersData = await fs.readFile(usersPath, 'utf8');
    const users = JSON.parse(usersData);
    
    return users.users.find(user => 
      user.username === username && user.active === true
    );
  } catch (error) {
    console.error('Erro ao buscar usuário:', error);
    return null;
  }
};

// Função para criar sessão
const createSession = async (user, token, req) => {
  try {
    const sessionsPath = path.join(AUTH_DATA_PATH, 'sessions.json');
    const sessionsData = await fs.readFile(sessionsPath, 'utf8');
    const sessions = JSON.parse(sessionsData);
    
    const expiresAt = new Date();
    expiresAt.setHours(expiresAt.getHours() + 24); // 24 horas
    
    const session = {
      token: token,
      user_id: user.id,
      username: user.username,
      created_at: new Date().toISOString(),
      expires_at: expiresAt.toISOString(),
      ip: req ? getClientIP(req) : 'unknown'
    };
    
    sessions.sessions.push(session);
    await fs.writeFile(sessionsPath, JSON.stringify(sessions, null, 2));
    
    return session;
  } catch (error) {
    console.error('Erro ao criar sessão:', error);
    return null;
  }
};

// Função para invalidar sessão
const invalidateSession = async (token) => {
  try {
    const sessionsPath = path.join(AUTH_DATA_PATH, 'sessions.json');
    const sessionsData = await fs.readFile(sessionsPath, 'utf8');
    const sessions = JSON.parse(sessionsData);
    
    sessions.sessions = sessions.sessions.filter(s => s.token !== token);
    await fs.writeFile(sessionsPath, JSON.stringify(sessions, null, 2));
    
    return true;
  } catch (error) {
    console.error('Erro ao invalidar sessão:', error);
    return false;
  }
};

module.exports = {
  requireAuth,
  findUser,
  createSession,
  invalidateSession,
  logAccess,
  getClientIP,
  JWT_SECRET
}; 