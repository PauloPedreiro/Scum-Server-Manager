export interface AdminLogEvent {
  timestamp: string;
  name?: string;
  steamId?: string;
  command?: string;
  param?: string;
  message: string;
}

export interface AdminLogResponse {
  success: boolean;
  message: string;
  file?: string;
  data: string | string[];
}

import { buildApiUrl } from '../config/api';

export const AdminLogService = {
  async getAdminLog(): Promise<AdminLogResponse> {
    const response = await fetch(buildApiUrl('/api/adminlog'));
    if (!response.ok) throw new Error('Erro ao buscar admin log');
    return await response.json();
  },
  // Parser detalhado para comandos e mensagens
  parseLogLines(logLines: string[]): AdminLogEvent[] {
    return logLines.map(line => {
      // Regex para comandos
      const cmdMatch = line.match(/^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*'(\d+):(.*?)\(\d+\)'\s+Command:\s+'(\w+)\s?(.*)?'$/);
      if (cmdMatch) {
        return {
          timestamp: cmdMatch[1],
          steamId: cmdMatch[2],
          name: cmdMatch[3],
          command: cmdMatch[4],
          param: cmdMatch[5]?.replace(/'$/, ''),
          message: line
        };
      }
      // Regex para comandos sem parâmetro
      const cmdNoParam = line.match(/^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*'(\d+):(.*?)\(\d+\)'\s+Command:\s+'(\w+)'$/);
      if (cmdNoParam) {
        return {
          timestamp: cmdNoParam[1],
          steamId: cmdNoParam[2],
          name: cmdNoParam[3],
          command: cmdNoParam[4],
          param: '',
          message: line
        };
      }
      // Regex para teleport
      const teleportMatch = line.match(/^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*'(\d+):(.*?)\(\d+\)' Used map click teleport to player: '(\d+):(.*?)\(\d+\)' Location: (.*)$/);
      if (teleportMatch) {
        return {
          timestamp: teleportMatch[1],
          steamId: teleportMatch[2],
          name: teleportMatch[3],
          command: 'Teleport',
          param: `${teleportMatch[5]} (${teleportMatch[6]})`,
          message: line
        };
      }
      // Regex para sistema/info
      const sysMatch = line.match(/^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*(.*)$/);
      if (sysMatch) {
        return {
          timestamp: sysMatch[1],
          message: sysMatch[2]
        };
      }
      // Fallback
      return { timestamp: '', message: line };
    });
  }
}; 