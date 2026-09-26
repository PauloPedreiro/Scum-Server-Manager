import api from './server';

// Interfaces TypeScript para ServerSettings.ini

export interface ServerSettingsResponse {
  success: boolean;
  data: {
    [section: string]: {
      [key: string]: string;
    };
  };
  timestamp?: number;
  error?: string;
}

export interface UpdateSettingRequest {
  section: string;
  key: string;
  value: string | number | boolean;
}

export interface UpdateSettingResponse {
  success: boolean;
  message: string;
  data: {
    section: string;
    key: string;
    value: string;
    backup: string | null;
  };
  timestamp?: number;
  error?: string;
}

export interface UpdateSectionRequest {
  [key: string]: string;
}

export interface UpdateSectionResponse {
  success: boolean;
  message: string;
  data: {
    section: string;
    updated_fields: string[];
    backup: string | null;
  };
  timestamp?: number;
  error?: string;
}

/**
 * Obter todas as configurações ou uma seção específica
 */
export async function getServerSettings(
  section?: string
): Promise<ServerSettingsResponse> {
  try {
    const params = section ? { section } : {};
    const { data } = await api.get<ServerSettingsResponse>('/server/settings', {
      params,
    });
    return data;
  } catch (error: any) {
    console.error('[Settings API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao buscar configurações',
      data: {},
    };
  }
}

/**
 * Atualizar uma configuração específica (PATCH)
 */
export async function updateSetting(
  request: UpdateSettingRequest
): Promise<UpdateSettingResponse> {
  try {
    const { data } = await api.patch<UpdateSettingResponse>(
      '/server/settings',
      request
    );
    return data;
  } catch (error: any) {
    console.error('[Settings API Error]', error);
    
    if (error.response?.data) {
      return error.response.data;
    }
    
    return {
      success: false,
      error: error.message || 'Erro ao atualizar configuração',
      message: error.message || 'Erro ao atualizar configuração',
      data: {
        section: request.section,
        key: request.key,
        value: String(request.value),
        backup: null,
      },
    };
  }
}

/**
 * Atualizar seção completa (PUT)
 */
export async function updateSection(
  section: string,
  settings: UpdateSectionRequest
): Promise<UpdateSectionResponse> {
  try {
    const { data } = await api.put<UpdateSectionResponse>(
      `/server/settings/${section}`,
      settings
    );
    return data;
  } catch (error: any) {
    console.error('[Settings API Error]', error);
    
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
        backup: null,
      },
    };
  }
}

