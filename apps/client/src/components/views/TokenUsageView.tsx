"use client";

import { useEffect, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { TokenUsageResponse } from "@/lib/types/auth";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function formatNumber(n: number) {
  return n.toLocaleString("ko-KR");
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatCountdown(iso: string) {
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return "곧 리셋";
  const h = Math.floor(diff / 3_600_000);
  const m = Math.floor((diff % 3_600_000) / 60_000);
  if (h > 0) return `${h}시간 ${m}분 후`;
  return `${m}분 후`;
}

function UsageRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}

function ProgressBar({ used, total, className }: { used: number; total: number; className?: string }) {
  const pct = total > 0 ? Math.min((used / total) * 100, 100) : 0;
  const danger = pct >= 90;
  const warn = pct >= 70;
  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>사용량</span>
        <span>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            danger ? "bg-destructive" : warn ? "bg-yellow-500" : "bg-primary"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function TokenUsageView() {
  const [data, setData] = useState<TokenUsageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<TokenUsageResponse>("/users/me/token-usage");
      setData(res);
    } catch {
      setError("토큰 사용량 정보를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetch(); }, []);

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">토큰 사용량</h2>
          <p className="text-muted-foreground">AI 토큰 사용 현황과 리셋 주기를 확인합니다.</p>
        </div>
        <Button variant="ghost" size="sm" onClick={fetch} disabled={loading} className="mt-1">
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
        </Button>
      </div>

      {loading && !data && (
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          불러오는 중...
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      {data && (
        <div className="grid gap-4 sm:grid-cols-2">
          {/* Short 카드 */}
          <div className="rounded-lg border border-border bg-card/70 p-5 space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">단기 (5시간)</p>
            </div>
            <ProgressBar used={data.short.used} total={data.short.allocated} />
            <div className="space-y-2">
              <UsageRow label="할당 쿼터" value={formatNumber(data.short.allocated)} />
              <UsageRow label="사용량" value={formatNumber(data.short.used)} />
              <UsageRow label="남은 쿼터" value={formatNumber(data.short.remaining)} />
              <UsageRow label="마지막 리셋" value={formatDateTime(data.short.last_reset)} />
              <UsageRow label="다음 리셋" value={`${formatDateTime(data.short.next_reset)} (${formatCountdown(data.short.next_reset)})`} />
            </div>
          </div>

          {/* Weekly 카드 */}
          <div className="rounded-lg border border-border bg-card/70 p-5 space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">주간 (매주 월요일)</p>
            </div>
            <ProgressBar used={data.weekly.total_used} total={data.weekly.total_quota} />
            <div className="space-y-2">
              <UsageRow label="전체 쿼터" value={formatNumber(data.weekly.total_quota)} />
              <UsageRow label="전체 사용량" value={formatNumber(data.weekly.total_used)} />
              <UsageRow label="전체 남은 쿼터" value={formatNumber(data.weekly.total_remaining)} />
              <UsageRow label="인당 5시간 할당" value={formatNumber(data.weekly.per_user_allocated)} />
              <UsageRow label="마지막 리셋" value={formatDateTime(data.weekly.last_reset)} />
              <UsageRow label="다음 리셋" value={`${formatDateTime(data.weekly.next_reset)} (${formatCountdown(data.weekly.next_reset)})`} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
