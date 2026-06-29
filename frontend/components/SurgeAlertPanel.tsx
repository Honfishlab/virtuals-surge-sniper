import type { SurgeAlert } from "@/lib/api";

export interface SurgeAlertPanelProps {
  alerts: SurgeAlert[];
  onAlertClick?: (alert: SurgeAlert) => void;
}

export function SurgeAlertPanel({ alerts, onAlertClick }: SurgeAlertPanelProps) {
  if (alerts.length === 0) {
    return (
      <div className="rounded-lg border border-border/50 bg-card p-6 text-center">
        <div className="text-3xl mb-2">🔍</div>
        <h3 className="text-sm font-medium text-muted-foreground">No Active Surges</h3>
        <p className="text-xs text-muted-foreground mt-1">Monitoring for surge events...</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      <div className="px-4 py-3 border-b border-border/50">
        <h3 className="font-semibold flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-yellow-500 pulse-green" />
          Active Surges
          <span className="ml-auto text-xs text-muted-foreground">{alerts.length} alerts</span>
        </h3>
      </div>
      <div className="divide-y divide-border/30 max-h-[500px] overflow-y-auto">
        {alerts.map((alert) => (
          <button
            key={alert.token_address + alert.timestamp}
            onClick={() => onAlertClick?.(alert)}
            className="w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-medium text-sm">{alert.token_name}</span>
              <span className="text-xs text-muted-foreground">
                {new Date(alert.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                {alert.surge_type}
              </span>
              <span className="text-yellow-400 font-bold">{alert.surge_multiplier.toFixed(2)}x</span>
            </div>
            {alert.details && (
              <p className="text-xs text-muted-foreground mt-1 truncate">{alert.details}</p>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
