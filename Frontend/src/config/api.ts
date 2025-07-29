// Configuração da API do backend
export const API_CONFIG = {
  BASE_URL: (import.meta as any).env?.VITE_BACKEND_URL || '',
  ENDPOINTS: {
    WEBHOOK_PAINELPLAYERS: '/api/webhook/painelplayers',
    WEBHOOK_CHAT_IN_GAME: '/api/webhook/chat_in_game',
    WEBHOOK_ADMINLOG: '/api/webhook/adminlog',
    WEBHOOK_BUNKERS: '/api/webhook/bunkers',
    WEBHOOK_FAMA: '/api/webhook/famepoints',
    WEBHOOK_SERVER_STATUS: '/api/webhook/serverstatus',
    WEBHOOK_FUNNY_STATISTIC: '/api/webhook/funny-statistic',
    // Endpoints para ServerSettingsAdminUsers.ini
    ADMIN_USERS: '/api/admin-users',
    // Endpoint para ServerSettingsAdminUsers.ini (Admin Config)
    SERVER_SETTINGS_ADMIN_USERS: '/api/configserver/ServerSettingsAdminUsers.ini',
  }
};

// Função para construir URLs completas da API
export const buildApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
}; 