// Types for the Virtuals Surge Sniper API

export interface BondingCurveMetrics {
  progress_percent: number;
  bonding_value_virtual: number;
  current_supply: number;
  total_supply: number;
  current_price: number;
  is_on_curve: boolean;
  is_graduated: boolean;
}

export interface PriceMetrics {
  current_price: number;
  price_24h_ago: number;
  price_change_24h: number;
  market_cap: number;
  fdv: number;
  liquidity_usd: number;
  volume_24h: number;
  volume_7d: number;
}

export interface SurgeMetrics {
  volume_multiplier: number;
  activity_multiplier: number;
  overall_surge_score: number;
  is_surging: boolean;
  last_surge_detected: string | null;
}

export interface UsageMetrics {
  acp_jobs_24h: number;
  acp_jobs_total: number;
  inference_calls_24h: number;
  micro_payments_24h: number;
  estimated_revenue_usd: number;
}

export interface AlphaScore {
  overall_score: number;
  surge_component: number;
  usage_component: number;
  bonding_component: number;
  trend_component: number;
}

export interface TokenData {
  address: string;
  name: string;
  symbol: string;
  agent_id: string;
  creator: string;
  description: string;
  age_days: number;
  launched_at: string | null;
  bonding: BondingCurveMetrics;
  price: PriceMetrics;
  surge: SurgeMetrics;
  usage: UsageMetrics;
  alpha_score: AlphaScore;
  accumulated_virtual: number;
  token_type: "on_curve" | "graduated";
  status: "active" | "sleeping";
}

export interface SurgeAlert {
  token_address: string;
  token_name: string;
  surge_type: string;
  surge_score: number;
  surge_multiplier: number;
  timestamp: string;
  details: string;
}

// HTTP API client
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  getTokens: (params?: Record<string, string>) => {
    const qs = new URLSearchParams(params || {}).toString();
    return request<TokenData[]>(`/tokens${qs ? "?" + qs : ""}`);
  },
  getTokenDetail: (address: string) =>
    request<TokenData | null>(`/tokens/${address}`),
  getNewTokens: (hours: number = 24) =>
    request<TokenData[]>(`/new-tokens?hours=${hours}`),
  getSurges: () => request<SurgeAlert[]>("/surges"),
  triggerSnipe: (data: {
    token_address: string;
    amount_virtual: number;
    execute?: boolean;
  }) => request("/snipe", { method: "POST", body: JSON.stringify(data) }),
  health: () => request("/health"),
};

export default api;
