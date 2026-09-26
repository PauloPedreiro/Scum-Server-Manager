import api from './server';

// Interfaces TypeScript para config.json

export interface ConfigResponse {
  success: boolean;
  data: Record<string, any>;
  timestamp?: number;
  error?: string;
}

export interface SectionsResponse {
  success: boolean;
  data: {
    sections: string[];
    total: number;
  };
  timestamp?: number;
  error?: string;
}

export interface UpdateConfigRequest {
  sections: Record<string, any>;
  create_backup?: boolean;
}

export interface UpdateConfigResponse {
  success: boolean;
  message?: string;
  data: {
    updated_sections: string[];
    requires_restart: string[];
  };
  timestamp?: number;
  error?: string;
}

export interface ReplaceConfigRequest {
  config: Record<string, any>;
  create_backup?: boolean;
}

export interface ReplaceConfigResponse {
  success: boolean;
  message?: string;
  data: {
    requires_restart: boolean;
  };
  timestamp?: number;
  error?: string;
}

export interface UpdateSectionResponse {
  success: boolean;
  message?: string;
  data: {
    section: string;
    updated_fields: string[];
    requires_restart: string[];
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

export interface BackupsResponse {
  success: boolean;
  data: {
    backups: BackupInfo[];
    total: number;
  };
  timestamp?: number;
  error?: string;
}

export interface RestoreConfigRequest {
  backup_file: string;
  create_backup?: boolean;
}

export interface RestoreConfigResponse {
  success: boolean;
  message?: string;
  data: {
    restored_from: string;
    requires_restart: boolean;
  };
  timestamp?: number;
  error?: string;
}

/**
 * Obter configuração completa ou uma seção específica
 */
export async function getConfig(section?: string): Promise<ConfigResponse> {
  try {
    const params = section ? { section } : {};
    const { data } = await api.get<ConfigResponse>('/config', { params });
    return data;
  } catch (error: any) {
    console.error('[Config API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao buscar configuração',
      data: {},
    };
  }
}

/**
 * Listar todas as seções disponíveis
 */
export async function getConfigSections(): Promise<SectionsResponse> {
  try {
    const { data } = await api.get<SectionsResponse>('/config/sections');
    return data;
  } catch (error: any) {
    console.error('[Config API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao listar seções',
      data: {
        sections: [],
        total: 0,
      },
    };
  }
}

/**
 * Atualizar uma ou mais seções (merge profundo)
 */
export async function updateConfig(
  request: UpdateConfigRequest
): Promise<UpdateConfigResponse> {
  try {
    const { data } = await api.patch<UpdateConfigResponse>('/config', request);
    return data;
  } catch (error: any) {
    console.error('[Config API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao atualizar configuração',
      message: error.message || 'Erro ao atualizar configuração',
      data: {
        updated_sections: [],
        requires_restart: [],
      },
    };
  }
}

/**
 * Substituir configuração completa
 */
export async function replaceConfig(
  request: ReplaceConfigRequest
): Promise<ReplaceConfigResponse> {
  try {
    const { data } = await api.put<ReplaceConfigResponse>('/config', request);
    return data;
  } catch (error: any) {
    console.error('[Config API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao substituir configuração',
      message: error.message || 'Erro ao substituir configuração',
      data: {
        requires_restart: false,
      },
    };
  }
}

/**
 * Atualizar seção específica (PUT)
 */
export async function updateConfigSection(
  section: string,
  sectionData: Record<string, any>,
  createBackup: boolean = true
): Promise<UpdateSectionResponse> {
  try {
    const { data } = await api.put<UpdateSectionResponse>(
      `/config/${section}`,
      sectionData,
      {
        params: { create_backup: createBackup },
      }
    );
    return data;
  } catch (error: any) {
    console.error('[Config API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao atualizar seção',
      message: error.message || 'Erro ao atualizar seção',
      data: {
        section,
        updated_fields: [],
        requires_restart: [],
      },
    };
  }
}

/**
 * Listar backups disponíveis
 */
export async function getConfigBackups(limit: number = 10): Promise<BackupsResponse> {
  try {
    const { data } = await api.get<BackupsResponse>('/config/backup', {
      params: { limit },
    });
    return data;
  } catch (error: any) {
    console.error('[Config API Error]', error);
    
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
 * Restaurar configuração de um backup
 */
export async function restoreConfig(
  request: RestoreConfigRequest
): Promise<RestoreConfigResponse> {
  try {
    const { data } = await api.post<RestoreConfigResponse>('/config/restore', request);
    return data;
  } catch (error: any) {
    console.error('[Config API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao restaurar backup',
      message: error.message || 'Erro ao restaurar backup',
      data: {
        restored_from: request.backup_file,
        requires_restart: false,
      },
    };
  }
}

export interface KillFeedPhrasesResponse {
  success: boolean;
  data: string[];
  error?: string;
  message?: string;
}

export interface UpdateKillFeedPhrasesResponse {
  success: boolean;
  message?: string;
  error?: string;
}

/**
 * Obter lista de frases do Kill Feed
 */
export async function getKillFeedPhrases(): Promise<KillFeedPhrasesResponse> {
  try {
    const { data } = await api.get<KillFeedPhrasesResponse>('/config/kill-feed-phrases');
    return data;
  } catch (error: any) {
    console.error('[Config API Error]', error);
    if (error.response?.data) {
      return error.response.data;
    }
    return {
      success: false,
      error: error.message || 'Erro ao buscar frases do kill feed',
      data: [],
    };
  }
}

/**
 * Atualizar lista de frases do Kill Feed
 */
export async function updateKillFeedPhrases(
  phrases: string[]
): Promise<UpdateKillFeedPhrasesResponse> {
  try {
    const { data } = await api.post<UpdateKillFeedPhrasesResponse>(
      '/config/kill-feed-phrases',
      phrases
    );
    return data;
  } catch (error: any) {
    console.error('[Config API Error]', error);
    if (error.response?.data) {
      return error.response.data;
    }
    return {
      success: false,
      error: error.message || 'Erro ao atualizar frases do kill feed',
    };
  }
}


