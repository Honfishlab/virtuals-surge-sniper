import type { TokenData } from "@/lib/api";

export interface TokenUniverseTableProps {
  tokens: TokenData[];
}

export function TokenUniverseTable({ tokens }: TokenUniverseTableProps) {
  const [sortBy, setSortBy] = useState<"alpha_score" | "surge_multiplier" | "age_days" | "bonding_progress">("alpha_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filter, setFilter] = useState<"all" | "surging" | "graduated">("all");
  const [search, setSearch] = useState("");

  const sorted = useMemo(() => {
    let result = [...tokens];

    if (filter === "surging") result = result.filter((t) => t.surge.is_surging);
    if (filter === "graduated") result = result.filter((t) => t.token_type === "graduated");
    if (search) {
      const s = search.toLowerCase();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(s) ||
          t.symbol.toLowerCase().includes(s) ||
          t.address.toLowerCase().includes(s),
      );
    }

    result.sort((a, b) => {
      let aVal: number, bVal: number;
      if (sortBy === "alpha_score") {
        aVal = a.alpha_score.overall_score;
        bVal = b.alpha_score.overall_score;
      } else if (sortBy === "surge_multiplier") {
        aVal = a.surge.overall_surge_score;
        bVal = b.surge.overall_surge_score;
      } else if (sortBy === "age_days") {
        aVal = a.age_days;
        bVal = b.age_days;
      } else {
        aVal = a.bonding.progress_percent;
        bVal = b.bonding.progress_percent;
      }
      return sortDir === "desc" ? bVal - aVal : aVal - bVal;
    });

    return result;
  }, [tokens, sortBy, sortDir, filter, search]);

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Search by name, symbol, or address..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-[200px] rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <div className="flex gap-1 bg-muted/50 p-1 rounded-md">
          {(["all", "surging", "graduated"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                filter === f ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f === "all" ? "All" : f === "surging" ? "Surging" : "Graduated"}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-border/50">
        <table className="w-full text-sm">
          <thead className="bg-muted/30">
            <tr>
              {[
                { key: "name" as const, label: "Token" },
                { key: "age_days" as const, label: "Age" },
                { key: "bonding_progress" as const, label: "Bonding %" },
                { key: "alpha_score" as const, label: "Alpha" },
                { key: "surge_multiplier" as const, label: "Surge" },
                { key: "usage" as const, label: "Jobs (24h)" },
                { key: "bonding_value" as const, label: "Bonded VIRTUAL" },
              ].map(({ key, label }) => (
                <th
                  key={key}
                  onClick={() => {
                    if (sortBy === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                    else {
                      setSortBy(key);
                      setSortDir("desc");
                    }
                  }}
                  className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground transition-colors whitespace-nowrap"
                >
                  {label}
                  {sortBy === key ? (sortDir === "desc" ? " \u2193" : " \u2191") : ""}
                </th>
              ))}
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/30">
            {sorted.map((token) => (
              <TokenRow key={token.address} token={token} onSnipe={() => console.log("Snipe:", token.address)} />
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                  No tokens found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Individual row component
function TokenRow({
  token,
  onSnipe,
}: {
  token: TokenData;
  onSnipe: () => void;
}) {
  return (
    <tr className="hover:bg-muted/20 transition-colors">
      <td className="px-4 py-3">
        <div className="font-medium">{token.name}</div>
        <div className="text-xs text-muted-foreground">{token.symbol} · {token.address.slice(0, 8)}...</div>
      </td>
      <td className="px-4 py-3 text-muted-foreground">
        {token.age_days >= 1 ? `${Math.round(token.age_days)}d` : `${Math.round(token.age_days * 24)}h`}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full"
              style={{ width: `${Math.min(token.bonding.progress_percent, 100)}%` }}
            />
          </div>
          <span className="text-xs font-medium">{token.bonding.progress_percent}%</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${
            token.alpha_score.overall_score >= 80
              ? "bg-green-500/20 text-green-400"
              : token.alpha_score.overall_score >= 60
                ? "bg-yellow-500/20 text-yellow-400"
                : "bg-muted text-muted-foreground"
          }`}
        >
          {Math.round(token.alpha_score.overall_score)}
        </span>
      </td>
      <td className="px-4 py-3">
        {token.surge.is_surging ? (
          <span className="text-yellow-400 font-bold pulse-green">
            {token.surge.overall_surge_score.toFixed(1)}x
          </span>
        ) : (
          <span className="text-muted-foreground">{token.surge.overall_surge_score.toFixed(1)}x</span>
        )}
      </td>
      <td className="px-4 py-3">{token.usage.acp_jobs_24h.toLocaleString()}</td>
      <td className="px-4 py-3 font-medium">{token.bonding.bonding_value_virtual.toLocaleString()}</td>
      <td className="px-4 py-3 text-right">
        <button
          onClick={onSnipe}
          className="inline-flex items-center px-3 py-1.5 bg-primary text-primary-foreground rounded-md text-xs font-medium hover:bg-primary/90 transition-colors"
        >
          Snipe
        </button>
      </td>
    </tr>
  );
}
