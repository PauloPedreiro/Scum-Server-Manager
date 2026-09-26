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

export type VehicleAdminCatalogItem = {
  code: number;
  setup: string;
  display_name: string;
  name: string;
  template_vehicle_entity_id: number;
  price: number;
  enabled: boolean;
  image_url?: string | null;
};

export type VehiclesAdminCatalogResponse = ApiResponse<{
  items: VehicleAdminCatalogItem[];
  count: number;
}>;

export async function getVehiclesAdminCatalog(): Promise<VehiclesAdminCatalogResponse> {
  const { data } = await api.get<VehiclesAdminCatalogResponse>('/vehicles/admin/catalog');
  return data;
}

export type PatchVehicleAdminCatalogRequest = {
  display_name?: string;
  price?: number;
  enabled?: boolean;
};

export type PatchVehicleAdminCatalogResponse = ApiResponse<{ item: VehicleAdminCatalogItem }>;

export async function patchVehicleAdminCatalogItem(
  code: number,
  payload: PatchVehicleAdminCatalogRequest
): Promise<PatchVehicleAdminCatalogResponse> {
  const { data } = await api.patch<PatchVehicleAdminCatalogResponse>(`/vehicles/admin/catalog/${code}`, payload);
  return data;
}

export type UploadVehicleAdminCatalogImageResponse = ApiResponse<{
  code: number;
  image_url: string;
}>;

export async function uploadVehicleAdminCatalogImage(
  code: number,
  file: File
): Promise<UploadVehicleAdminCatalogImageResponse> {
  const form = new FormData();
  form.append('file', file);

  const { data } = await api.post<UploadVehicleAdminCatalogImageResponse>(`/vehicles/admin/catalog/${code}/image`, form, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return data;
}

export type AdminVehicleTemplatesSyncRequest = {
  source_scum_db: string;
  ids?: number[];
  template_vehicle_entity_ids?: number[];
  force?: boolean;
};

export type AdminVehicleTemplatesSyncResponse = ApiResponse<{
  report: {
    output: string;
    synced: number[];
    missing: number[];
    counts: {
      requested: number;
      synced: number;
      missing: number;
    };
  };
  diagnostics?: {
    service_running?: boolean;
    used_snapshot?: boolean;
  };
  invalid: Array<any>;
  catalog: {
    ssm_db_path: string;
    upserted: number;
    skipped: number;
    name_source_db: string;
    defaults: {
      code: string;
      setup: string;
      display_name: string;
      price: number;
      enabled: number;
    };
  };
}>;

export async function syncVehicleAdminTemplates(
  payload: AdminVehicleTemplatesSyncRequest
): Promise<AdminVehicleTemplatesSyncResponse> {
  const { data } = await api.post<AdminVehicleTemplatesSyncResponse>('/vehicles/admin/templates/sync', payload);
  return data;
}

export type AdminVehicleTemplatesResetRequest = {
  force?: boolean;
  make_backup?: boolean;
  reset_catalog?: boolean;
  reset_orders?: boolean;
};

export type AdminVehicleTemplatesResetResponse = ApiResponse<{
  templates_db: string;
  reset_catalog: boolean;
  reset_orders: boolean;
}>;

export async function resetVehicleAdminTemplates(
  payload: AdminVehicleTemplatesResetRequest
): Promise<AdminVehicleTemplatesResetResponse> {
  const { data } = await api.post<AdminVehicleTemplatesResetResponse>('/vehicles/admin/templates/reset', payload);
  return data;
}
