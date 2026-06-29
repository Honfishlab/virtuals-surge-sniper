"use client";

import { useState, useEffect, useRef } from "react";
import { TokenUniverseTable } from "./components/TokenUniverseTable";
import { SurgeAlertPanel } from "./components/SurgeAlertPanel";
import type { TokenData, SurgeAlert, WSMessage } from "./lib/api";
import { api, surgeWS, tokenWS } from "./lib/api";

export default function Dashboard() {
  const [tokens, setTokens] = useState<TokenData[]>([]);
  const [surges, setSurges] = useState<SurgeAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<"tokens" | "surges">("tokens");
  const [wsStatus, setWsStatus] = useState<"disconnected" | "connected" | "error">("disconnected");
  const [newSurgeCount, setNewSurgeCount] = useState(0);
  const prevSurgeCountRef = useRef(0);

  // HTTP polling (fallback)
  const loadData = async () => {
    try {
      const [tokensRes, surgesRes] = await Promise.all([
        api.getTokens({ sort_by: "alpha_score", sort_order: "desc", limit: "100" }),
        api.getSurges(),
      ]);
      setTokens(tokensRes);
      setSurges(surgesRes);
      setLoading(false);
    } catch (err) {
      console.error("Failed to load data:", err);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket: surge alerts
  useEffect(() => {
    const onSurgeAlert = (msg: WSMessage) => {
      setSurges((prev) => {
        const newSurgeCount = msg.data?.length || 0;
        setNewSurgeCount((nc) => (nc > 0 ? nc + newSurgeCount : 0));
        return msg.data || prev;
      });
    };

    surgeWS.connect(`${process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"}/ws/surges`);
    surgeWS.subscribe("surge_alerts", onSurgeAlert);
    surgeWS.subscribe("ping", () => setWsStatus("connected"));
    surgeWS.subscribe("error", () => setWsStatus("error"));

    return () => {
      surgeWS.unsubscribe("surge_alerts", onSurgeAlert);
      surgeWS.unsubscribe("ping", () => {});
    };
  }, []);

  const surgingCount = tokens.filter((t) => t.surge.is_surging).length;
  const graduatedCount = tokens.filter((t) => t.token_type === "graduated").length;
  const totalMc = tokens.reduce((sum, t) => sum + t.price.market_cap, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-2xl font-bold mb-2">Loading...</div>
          <div className="text-muted-foreground">Connecting to surge sniper</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-primary/20 flex items-center justify-center">
              <span className="text-primary font-bold text-sm">V</span>
            </div>
            <div>
              <h1 className="font-bold text-lg">Virtuals Surge Sniper</h1>
              <p className="text-xs text-muted-foreground">Protocol Intelligence Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <div className="text-center">
              <div className="text-lg font-semibold">{tokens.length}</div>
              <div className="text-xs text-muted-foreground">Tracked</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-green-400">{surgingCount}</div>
              <div className="text-xs text-muted-foreground">Surging</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold">{graduatedCount}</div>
              <div className="text-xs text-muted-foreground">Graduated</div>
            </div>
            <div className="text-center">
              <div className={`text-lg font-semibold ${
                wsStatus === "connected" ? "text-green-400" : 
                wsStatus === "error" ? "text-red-400" : "text-yellow-400"
              }`}>
                {wsStatus === "connected" ? "WS" : wsStatus === "error" ? "ERR" : "PT"}
              </div>
              <div className="text-xs text-muted-foreground">WebSocket</div>
            </div>
            {newSurgeCount > 0 && (
              <div className="text-center animate-pulse">
                <div className="text-lg font-semibold text-yellow-400">+{newSurgeCount}</div>
                <div className="text-xs text-muted-foreground">New Alerts</div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Hero Stats */}
      <section className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="rounded-lg border border-border/50 bg-card p-4">
            <div className="text-xs text-muted-foreground mb-1">Total Market Cap</div>
            <div className="text-xl font-bold">
              ${totalMc.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="rounded-lg border border-border/50 bg-card p-4">
            <div className="text-xs text-muted-foreground mb-1">Surge Alerts</div>
            <div className="text-xl font-bold text-yellow-400">{surges.length}</div>
          </div>
          <div className="rounded-lg border border-border/50 bg-card p-4">
            <div className="text-xs text-muted-foreground mb-1">On Curve</div>
            <div className="text-xl font-bold">{tokens.length - graduatedCount}</div>
          </div>
          <div className="rounded-lg border border-border/50 bg-card p-4">
            <div className="text-xs text-muted-foreground mb-1">Status</div>
            <div className="text-xl font-bold flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${
                wsStatus === "connected" ? "bg-green-500" : "bg-yellow-500"
              } animate-pulse`} />
              Live
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-border/50 pb-2">
          {[
            { id: "tokens" as const, label: "Token Universe" },
            { id: "surges" as const, label: `Surge Alerts (${surges.length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                selectedTab === tab.id
                  ? "bg-primary/20 text-primary border-b-2 border-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3">
            {selectedTab === "tokens" && <TokenUniverseTable tokens={tokens} />}
            {selectedTab === "surges" && (
              <SurgeAlertPanel alerts={surges} />
            )}
          </div>
          <div className="lg:col-span-1">
            <SurgeAlertPanel alerts={surges} />
          </div>
        </div>
      </section>
    </div>
  );
}
