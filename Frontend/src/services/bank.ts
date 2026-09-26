import api from './server';

export interface BankBalances {
  money_in_hand: number;
  money_in_bank: number;
  money_total: number;
  gold: number;
}

export interface BankAccountMeta {
  updated_at: string;
  source: string;
  last_transaction_ts: string | null;
}

export interface BankAccountCurrentItem {
  steam_id: string;
  player_name: string;
  account_number: string;
  balances: BankBalances;
  meta: BankAccountMeta;
}

export interface BankAccountsCurrentResponse {
  success: boolean;
  data?: {
    items: BankAccountCurrentItem[];
    count: number;
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
  timestamp?: number;
  error?: string;
}

export interface BankAccountsCurrentParams {
  limit?: number;
  offset?: number;
  q?: string;
}

export async function getBankAccountsCurrent(
  params: BankAccountsCurrentParams = {}
): Promise<BankAccountsCurrentResponse> {
  const { data } = await api.get<BankAccountsCurrentResponse>('/shop/admin/bank-accounts/current', {
    params,
  });
  return data;
}
