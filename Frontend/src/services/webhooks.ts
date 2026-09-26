import api from './server';

// Interfaces TypeScript para Webhooks

export interface WebhooksResponse {
  success: boolean;
  data: Record<string, string>; // { webhook_name: url }
  timestamp?: number;
  error?: string;
}

export interface WebhookNamesResponse {
  success: boolean;
  data: {
    webhooks: string[];
    total: number;
  };
  timestamp?: number;
  error?: string;
}

export interface UpdateWebhooksRequest {
  webhooks: Record<string, string>;
  create_backup?: boolean;
}

export interface UpdateWebhooksResponse {
  success: boolean;
  message?: string;
  data: {
    updated_webhooks: string[];
  };
  timestamp?: number;
  error?: string;
}

export interface ReplaceWebhooksRequest {
  webhooks: Record<string, string>;
  create_backup?: boolean;
}

export interface ReplaceWebhooksResponse {
  success: boolean;
  message?: string;
  timestamp?: number;
  error?: string;
}

export interface UpdateWebhookRequest {
  url: string;
  create_backup?: boolean;
}

export interface UpdateWebhookResponse {
  success: boolean;
  message?: string;
  data: {
    webhook_name: string;
    url: string;
    created: boolean;
  };
  timestamp?: number;
  error?: string;
}

export interface BackupInfo {
  filename: string;
  path: string;
  created_at: string;
  size: number;
}

export interface ListBackupsResponse {
  success: boolean;
  data: {
    backups: BackupInfo[];
    total: number;
  };
  timestamp?: number;
  error?: string;
}

export interface RestoreBackupRequest {
  backup_file: string;
  create_backup?: boolean;
}

export interface RestoreBackupResponse {
  success: boolean;
  message?: string;
  data: {
    restored_from: string;
  };
  timestamp?: number;
  error?: string;
}

/**
 * Obter todos os webhooks ou um específico
 */
export async function getWebhooks(webhookName?: string): Promise<WebhooksResponse> {
  try {
    const params = webhookName ? { webhook: webhookName } : {};
    const { data } = await api.get<WebhooksResponse>('/webhooks', { params });
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao buscar webhooks',
      data: {},
    };
  }
}

/**
 * Obter um webhook específico pelo nome
 */
export async function getWebhook(webhookName: string): Promise<WebhooksResponse> {
  try {
    const { data } = await api.get<WebhooksResponse>(`/webhooks/${webhookName}`);
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao buscar webhook',
      data: {},
    };
  }
}

/**
 * Listar todos os nomes de webhooks disponíveis
 */
export async function getWebhookNames(): Promise<WebhookNamesResponse> {
  try {
    const { data } = await api.get<WebhookNamesResponse>('/webhooks/names');
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao listar nomes dos webhooks',
      data: {
        webhooks: [],
        total: 0,
      },
    };
  }
}

/**
 * Atualizar múltiplos webhooks (PATCH)
 */
export async function updateWebhooks(
  request: UpdateWebhooksRequest
): Promise<UpdateWebhooksResponse> {
  try {
    const { data } = await api.patch<UpdateWebhooksResponse>('/webhooks', request);
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao atualizar webhooks',
      message: error.message || 'Erro ao atualizar webhooks',
      data: {
        updated_webhooks: [],
      },
    };
  }
}

/**
 * Substituir todos os webhooks (PUT)
 */
export async function replaceWebhooks(
  request: ReplaceWebhooksRequest
): Promise<ReplaceWebhooksResponse> {
  try {
    const { data } = await api.put<ReplaceWebhooksResponse>('/webhooks', request);
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao substituir webhooks',
      message: error.message || 'Erro ao substituir webhooks',
    };
  }
}

/**
 * Atualizar ou criar um webhook específico (PUT)
 */
export async function updateWebhook(
  webhookName: string,
  url: string,
  createBackup: boolean = true
): Promise<UpdateWebhookResponse> {
  try {
    const { data } = await api.put<UpdateWebhookResponse>(
      `/webhooks/${webhookName}`,
      { url, create_backup: createBackup },
      {
        params: { create_backup: createBackup },
      }
    );
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao atualizar webhook',
      message: error.message || 'Erro ao atualizar webhook',
      data: {
        webhook_name: webhookName,
        url,
        created: false,
      },
    };
  }
}

/**
 * Deletar um webhook específico
 */
export async function deleteWebhook(
  webhookName: string,
  createBackup: boolean = true
): Promise<{ success: boolean; message?: string; error?: string; data?: { webhook_name: string } }> {
  try {
    const { data } = await api.delete(`/webhooks/${webhookName}`, {
      params: { create_backup: createBackup },
    });
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao deletar webhook',
      message: error.message || 'Erro ao deletar webhook',
      data: {
        webhook_name: webhookName,
      },
    };
  }
}

/**
 * Listar backups disponíveis
 */
export async function getWebhookBackups(limit: number = 10): Promise<ListBackupsResponse> {
  try {
    const { data } = await api.get<ListBackupsResponse>('/webhooks/backup', {
      params: { limit },
    });
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao listar backups',
      data: {
        backups: [],
        total: 0,
      },
    };
  }
}

/**
 * Testar um webhook específico pelo nome
 */
export interface TestWebhookResponse {
  success: boolean;
  message?: string;
  data: {
    webhook_name?: string;
    webhook_url: string;
    status_code: number;
    error?: string;
  };
  timestamp?: number;
  error?: string;
}

export async function testWebhook(webhookName: string): Promise<TestWebhookResponse> {
  try {
    const { data } = await api.post<TestWebhookResponse>(`/webhooks/${webhookName}/test`);
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao testar webhook',
      message: error.message || 'Erro ao testar webhook',
      data: {
        webhook_url: '',
        status_code: 0,
      },
    };
  }
}

/**
 * Testar um webhook por URL (antes de salvar)
 */
export interface TestWebhookByUrlRequest {
  url: string;
}

export async function testWebhookByUrl(request: TestWebhookByUrlRequest): Promise<TestWebhookResponse> {
  try {
    const { data } = await api.post<TestWebhookResponse>('/webhooks/test', request);
    return data;
  } catch (error: any) {
    console.error('[Webhooks API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao testar webhook',
      message: error.message || 'Erro ao testar webhook',
      data: {
        webhook_url: request.url,
        status_code: 0,
      },
    };
  }
}

