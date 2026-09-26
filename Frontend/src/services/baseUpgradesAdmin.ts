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
  code?: string;
  details?: any;
};

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

export type FlagOwnerType = 'squad' | 'player' | 'unknown';

export type AdminFlagOwnerItem = {
  flag_id: number;
  owner: string;
  owner_type: FlagOwnerType;
  elements: number;
  last_seen_at: string;
};

export type AdminFlagsOwnersResponse = ApiResponse<{
  flags: AdminFlagOwnerItem[];
  total: number;
  page: number;
  page_size: number;
}>;

export async function getAdminFlagsOwners(page = 1, pageSize = 50): Promise<AdminFlagsOwnersResponse> {
  const { data } = await api.get<AdminFlagsOwnersResponse>('/admin/flags/owners', {
    params: { page, page_size: pageSize },
  });
  return data;
}

export type BaseMaterialDryRunRequest = {
  flag_id: number;
  target_level: number;
  fallback_lowest: boolean;
  auto_enrich_whitelist?: boolean;
};

export type BaseMaterialDryRunStats = {
  total: number;
  not_whitelisted: number;
  no_family: number;
  no_mapping: number;
  fallback_lowest_used: number;
  already_target: number;
  to_change: number;
};

export type BaseMaterialDryRunChangeSample = {
  element_id: number;
  from_asset?: string;
  to_asset?: string;
  old_asset?: string;
  new_asset?: string;
  family_key: string;
};

export type BaseMaterialDryRunResponse = ApiResponse<{
  flag_id: number;
  internal_base_id: number;
  target_level: number;
  stats: BaseMaterialDryRunStats;
  changes_sample: BaseMaterialDryRunChangeSample[];
  changes_sample_truncated: boolean;
  debug?: {
    auto_whitelisted?: number;
    auto_whitelisted_assets?: string[];
  };
}>;

export async function dryRunBaseMaterialUpgrade(
  payload: BaseMaterialDryRunRequest
): Promise<BaseMaterialDryRunResponse> {
  const { data } = await api.post<BaseMaterialDryRunResponse>('/admin/base-material/dry-run', payload);
  return data;
}

export type BaseMaterialScheduleRequest = BaseMaterialDryRunRequest & {
  run_now_if_offline: boolean;
};

export type BaseMaterialRunResult = {
  claimed: number;
  updated: number;
  no_changes: number;
  failed: number;
  job_ids: string[];
};

export type BaseMaterialScheduleResponse = ApiResponse<{
  job_id: string;
  scheduled: boolean;
  deduplicated?: boolean;
  executed_now: boolean;
  run_result: BaseMaterialRunResult | null;
}>;

export async function scheduleBaseMaterialUpgrade(
  payload: BaseMaterialScheduleRequest
): Promise<BaseMaterialScheduleResponse> {
  const { data } = await api.post<BaseMaterialScheduleResponse>('/admin/base-material/schedule', payload);
  return data;
}

export type BaseMaterialJobStatus = 'pending' | 'done' | 'failed' | string;

export type BaseMaterialJobItem = {
  job_id: string;
  flag_id: number;
  target_level: number;
  fallback_lowest: boolean;
  status: BaseMaterialJobStatus;
  attempt_count: number;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type BaseMaterialJobsResponse = ApiResponse<{
  jobs: BaseMaterialJobItem[];
  total: number;
  limit: number;
  offset: number;
}>;

export async function getBaseMaterialJobs(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<BaseMaterialJobsResponse> {
  const { data } = await api.get<BaseMaterialJobsResponse>('/admin/base-material/jobs', {
    params,
  });
  return data;
}
