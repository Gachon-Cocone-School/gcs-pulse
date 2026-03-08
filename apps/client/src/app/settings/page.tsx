"use client";

import { Suspense, useEffect, useReducer } from "react";
import { TokenManager } from "@/components/views/TokenManager";
import { TeamManager } from "@/components/views/TeamManager";
import { Navigation } from "@/components/Navigation";
import { PageHeader } from "@/components/PageHeader";
import { AccessDeniedView } from "@/components/views/AccessDenied";
import { useAuth } from "@/context/auth-context";
import { redirect, usePathname, useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { hasPrivilegedRole } from "@/lib/types";
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

type LeagueState = {
  leagueLoading: boolean;
  leagueSubmitting: boolean;
  leagueInfo: MeLeagueResponse | null;
  selectedLeague: LeagueType;
};

type LeagueAction =
  | { type: "FETCH_LEAGUE_START" }
  | { type: "FETCH_LEAGUE_SUCCESS"; payload: MeLeagueResponse }
  | { type: "FETCH_LEAGUE_FAILURE" }
  | { type: "SET_SELECTED_LEAGUE"; payload: LeagueType }
  | { type: "SAVE_LEAGUE_START" }
  | { type: "SAVE_LEAGUE_SUCCESS"; payload: MeLeagueResponse }
  | { type: "SAVE_LEAGUE_FINISH" };

const initialLeagueState: LeagueState = {
  leagueLoading: false,
  leagueSubmitting: false,
  leagueInfo: null,
  selectedLeague: "none",
};

function leagueReducer(state: LeagueState, action: LeagueAction): LeagueState {
  switch (action.type) {
    case "FETCH_LEAGUE_START":
      return {
        ...state,
        leagueLoading: true,
      };
    case "FETCH_LEAGUE_SUCCESS":
      return {
        ...state,
        leagueLoading: false,
        leagueInfo: action.payload,
        selectedLeague: action.payload.league_type,
      };
    case "FETCH_LEAGUE_FAILURE":
      return {
        ...state,
        leagueLoading: false,
        leagueInfo: null,
      };
    case "SET_SELECTED_LEAGUE":
      return {
        ...state,
        selectedLeague: action.payload,
      };
    case "SAVE_LEAGUE_START":
      return {
        ...state,
        leagueSubmitting: true,
      };
    case "SAVE_LEAGUE_SUCCESS":
      return {
        ...state,
        leagueInfo: action.payload,
        selectedLeague: action.payload.league_type,
      };
    case "SAVE_LEAGUE_FINISH":
      return {
        ...state,
        leagueSubmitting: false,
      };
    default:
      return state;
  }
}

function SettingsPageContent() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const menuParam = searchParams.get("menu");
  const menu: "api" | "team" | "league" =
    menuParam === "team" || menuParam === "league" ? menuParam : "api";
  const [leagueState, leagueDispatch] = useReducer(leagueReducer, initialLeagueState);

  const handleMenuChange = (value: "api" | "team" | "league") => {
    const params = new URLSearchParams(searchParams.toString());

    if (value === "api") {
      params.delete("menu");
    } else {
      params.set("menu", value);
    }

    const queryString = params.toString();
    router.replace(queryString ? `${pathname}?${queryString}` : pathname);
  };

  const fetchMyLeague = async () => {
    leagueDispatch({ type: "FETCH_LEAGUE_START" });
    try {
      const data = await api.get<MeLeagueResponse>("/users/me/league");
      leagueDispatch({ type: "FETCH_LEAGUE_SUCCESS", payload: data });
    } catch (error) {
      console.error("Failed to fetch league settings", error);
      leagueDispatch({ type: "FETCH_LEAGUE_FAILURE" });
      toast.error("리그 설정 정보를 불러오지 못했습니다");
    }
  };

  useEffect(() => {
    if (!isAuthenticated || !hasAccess || menu !== "league") return;
    fetchMyLeague();
  }, [isAuthenticated, hasAccess, menu]);

  const handleSaveLeague = async () => {
    if (!leagueState.leagueInfo?.can_update) return;

    leagueDispatch({ type: "SAVE_LEAGUE_START" });
    try {
      const updated = await api.patch<MeLeagueResponse, MeLeagueUpdateRequest>(
        "/users/me/league",
        { league_type: leagueState.selectedLeague }
      );
      leagueDispatch({ type: "SAVE_LEAGUE_SUCCESS", payload: updated });
      toast.success("리그 설정을 저장했습니다");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("리그 설정 저장에 실패했습니다");
      }
    } finally {
      leagueDispatch({ type: "SAVE_LEAGUE_FINISH" });
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    redirect("/login");
  }

  if (!hasAccess) {
    return <AccessDeniedView reason="student-only" />;
  }

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="max-w-7xl mx-auto px-6 py-8">
        <PageHeader
          title="설정"
          description="개인/팀 설정, API 토큰을 관리합니다."
        />

        <div className="mt-8">
          <div className="glass-card p-8 rounded-xl animate-entrance">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-[220px_1fr]">
              <aside className="space-y-2">
                <p className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">설정 메뉴</p>
                <button
                  type="button"
                  onClick={() => handleMenuChange("api")}
                  className={cn(
                    "w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
                    menu === "api"
                      ? "bg-primary/10 text-primary"
                      : "text-foreground hover:bg-muted"
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
                      ? "bg-primary/10 text-primary"
                      : "text-foreground hover:bg-muted"
                  )}
                >
                  팀 설정
                </button>
                <button
                  type="button"
                  onClick={() => handleMenuChange("league")}
                  className={cn(
                    "w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
                    menu === "league"
                      ? "bg-primary/10 text-primary"
                      : "text-foreground hover:bg-muted"
                  )}
                >
                  개인 설정
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
                      <h2 className="text-2xl font-bold tracking-tight text-foreground">개인 리그 설정</h2>
                      <p className="text-muted-foreground">팀 미소속 사용자만 개인 리그를 변경할 수 있습니다.</p>
                    </div>

                    {leagueState.leagueLoading ? (
                      <div className="flex items-center gap-2 text-muted-foreground text-sm">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        리그 설정 정보를 불러오는 중입니다...
                      </div>
                    ) : !leagueState.leagueInfo ? (
                      <p className="text-sm text-destructive">리그 설정 정보를 불러오지 못했습니다.</p>
                    ) : leagueState.leagueInfo.managed_by_team ? (
                      <div className="rounded-lg border border-border bg-card/70 p-4 space-y-2">
                        <p className="text-sm text-foreground">팀 소속 사용자는 개인 리그를 변경할 수 없습니다.</p>
                        <p className="text-sm text-muted-foreground">현재 리그: {leagueTypeLabel(leagueState.leagueInfo.league_type)}</p>
                        <p className="text-sm text-muted-foreground">리그 변경은 <span className="font-semibold">팀 설정</span>에서 진행해 주세요.</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="grid gap-2">
                          {LEAGUE_OPTIONS.map((option) => {
                            const active = leagueState.selectedLeague === option.value;
                            return (
                              <button
                                key={option.value}
                                type="button"
                                onClick={() => leagueDispatch({ type: "SET_SELECTED_LEAGUE", payload: option.value })}
                                className={cn(
                                  "rounded-lg border px-4 py-3 text-left transition-colors",
                                  active
                                    ? "border-primary/40 bg-primary/10"
                                    : "border-border bg-card hover:bg-muted/50"
                                )}
                              >
                                <p className="text-sm font-semibold text-foreground">{option.label}</p>
                                <p className="text-xs text-muted-foreground">{option.description}</p>
                              </button>
                            );
                          })}
                        </div>

                        <Button
                          type="button"
                          onClick={handleSaveLeague}
                          disabled={leagueState.leagueSubmitting || leagueState.selectedLeague === leagueState.leagueInfo.league_type}
                          className="bg-primary hover:bg-primary/90 text-primary-foreground"
                        >
                          {leagueState.leagueSubmitting ? "저장 중..." : "저장"}
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
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
      }
    >
      <SettingsPageContent />
    </Suspense>
  );
}
