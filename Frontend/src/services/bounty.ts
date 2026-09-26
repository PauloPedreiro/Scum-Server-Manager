import api from './server';

export interface BountyDiscordConfig {
  top_killers_message_id: string;
  shame_rank_message_id: string;
}

export interface BountyNotificationsConfig {
  in_game_chat_color: string;
  activation_template: string;
  increment_template: string;
  claimed_template: string;
}

export interface BountyConfig {
  enabled: boolean;
  killstreak_trigger: number;
  base_bounty: number;
  increment_bounty: number;
  cooldown_hours: number;
  squad_leave_cooldown_hours: number;
  discord: BountyDiscordConfig;
  notifications: BountyNotificationsConfig;
}

export interface ActiveBountyPlayer {
  steam_id: string;
  player_name: string;
  current_streak: number;
  bounty_value: number;
  is_online: number;
}

export interface BountyConfigResponse {
  success: boolean;
  config: BountyConfig;
}

export interface BountyUpdateResponse {
  success: boolean;
  message: string;
}

export interface ActiveBountyResponse {
  success: boolean;
  data: ActiveBountyPlayer[];
}

export interface BountyActionResponse {
  success: boolean;
  message: string;
}

export async function getBountyConfig(): Promise<BountyConfigResponse> {
  const { data } = await api.get<BountyConfigResponse>('/bounty/config');
  return data;
}

export async function updateBountyConfig(payload: BountyConfig): Promise<BountyUpdateResponse> {
  const { data } = await api.put<BountyUpdateResponse>('/bounty/config', payload);
  return data;
}

export async function getActiveBountyPlayers(): Promise<ActiveBountyResponse> {
  const { data } = await api.get<ActiveBountyResponse>('/bounty/active');
  return data;
}

export async function triggerManualBounty(
  steamId: string,
  playerName: string,
  bountyValue: number
): Promise<BountyActionResponse> {
  const { data } = await api.post<BountyActionResponse>('/bounty/trigger', {
    steam_id: steamId,
    player_name: playerName,
    bounty_value: bountyValue,
  });
  return data;
}

export async function resetManualBounty(steamId?: string): Promise<BountyActionResponse> {
  const payload = steamId ? { steam_id: steamId } : {};
  const { data } = await api.post<BountyActionResponse>('/bounty/reset', payload);
  return data;
}
