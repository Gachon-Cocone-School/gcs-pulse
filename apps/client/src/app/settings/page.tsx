"use client";

import { Suspense, useEffect, useState } from "react";
import { TokenManager } from "@/components/views/TokenManager";
import { TeamManager } from "@/components/views/TeamManager";
import { Navigation } from "@/components/Navigation";
import { PageHeader } from "@/components/PageHeader";
import { useAuth } from "@/context/auth-context";
import { redirect, usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import type { LeagueType, MeLeagueResponse, MeLeagueUpdateRequest } from "@/lib/types/auth";
import { toast } from "sonner";

const LEAGUE_OPTIONS: Array<{ value: LeagueType; label: string; description: string }> = [
  { value: "undergrad", label: "학부제", description: "학부제 리그에 참여합니다." },
  { value: "semester", label: "학기제", description: "학기제 리그에 참여합니다." },
  { value: "none", label: "미참여", description: "리더보드 집계에서 제외됩니다." },
];

function leagueTypeLabel(value: LeagueType) {
  if (value === "undergrad") return "학부제";
  if (value === "semester") return "학기제";
  return "미참여";
}

function SettingsPageContent() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menu, setMenu] = useState<"api" | "team" | "league">("api");
  const [leagueLoading, setLeagueLoading] = useState(false);
  const [leagueSubmitting, setLeagueSubmitting] = useState(false);
  const [leagueInfo, setLeagueInfo] = useState<MeLeagueResponse | null>(null);
  const [selectedLeague, setSelectedLeague] = useState<LeagueType>("none");

  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncMenuFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      const menuParam = params.get("menu");
      const nextMenu = menuParam === "team" || menuParam === "league" ? menuParam : "api";
      setMenu(nextMenu);
    };

    syncMenuFromUrl();
    window.addEventListener("popstate", syncMenuFromUrl);

    return () => {
      window.removeEventListener("popstate", syncMenuFromUrl);
    };
  }, []);

  const handleMenuChange = (value: "api" | "team" | "league") => {
    const params = new URLSearchParams(window.location.search);

    if (value === "api") {
      params.delete("menu");
    } else {
      params.set("menu", value);
    }

    const queryString = params.toString();
    router.replace(queryString ? `${pathname}?${queryString}` : pathname);
    setMenu(value);
  };

  const fetchMyLeague = async () => {
    setLeagueLoading(true);
    try {
      const data = await api.get<MeLeagueResponse>("/users/me/league");
      setLeagueInfo(data);
      setSelectedLeague(data.league_type);
    } catch (error) {
      console.error("Failed to fetch league settings", error);
      setLeagueInfo(null);
      toast.error("리그 설정 정보를 불러오지 못했습니다");
    } finally {
      setLeagueLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated || menu !== "league") return;
    fetchMyLeague();
  }, [isAuthenticated, menu]);

  const handleSaveLeague = async () => {
    if (!leagueInfo?.can_update) return;

    setLeagueSubmitting(true);
    try {
      const updated = await api.patch<MeLeagueResponse, MeLeagueUpdateRequest>(
        "/users/me/league",
        { league_type: selectedLeague }
      );
      setLeagueInfo(updated);
      setSelectedLeague(updated.league_type);
      toast.success("리그 설정을 저장했습니다");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("리그 설정 저장에 실패했습니다");
      }
    } finally {
      setLeagueSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen bg-slate-50 bg-mesh">
      <Navigation />
      <main className="max-w-7xl mx-auto px-6 py-8">
        <PageHeader
          title="설정"
          description="계정 설정, 리그, API 액세스를 관리합니다."
        />

        <div className="mt-8">
          <div className="glass-card p-8 rounded-xl animate-entrance">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-[220px_1fr]">
              <aside className="space-y-2">
                <p className="text-xs font-semibold tracking-wider text-slate-500 uppercase">설정 메뉴</p>
                <button
                  type="button"
                  onClick={() => handleMenuChange("api")}
                  className={cn(
                    "w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
                    menu === "api"
                      ? "bg-rose-50 text-rose-700"
                      : "text-slate-700 hover:bg-slate-100"
                  )}
                >
                  API 키
                </button>
                <button
                  type="button"
                  onClick={() => handleMenuChange("team")}
                  className={cn(
                    "w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
                    menu === "team"
                      ? "bg-rose-50 text-rose-700"
                      : "text-slate-700 hover:bg-slate-100"
                  )}
                >
                  팀 관리
                </button>
                <button
                  type="button"
                  onClick={() => handleMenuChange("league")}
                  className={cn(
                    "w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
                    menu === "league"
                      ? "bg-rose-50 text-rose-700"
                      : "text-slate-700 hover:bg-slate-100"
                  )}
                >
                  개인 리그
                </button>
              </aside>

              <section>
                {menu === "api" ? (
                  <TokenManager />
                ) : menu === "team" ? (
                  <TeamManager />
                ) : (
                  <div className="space-y-5">
                    <div>
                      <h2 className="text-2xl font-bold tracking-tight text-slate-900">개인 리그 설정</h2>
                      <p className="text-slate-600">팀 미소속 사용자만 개인 리그를 변경할 수 있습니다.</p>
                    </div>

                    {leagueLoading ? (
                      <div className="flex items-center gap-2 text-slate-500 text-sm">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        리그 설정 정보를 불러오는 중입니다...
                      </div>
                    ) : !leagueInfo ? (
                      <p className="text-sm text-rose-600">리그 설정 정보를 불러오지 못했습니다.</p>
                    ) : leagueInfo.managed_by_team ? (
                      <div className="rounded-lg border border-slate-200 bg-white/70 p-4 space-y-2">
                        <p className="text-sm text-slate-700">팀 소속 사용자는 개인 리그를 변경할 수 없습니다.</p>
                        <p className="text-sm text-slate-600">현재 리그: {leagueTypeLabel(leagueInfo.league_type)}</p>
                        <p className="text-sm text-slate-600">리그 변경은 <span className="font-semibold">팀 관리</span>에서 진행해 주세요.</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="grid gap-2">
                          {LEAGUE_OPTIONS.map((option) => {
                            const active = selectedLeague === option.value;
                            return (
                              <button
                                key={option.value}
                                type="button"
                                onClick={() => setSelectedLeague(option.value)}
                                className={cn(
                                  "rounded-lg border px-4 py-3 text-left transition-colors",
                                  active
                                    ? "border-rose-300 bg-rose-50"
                                    : "border-slate-200 bg-white hover:bg-slate-50"
                                )}
                              >
                                <p className="text-sm font-semibold text-slate-900">{option.label}</p>
                                <p className="text-xs text-slate-500">{option.description}</p>
                              </button>
                            );
                          })}
                        </div>

                        <Button
                          type="button"
                          onClick={handleSaveLeague}
                          disabled={leagueSubmitting || selectedLeague === leagueInfo.league_type}
                          className="bg-rose-500 hover:bg-rose-600 text-white"
                        >
                          {leagueSubmitting ? "저장 중..." : "저장"}
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center items-center min-h-[50vh]">
          <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
        </div>
      }
    >
      <SettingsPageContent />
    </Suspense>
  );
}
