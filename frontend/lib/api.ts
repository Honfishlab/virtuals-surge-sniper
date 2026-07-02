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
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// WebSocket client
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8080";

export interface WSMessage {
  type: "surge_alerts" | "token_update" | "ping";
  data?: any;
  count?: number;
  ts?: number;
}

export type WSHandler = (msg: WSMessage) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<WSHandler>> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(endpoint: string) {
    this.ws = new WebSocket(endpoint);

    this.ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      this.handlers.get(msg.type)?.forEach((handler) => handler(msg));
    };

    this.ws.onclose = () => {
      this.reconnect();
    };

    this.ws.onerror = (error) => {
      console.error(`WS error: ${error}`);
    };
  }

  subscribe(type: string, handler: WSHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);
  }

  unsubscribe(type: string, handler?: WSHandler) {
    if (!handler) {
      this.handlers.delete(type);
    } else {
      this.handlers.get(type)?.delete(handler);
    }
  }

  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max reconnection attempts reached");
      return;
    }
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts})`);
    this.reconnectTimer = setTimeout(() => {
      this.connect(this.ws?.url || WS_BASE);
    }, delay);
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    if (this.ws) {
      this.ws.close();
    }
    this.reconnectAttempts = 0;
  }
}

// Singleton instances
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

// Export singleton WS clients
export const surgeWS = new WebSocketClient();
export const tokenWS = new WebSocketClient();

export default api;
