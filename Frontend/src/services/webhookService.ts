import { buildApiUrl, API_CONFIG } from '../config/api';

const API_BASE_URL = API_CONFIG.BASE_URL;

export interface WebhookResponse {
  success: boolean;
  message: string;
  url?: string | null;
}

export const WebhookService = {
  async savePainelPlayersWebhook(url: string): Promise<WebhookResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_PAINELPLAYERS), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Erro ao salvar webhook painel players:', error);
      throw new Error('Erro ao conectar com o servidor. Verifique se o backend está rodando.');
    }
  },

  async getPainelPlayersWebhook(): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo GET para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_PAINELPLAYERS));
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_PAINELPLAYERS));
      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao consultar webhook painel players:', error);
      throw new Error('Erro ao consultar webhook. Verifique se o backend está rodando.');
    }
  },

  async testWebhook(url: string): Promise<WebhookResponse> {
    try {
      // Simula um teste de webhook enviando uma mensagem de teste
      const testMessage = {
        content: '🧪 **Teste de Webhook**\n\nEste é um teste de conectividade do webhook do SCUM Server Manager.\n\n✅ Webhook funcionando corretamente!',
        embeds: [
          {
            title: 'Teste de Conectividade',
            description: 'Webhook configurado e funcionando',
            color: 0x00ff00,
            timestamp: new Date().toISOString(),
            footer: {
              text: 'SCUM Server Manager - Teste'
            }
          }
        ]
      };

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testMessage),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return {
        success: true,
        message: 'Teste realizado com sucesso! Mensagem enviada para o Discord.',
        url
      };
    } catch (error) {
      console.error('Erro ao testar webhook:', error);
      throw new Error('Erro ao testar webhook. Verifique se a URL está correta e o Discord está acessível.');
    }
  },

  async saveChatInGameWebhook(url: string): Promise<WebhookResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_CHAT_IN_GAME), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Erro ao salvar webhook Chat in Game:', error);
      throw new Error('Erro ao conectar com o servidor. Verifique se o backend está rodando.');
    }
  },

  async getChatInGameWebhook(): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo GET para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_CHAT_IN_GAME));
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_CHAT_IN_GAME));
      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao consultar webhook Chat in Game:', error);
      throw new Error('Erro ao consultar webhook. Verifique se o backend está rodando.');
    }
  },

  async getChatInGameMessages() {
    try {
      const response = await fetch(buildApiUrl('/api/chat_in_game'));
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Erro ao buscar mensagens do chat in game:', error);
      throw new Error('Erro ao buscar mensagens do chat in game.');
    }
  },

  saveLogVeiculosWebhook: async (url: string) => {
    const response = await fetch(buildApiUrl('/api/webhook/LogVeiculos'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    return await response.json();
  },

  getLogVeiculosWebhook: async () => {
    const response = await fetch(buildApiUrl('/api/webhook/LogVeiculos'));
    return await response.json();
  },

  async saveAdminLogWebhook(url: string): Promise<WebhookResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_ADMINLOG), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Erro ao salvar webhook Admin Log:', error);
      throw new Error('Erro ao conectar com o servidor. Verifique se o backend está rodando.');
    }
  },

  async getAdminLogWebhook(): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo GET para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_ADMINLOG));
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_ADMINLOG));
      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao consultar webhook Admin Log:', error);
      throw new Error('Erro ao consultar webhook. Verifique se o backend está rodando.');
    }
  },

  async saveBunkersWebhook(url: string): Promise<WebhookResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_BUNKERS), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Erro ao salvar webhook Bunkers:', error);
      throw new Error('Erro ao conectar com o servidor. Verifique se o backend está rodando.');
    }
  },

  async getBunkersWebhook(): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo GET para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_BUNKERS));
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_BUNKERS));
      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao consultar webhook Bunkers:', error);
      throw new Error('Erro ao consultar webhook. Verifique se o backend está rodando.');
    }
  },

  async saveFamaWebhook(url: string): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo POST para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_FAMA));
      console.log('📡 Body:', { url });
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_FAMA), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao salvar webhook Fama:', error);
      throw new Error('Erro ao conectar com o servidor. Verifique se o backend está rodando.');
    }
  },

  async getFamaWebhook(): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo GET para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_FAMA));
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_FAMA));
      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao consultar webhook Fama:', error);
      throw new Error('Erro ao consultar webhook. Verifique se o backend está rodando.');
    }
  },

  async saveServerStatusWebhook(url: string): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo POST para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_SERVER_STATUS));
      console.log('📡 Body:', { url });
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_SERVER_STATUS), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao salvar webhook Server Status:', error);
      throw new Error('Erro ao conectar com o servidor. Verifique se o backend está rodando.');
    }
  },

  async getServerStatusWebhook(): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo GET para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_SERVER_STATUS));
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_SERVER_STATUS));
      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao consultar webhook Server Status:', error);
      throw new Error('Erro ao consultar webhook. Verifique se o backend está rodando.');
    }
  },

  async saveFunnyStatisticWebhook(url: string): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo POST para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_FUNNY_STATISTIC));
      console.log('📡 Body:', { url });
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_FUNNY_STATISTIC), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao salvar webhook Funny Statistic:', error);
      throw new Error('Erro ao conectar com o servidor. Verifique se o backend está rodando.');
    }
  },

  async getFunnyStatisticWebhook(): Promise<WebhookResponse> {
    try {
      console.log('🌐 Fazendo GET para:', buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_FUNNY_STATISTIC));
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WEBHOOK_FUNNY_STATISTIC));
      console.log('📡 Response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('📡 Response data:', data);
      return data;
    } catch (error) {
      console.error('Erro ao consultar webhook Funny Statistic:', error);
      throw new Error('Erro ao consultar webhook. Verifique se o backend está rodando.');
    }
  },
}; 