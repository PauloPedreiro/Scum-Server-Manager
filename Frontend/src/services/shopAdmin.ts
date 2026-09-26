import api from './server';

export type ApiSuccess<T> = {
  success: true;
  data: T;
  message?: string;
};

export type ApiError = {
  success: false;
  error?: string;
  message?: string;
};

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

export type WalletTxItem = {
  tx_id: string;
  delta: number;
  reason: string;
  ref_type: string | null;
  ref_id: string | null;
  meta: Record<string, any> | null;
  created_at: string;
};

export type ShopAdminCatalogItem = {
  code: number;
  setup: string;
  name: string;
  display_name?: string | null;  // Campo retornado pelo backend após PATCH
  catalog_enabled: boolean;
  offer_enabled: boolean;
  price: number;
  qty: number;
  max_per_order: number | null;
  max_per_day: number | null;
};

export type ShopAdminCatalogResponse = ApiResponse<{
  items: ShopAdminCatalogItem[];
  count: number;
}>;

export async function getShopAdminCatalog(): Promise<ShopAdminCatalogResponse> {
  const { data } = await api.get<ShopAdminCatalogResponse>('/shop/admin/catalog');
  return data;
}

export type PatchShopAdminCatalogRequest = {
  display_name?: string;
  catalog_enabled?: boolean;
  offer_enabled?: boolean;
  price?: number;
  qty?: number;
  max_per_order?: number | null;
  max_per_day?: number | null;
};

export type PatchShopAdminCatalogResponse = ApiResponse<{ item: ShopAdminCatalogItem }>;

export async function patchShopAdminCatalogItem(
  code: number,
  payload: PatchShopAdminCatalogRequest
): Promise<PatchShopAdminCatalogResponse> {
  const { data } = await api.patch<PatchShopAdminCatalogResponse>(`/shop/admin/catalog/${code}`, payload);
  return data;
}

export type ShopAdminScannerChestResponse = ApiResponse<{ chest_id: number }>;

export async function setShopAdminScannerChest(chestId: number): Promise<ShopAdminScannerChestResponse> {
  const { data } = await api.post<ShopAdminScannerChestResponse>('/shop/admin/scanner-chest', {
    chest_id: chestId,
  });
  return data;
}

export type ShopAdminScannerSyncResponse = ApiResponse<{
  chest_id: number;
  discovered_setups: number;
  created_catalog: number;
}>;

export async function syncShopAdminScanner(): Promise<ShopAdminScannerSyncResponse> {
  const { data } = await api.post<ShopAdminScannerSyncResponse>('/shop/admin/scanner/sync', {});
  return data;
}

export type ShopWalletBalanceResponse = ApiResponse<{
  steam_id: string;
  balance: number;
}>;

export async function getShopWalletBalance(steamId?: string): Promise<ShopWalletBalanceResponse> {
  const { data } = await api.get<ShopWalletBalanceResponse>('/shop/wallet/balance', {
    params: steamId ? { steam_id: steamId } : undefined,
  });
  return data;
}

export type ShopWalletTransactionsResponse = ApiResponse<{
  steam_id: string;
  items: WalletTxItem[];
  count: number;
}>;

export async function getShopWalletTransactions(limit?: number): Promise<ShopWalletTransactionsResponse> {
  const { data } = await api.get<ShopWalletTransactionsResponse>('/shop/wallet/transactions', {
    params: typeof limit === 'number' ? { limit } : undefined,
  });
  return data;
}

/** @deprecated Use RegisteredPlayerItem instead */
export type ShopMailboxItem = {
  steam_id: string;
  player_name: string | null;
  chest_id: number;
  created_at: string;
  updated_at: string;
};

/** @deprecated Use RegisteredPlayersListResponse instead */
export type ShopMailboxListResponse = ApiResponse<{
  items: ShopMailboxItem[];
  total: number;
  count: number;
  limit: number;
  offset: number;
}>;

/** @deprecated Use getRegisteredPlayers instead */
export async function getShopMailbox(limit = 100, offset = 0): Promise<ShopMailboxListResponse> {
  const { data } = await api.get<ShopMailboxListResponse>('/shop/mailbox', {
    params: { limit, offset },
  });
  return data;
}

export type RegisteredPlayerItem = {
  steam_id: string;
  player_name: string | null;
  discord_user_id: string | null;
  discord_linked_at: string | null;
  created_at: string | null;
  balance?: number;
};

export type RegisteredPlayersListResponse = ApiResponse<{
  items: RegisteredPlayerItem[];
  total: number;
  count: number;
  limit: number;
  offset: number;
}>;

export async function getRegisteredPlayers(
  limit = 100,
  offset = 0,
  q?: string,
  sort_by?: string,
  sort_order?: string
): Promise<RegisteredPlayersListResponse> {
  const { data } = await api.get<RegisteredPlayersListResponse>(
    '/shop/admin/registered-players',
    { params: { limit, offset, q, sort_by, sort_order } }
  );
  return data;
}


export type ShopAdminIntegrationKeyItem = {
  key_id: string;
  name: string;
  enabled: 0 | 1;
  created_at: string;
  last_used_at: string | null;
};

export type ShopAdminIntegrationKeysListResponse = ApiResponse<{
  items: ShopAdminIntegrationKeyItem[];
  count: number;
}>;

export async function getShopAdminIntegrationKeys(): Promise<ShopAdminIntegrationKeysListResponse> {
  const { data } = await api.get<ShopAdminIntegrationKeysListResponse>('/shop/admin/integrations/keys');
  return data;
}

export type PostShopAdminIntegrationKeyRequest = {
  name: string;
  key: string;
};

export type PostShopAdminIntegrationKeyResponse = ApiResponse<{
  key_id: string;
  name: string;
  enabled: 0 | 1;
}>;

export async function createShopAdminIntegrationKey(
  payload: PostShopAdminIntegrationKeyRequest
): Promise<PostShopAdminIntegrationKeyResponse> {
  const { data } = await api.post<PostShopAdminIntegrationKeyResponse>('/shop/admin/integrations/keys', payload);
  return data;
}

export type PatchShopAdminIntegrationKeyRequest = {
  enabled: 0 | 1;
};

export type PatchShopAdminIntegrationKeyResponse = ApiResponse<{
  key_id: string;
  name: string;
  enabled: 0 | 1;
}>;

export async function patchShopAdminIntegrationKey(
  keyId: string,
  payload: PatchShopAdminIntegrationKeyRequest
): Promise<PatchShopAdminIntegrationKeyResponse> {
  const { data } = await api.patch<PatchShopAdminIntegrationKeyResponse>(`/shop/admin/integrations/keys/${keyId}`,
    payload
  );
  return data;
}

export async function getShopAdminWalletTransactions(
  steamId: string,
  limit?: number
): Promise<ShopWalletTransactionsResponse> {
  const params: Record<string, any> = { steam_id: steamId };
  if (typeof limit === 'number') params.limit = limit;
  const { data } = await api.get<ShopWalletTransactionsResponse>('/shop/admin/wallet/transactions', { params });
  return data;
}

export type ShopAdminWalletAdjustRequest = {
  external_id: string;
  steam_id: string;
  delta: number;
  reason: string;
  meta?: Record<string, any>;
};

export type ShopAdminWalletAdjustResponse = ApiResponse<{
  already_applied: boolean;
  steam_id: string;
  delta: number;
  balance: number;
}>;

export type ShopAdminRewardsPlaytimeConfig = {
  enabled: 0 | 1;
  points_per_hour: number;
  max_hours_per_run: number;
  interval_minutes: number;
  baseline_mode: string;
};

export type ShopAdminRewardsPlaytimeConfigResponse = ApiResponse<ShopAdminRewardsPlaytimeConfig>;

export async function getShopAdminRewardsPlaytimeConfig(): Promise<ShopAdminRewardsPlaytimeConfigResponse> {
  const { data } = await api.get<ShopAdminRewardsPlaytimeConfigResponse>('/shop/admin/rewards/playtime-config');
  return data;
}

export type PatchShopAdminRewardsPlaytimeConfigRequest = {
  enabled?: 0 | 1;
  points_per_hour?: number;
  max_hours_per_run?: number;
};

export async function patchShopAdminRewardsPlaytimeConfig(
  payload: PatchShopAdminRewardsPlaytimeConfigRequest
): Promise<ShopAdminRewardsPlaytimeConfigResponse> {
  const { data } = await api.patch<ShopAdminRewardsPlaytimeConfigResponse>('/shop/admin/rewards/playtime-config', payload);
  return data;
}

export type ShopAdminRewardsPlaytimeRule = {
  rule_id: string;
  name: string;
  enabled: 0 | 1;
  exclusive: 0 | 1;
  points_per_hour: number;
  max_hours_per_run: number;
  audience_type: 'all' | 'list';
};

export type ShopAdminRewardsPlaytimeRulesResponse = ApiResponse<{
  items: ShopAdminRewardsPlaytimeRule[];
  count: number;
}>;

export async function getShopAdminRewardsPlaytimeRules(enabledOnly?: 0 | 1): Promise<ShopAdminRewardsPlaytimeRulesResponse> {
  const params = enabledOnly ? { enabled_only: 1 } : undefined;
  const { data } = await api.get<ShopAdminRewardsPlaytimeRulesResponse>('/shop/admin/rewards/playtime-rules', { params });
  return data;
}

export type PostShopAdminRewardsPlaytimeRuleRequest = {
  name: string;
  enabled: 0 | 1;
  exclusive: 0 | 1;
  points_per_hour: number;
  max_hours_per_run: number;
  audience_type: 'all' | 'list';
};

export type PostShopAdminRewardsPlaytimeRuleResponse = ApiResponse<{ rule_id: string }>;

export async function postShopAdminRewardsPlaytimeRule(
  payload: PostShopAdminRewardsPlaytimeRuleRequest
): Promise<PostShopAdminRewardsPlaytimeRuleResponse> {
  const { data } = await api.post<PostShopAdminRewardsPlaytimeRuleResponse>('/shop/admin/rewards/playtime-rules', payload);
  return data;
}

export type PatchShopAdminRewardsPlaytimeRuleRequest = {
  enabled?: 0 | 1;
  exclusive?: 0 | 1;
  points_per_hour?: number;
  max_hours_per_run?: number;
  audience_type?: 'all' | 'list';
  name?: string;
};

export type PatchShopAdminRewardsPlaytimeRuleResponse = ApiResponse<{}>;

export async function patchShopAdminRewardsPlaytimeRule(
  ruleId: string,
  payload: PatchShopAdminRewardsPlaytimeRuleRequest
): Promise<PatchShopAdminRewardsPlaytimeRuleResponse> {
  const { data } = await api.patch<PatchShopAdminRewardsPlaytimeRuleResponse>(
    `/shop/admin/rewards/playtime-rules/${encodeURIComponent(ruleId)}`,
    payload
  );
  return data;
}

export type DeleteShopAdminRewardsPlaytimeRuleResponse = ApiResponse<{}>;

export async function deleteShopAdminRewardsPlaytimeRule(ruleId: string): Promise<DeleteShopAdminRewardsPlaytimeRuleResponse> {
  const { data } = await api.delete<DeleteShopAdminRewardsPlaytimeRuleResponse>(
    `/shop/admin/rewards/playtime-rules/${encodeURIComponent(ruleId)}`
  );
  return data;
}

export type ShopAdminRewardsPlaytimeRuleTargetsResponse = ApiResponse<{
  rule_id: string;
  items: string[];
  count: number;
}>;

export async function getShopAdminRewardsPlaytimeRuleTargets(ruleId: string): Promise<ShopAdminRewardsPlaytimeRuleTargetsResponse> {
  const { data } = await api.get<ShopAdminRewardsPlaytimeRuleTargetsResponse>(
    `/shop/admin/rewards/playtime-rules/${encodeURIComponent(ruleId)}/targets`
  );
  return data;
}

export type PostShopAdminRewardsPlaytimeRuleTargetRequest = { steam_id: string };
export type PostShopAdminRewardsPlaytimeRuleTargetResponse = ApiResponse<{}>;

export async function postShopAdminRewardsPlaytimeRuleTarget(
  ruleId: string,
  payload: PostShopAdminRewardsPlaytimeRuleTargetRequest
): Promise<PostShopAdminRewardsPlaytimeRuleTargetResponse> {
  const { data } = await api.post<PostShopAdminRewardsPlaytimeRuleTargetResponse>(
    `/shop/admin/rewards/playtime-rules/${encodeURIComponent(ruleId)}/targets`,
    payload
  );
  return data;
}

export type DeleteShopAdminRewardsPlaytimeRuleTargetResponse = ApiResponse<{}>;

export async function deleteShopAdminRewardsPlaytimeRuleTarget(
  ruleId: string,
  steamId: string
): Promise<DeleteShopAdminRewardsPlaytimeRuleTargetResponse> {
  const { data } = await api.delete<DeleteShopAdminRewardsPlaytimeRuleTargetResponse>(
    `/shop/admin/rewards/playtime-rules/${encodeURIComponent(ruleId)}/targets/${encodeURIComponent(steamId)}`
  );
  return data;
}

export async function adjustShopAdminWallet(
  payload: ShopAdminWalletAdjustRequest
): Promise<ShopAdminWalletAdjustResponse> {
  const { data } = await api.post<any>('/shop/admin/wallet/adjust', payload);
  if (data?.success === true && data?.data == null) {
    const { success, message, ...rest } = data;
    if (Object.keys(rest).length > 0) {
      return { success: true, data: rest, message } as ShopAdminWalletAdjustResponse;
    }
  }
  return data as ShopAdminWalletAdjustResponse;
}

export type ShopAdminCatalogClearResponse = ApiResponse<{
  deleted: {
    shop_offer: number;
    shop_catalog: number;
  };
}>;

export async function clearShopAdminCatalog(): Promise<ShopAdminCatalogClearResponse> {
  const { data } = await api.post<ShopAdminCatalogClearResponse>('/shop/admin/catalog/clear', {
    confirm: 'DELETE_ALL_CATALOG',
  });
  return data;
}

export type ShopAdminCatalogImportItem = {
  code: number;
  display_name?: string;
  setup: string;
  catalog_enabled: boolean;
  offer_enabled: boolean;
  price: number;
  qty: number;
  max_per_order: number | null;
  max_per_day: number | null;
};

export type ShopAdminCatalogImportRequest = {
  schema: 'shop_catalog_snapshot_v1';
  exportedAt: string;
  mode?: 'merge';
  dry_run?: boolean;
  items: ShopAdminCatalogImportItem[];
};

export type ShopAdminCatalogImportResult = {
  created: number;
  updated: number;
  ignored: number;
  errors: Array<{ code: number; reason: string; field?: string }>;
};

export type ShopAdminCatalogImportResponse = ApiResponse<ShopAdminCatalogImportResult>;

export async function importShopAdminCatalog(
  payload: ShopAdminCatalogImportRequest
): Promise<ShopAdminCatalogImportResponse> {
  const { data } = await api.post<ShopAdminCatalogImportResponse>('/shop/admin/catalog/import', payload);
  return data;
}

export type PostShopAdminCatalogRequest = {
  setup: string;
  display_name?: string;
  price?: number;
  qty?: number;
  enabled?: boolean;
  code?: number;
};

export type PostShopAdminCatalogItem = {
  code: number;
  setup: string;
  display_name: string;
  price: number;
  qty: number;
  enabled: boolean;
};

export type PostShopAdminCatalogResponse = ApiResponse<PostShopAdminCatalogItem>;

export async function postShopAdminCatalog(
  payload: PostShopAdminCatalogRequest
): Promise<PostShopAdminCatalogResponse> {
  const { data } = await api.post<PostShopAdminCatalogResponse>('/shop/admin/catalog', payload);
  return data;
}

// --- Novos tipos e estruturas para Kits ---

export type ShopAdminKitItemDetail = {
  setup: string;
  qty: number;
};

export type ShopAdminKit = {
  kit_id: string;
  code: number;
  name: string;
  price: number;
  enabled: 0 | 1 | boolean;
  only_once: 0 | 1 | boolean;
  auto_deliver_on_register: 0 | 1 | boolean;
  created_at: string;
  updated_at: string;
  items: ShopAdminKitItemDetail[];
};

export type ShopAdminKitListResponse = ApiResponse<ShopAdminKit[]>;
export type ShopAdminKitDetailResponse = ApiResponse<ShopAdminKit>;
export type ShopAdminKitActionResponse = ApiResponse<{ message: string }>;

export type SaveKitPayload = {
  kit_id: string;
  code: number;
  name: string;
  price: number;
  enabled: boolean;
  only_once: boolean;
  auto_deliver_on_register?: boolean;
  items: ShopAdminKitItemDetail[];
};

export type ScanKitPayload = {
  chest_id: number;
  kit_id: string;
  name: string;
  price: number;
  enabled: boolean;
  only_once: boolean;
  auto_deliver_on_register?: boolean;
  code?: number;
};

/**
 * Retorna a lista de todos os kits cadastrados
 */
export async function getShopAdminKits(): Promise<ShopAdminKitListResponse> {
  const { data } = await api.get<ShopAdminKitListResponse>('/shop/admin/kits');
  return data;
}

/**
 * Cria ou edita um kit manualmente
 */
export async function saveShopAdminKit(payload: SaveKitPayload): Promise<ShopAdminKitActionResponse> {
  const { data } = await api.post<ShopAdminKitActionResponse>('/shop/admin/kits', payload);
  return data;
}

/**
 * Obtém os detalhes de um kit específico
 */
export async function getShopAdminKitDetail(kitId: string): Promise<ShopAdminKitDetailResponse> {
  const { data } = await api.get<ShopAdminKitDetailResponse>(`/shop/admin/kits/${encodeURIComponent(kitId)}`);
  return data;
}

/**
 * Deleta um kit específico
 */
export async function deleteShopAdminKit(kitId: string): Promise<ShopAdminKitActionResponse> {
  const { data } = await api.delete<ShopAdminKitActionResponse>(`/shop/admin/kits/${encodeURIComponent(kitId)}`);
  return data;
}

/**
 * Escaneia um baú in-game e cria um kit automaticamente
 */
export async function scanChestToKit(payload: ScanKitPayload): Promise<ApiResponse<ShopAdminKit>> {
  const { data } = await api.post<ApiResponse<ShopAdminKit>>('/shop/admin/kits/scan', payload);
  return data;
}

