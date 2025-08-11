export interface ServerConfigResponse {
  success: boolean;
  content?: string[];
  message?: string;
  error?: string;
  stats?: {
    size: number;
    modified: string;
    created: string;
  };
  backupCreated?: string;
  linesCount?: number;
  updated?: boolean;
}

export interface BackupInfo {
  filename: string;
  size: number;
  created: string;
  originalFile: string;
}

export interface BackupsResponse {
  success: boolean;
  backups?: BackupInfo[];
  error?: string;
}

export interface ConfigInfo {
  sections: string[];
  totalLines: number;
  size: number;
  modified: string;
  importantSettings: Record<string, string>;
}

export interface ConfigInfoResponse {
  success: boolean;
  info?: ConfigInfo;
  error?: string;
}

export class ServerConfigService {
  private static baseUrl = '/api/configserver';

  // Ler configuração completa
  static async getServerConfig(): Promise<ServerConfigResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/ServerSettings.ini`);
      const data = await response.json();
      return data;
    } catch (error: any) {
      console.error('Erro ao buscar configuração do servidor:', error);
      return {
        success: false,
        error: error.message || 'Erro ao buscar configuração do servidor'
      };
    }
  }

  // Salvar configuração completa
  static async saveServerConfig(content: string[]): Promise<ServerConfigResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/ServerSettings.ini`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      });
      
      const data = await response.json();
      return data;
    } catch (error: any) {
      console.error('Erro ao salvar configuração do servidor:', error);
      return {
        success: false,
        error: error.message || 'Erro ao salvar configuração do servidor'
      };
    }
  }

  // Atualizar valor específico
  static async updateConfigValue(section: string, key: string, value: string): Promise<ServerConfigResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/ServerSettings.ini/${section}/${key}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ value })
      });
      const data = await response.json();
      return data;
    } catch (error: any) {
      console.error('Erro ao atualizar valor da configuração:', error);
      return {
        success: false,
        error: error.message || 'Erro ao atualizar valor da configuração'
      };
    }
  }

  // Listar backups
  static async getBackups(): Promise<BackupsResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/backups`);
      const data = await response.json();
      return data;
    } catch (error: any) {
      console.error('Erro ao buscar backups:', error);
      return {
        success: false,
        error: error.message || 'Erro ao buscar backups'
      };
    }
  }

  // Restaurar backup
  static async restoreBackup(filename: string): Promise<ServerConfigResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/backups/restore/${filename}`, {
        method: 'POST'
      });
      const data = await response.json();
      return data;
    } catch (error: any) {
      console.error('Erro ao restaurar backup:', error);
      return {
        success: false,
        error: error.message || 'Erro ao restaurar backup'
      };
    }
  }

  // Obter informações da configuração
  static async getConfigInfo(): Promise<ConfigInfoResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/ServerSettings.ini/info`);
      const data = await response.json();
      return data;
    } catch (error: any) {
      console.error('Erro ao buscar informações da configuração:', error);
      return {
        success: false,
        error: error.message || 'Erro ao buscar informações da configuração'
      };
    }
  }

  // Testar configuração
  static async testConfig(content: string[]): Promise<ServerConfigResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/ServerSettings.ini/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      });
      const data = await response.json();
      return data;
    } catch (error: any) {
      console.error('Erro ao testar configuração:', error);
      return {
        success: false,
        error: error.message || 'Erro ao testar configuração'
      };
    }
  }

  // Utilitários para parsing de configuração
  static parseConfigLines(lines: string[]): Record<string, Record<string, string>> {
    const config: Record<string, Record<string, string>> = {};
    let currentSection = '';

    lines.forEach((line, index) => {
      const trimmedLine = line.trim();
      
      if (trimmedLine.startsWith('[') && trimmedLine.endsWith(']')) {
        // Nova seção
        currentSection = trimmedLine.slice(1, -1);
        config[currentSection] = {};
      } else if (trimmedLine.includes('=') && currentSection) {
        // Configuração
        const [key, ...valueParts] = trimmedLine.split('=');
        const value = valueParts.join('=');
        config[currentSection][key.trim()] = value.trim();
      }
      // Ignorar linhas vazias e comentários
    });

    return config;
  }

  static convertConfigToLines(config: Record<string, Record<string, string>>): string[] {
    const lines: string[] = [];
    
    // Ordem padrão das seções para manter a estrutura original
    const sectionOrder = ['General', 'World', 'Vehicles', 'Damage', 'Respawn', 'Features'];
    
    // Primeiro, adicionar as seções na ordem padrão
    sectionOrder.forEach(sectionName => {
      if (config[sectionName]) {
        lines.push(`[${sectionName}]`);
        // Ordenar as chaves para manter consistência
        const sortedKeys = Object.keys(config[sectionName]).sort();
        sortedKeys.forEach(key => {
          lines.push(`${key}=${config[sectionName][key]}`);
        });
        lines.push(''); // Linha em branco entre seções
      }
    });
    
    // Depois, adicionar qualquer seção que não esteja na ordem padrão
    Object.entries(config).forEach(([sectionName, settings]) => {
      if (!sectionOrder.includes(sectionName)) {
        lines.push(`[${sectionName}]`);
        // Ordenar as chaves para manter consistência
        const sortedKeys = Object.keys(settings).sort();
        sortedKeys.forEach(key => {
          lines.push(`${key}=${settings[key]}`);
        });
        lines.push(''); // Linha em branco entre seções
      }
    });

    return lines;
  }

  static findConfigValue(config: Record<string, Record<string, string>>, key: string): string | null {
    for (const section of Object.values(config)) {
      if (section[key]) {
        return section[key];
      }
    }
    
    return null;
  }

  static updateConfigValueInMemory(config: Record<string, Record<string, string>>, key: string, value: string): Record<string, Record<string, string>> {
    const newConfig = { ...config };
    
    for (const [sectionName, section] of Object.entries(newConfig)) {
      if (section[key] !== undefined) {
        newConfig[sectionName] = { ...section, [key]: value };
        return newConfig;
      }
    }

    // Se não encontrou, adiciona na seção General
    if (!newConfig.General) {
      newConfig.General = {};
    }
    newConfig.General[key] = value;
    
    return newConfig;
  }
} 