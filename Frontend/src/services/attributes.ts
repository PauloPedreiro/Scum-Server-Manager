import api from './server';

export type PrisonerListItem = {
  prisoner_id: number;
  steam_id: string;
  name: string;
};

export type AttributesValues = {
  strength: number;
  constitution: number;
  dexterity: number;
  intelligence: number;
};

export type AttributesPlayer = {
  prisoner_id: number;
  steam_id: string;
  name: string;
};

export type ListPrisonersResponse = {
  success: boolean;
  data?: {
    prisoners: PrisonerListItem[];
    total: number;
    limit: number;
    offset: number;
    count: number;
  };
  error?: string;
};

export async function listPrisoners(params?: {
  query?: string;
  limit?: number;
  offset?: number;
}): Promise<ListPrisonersResponse> {
  const { data } = await api.get<ListPrisonersResponse>('/attributes/prisoners', {
    params: {
      query: params?.query,
      limit: params?.limit,
      offset: params?.offset,
    },
  });
  return data;
}

export type GetPlayerAttributesResponse = {
  success: boolean;
  data?: {
    player: AttributesPlayer;
    attributes: AttributesValues;
  };
  error?: string;
  details?: any;
};

export async function getPlayerAttributes(identifier: string | number): Promise<GetPlayerAttributesResponse> {
  const { data } = await api.get<GetPlayerAttributesResponse>(`/attributes/player/${identifier}`);
  return data;
}

export type PatchPlayerAttributesResponse = {
  success: boolean;
  message?: string;
  data?: {
    player: AttributesPlayer;
    before: AttributesValues;
    after: AttributesValues;
    changes: string[];
    backup_path: string;
  };
  error?: string;
  details?: any;
};

export async function patchPlayerAttributes(
  identifier: string | number,
  attributes: Partial<AttributesValues>
): Promise<PatchPlayerAttributesResponse> {
  const { data } = await api.patch<PatchPlayerAttributesResponse>(`/attributes/player/${identifier}`, {
    attributes,
  });
  return data;
}

export type GetAttributePricesResponse = {
  success: boolean;
  data?: {
    prices: {
      strength: Record<string, number>;
      constitution: Record<string, number>;
      dexterity: Record<string, number>;
      intelligence: Record<string, number>;
    };
    expiration_enabled: 0 | 1;
    expiration_duration_days: number;
  };
  error?: string;
};

export type UpdateAttributePricesResponse = {
  success: boolean;
  message?: string;
  error?: string;
};

export async function getAttributePrices(): Promise<GetAttributePricesResponse> {
  const { data } = await api.get<GetAttributePricesResponse>('/attributes/prices');
  return data;
}

export async function updateAttributePrices(payload: {
  prices: any;
  expiration_enabled: boolean;
  expiration_duration_days: number;
}): Promise<UpdateAttributePricesResponse> {
  const { data } = await api.put<UpdateAttributePricesResponse>('/attributes/prices', payload);
  return data;
}
