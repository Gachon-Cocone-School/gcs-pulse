"use client";

import { Suspense, useEffect, useReducer, useState } from "react";
import { TokenManager } from "@/components/views/TokenManager";
import { TokenUsageView } from "@/components/views/TokenUsageView";
import { TeamManager } from "@/components/views/TeamManager";
import { ThemeSettings } from "@/components/views/ThemeSettings";
import { Navigation } from "@/components/Navigation";
import { PageHeader } from "@/components/PageHeader";
import { useAuth } from "@/context/auth-context";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { hasPrivilegedRole, hasTokenRole } from "@/lib/types";
import type { LeagueType, MeLeagueResponse, MeLeagueUpdateRequest } from "@/lib/types/auth";
import { LeagueSelector } from "@/components/views/LeagueSelector";
import { toast } from "sonner";

const SETTINGS_MENUS = [
  { value: "theme", label: "테마 설정" },
  { value: "team", label: "팀 관리" },
  { value: "league", label: "개인 관리" },
  { value: "api", label: "API 키" },
  { value: "token-usage", label: "토큰 사용량" },
] as const;

const THEME_ONLY_MENU = SETTINGS_MENUS.filter((item) => item.value === "theme");
const TOKEN_MENU_VALUES = new Set(["token-usage"]);

type SettingsMenu = (typeof SETTINGS_MENUS)[number]["value"];

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
  const isToken = hasTokenRole(user?.roles);
  const router = useRouter();
  const pathname = usePathname();
  const [menu, setMenu] = useState<SettingsMenu>("theme");
  const [leagueState, leagueDispatch] = useReducer(leagueReducer, initialLeagueState);

  useEffect(() => {
    const syncMenuFromLocation = () => {
      const menuParam = new URLSearchParams(window.location.search).get("menu");
      const isValidMenu = SETTINGS_MENUS.some(({ value }) => value === menuParam);

      if (!hasAccess) {
        setMenu("theme");
        return;
      }

      setMenu(isValidMenu ? (menuParam as SettingsMenu) : "theme");
    };

    syncMenuFromLocation();
    window.addEventListener("popstate", syncMenuFromLocation);

    return () => {
      window.removeEventListener("popstate", syncMenuFromLocation);
    };
  }, [hasAccess]);

  const handleMenuChange = (value: SettingsMenu) => {
    if (!hasAccess && value !== "theme") return;

    const params = new URLSearchParams(window.location.search);

    if (value === "theme") {
      params.delete("menu");
    } else {
      params.set("menu", value);
    }

    const queryString = params.toString();
    router.replace(queryString ? `${pathname}?${queryString}` : pathname);
    setMenu(value);
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

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="max-w-7xl mx-auto px-6 py-8">
        <PageHeader
          title="설정"
          description="테마 설정, 개인/팀 설정, API 토큰을 관리합니다."
        />

        <div className="mt-8">
          <div className="glass-card p-8 rounded-xl animate-entrance">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-[220px_1fr]">
              <aside className="space-y-2">
                <p className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">설정 메뉴</p>
                {(hasAccess ? SETTINGS_MENUS : THEME_ONLY_MENU).filter((item) => !TOKEN_MENU_VALUES.has(item.value) || isToken).map((item) => (
                  <Button
                    key={item.value}
                    type="button"
                    variant="ghost"
                    onClick={() => handleMenuChange(item.value)}
                    className={cn(
                      "w-full justify-start rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
                      menu === item.value
                        ? "border-[var(--sys-current-border)] bg-[var(--sys-current-bg)] text-[var(--sys-current-fg)] shadow-sm"
                        : "text-foreground hover:bg-muted"
                    )}
                  >
                    {item.label}
                  </Button>
                ))}
              </aside>

              <section>
                {menu === "theme" && <ThemeSettings />}
                {hasAccess && menu === "team" && <TeamManager />}
                {hasAccess && menu === "api" && <TokenManager />}
                {isToken && menu === "token-usage" && <TokenUsageView />}
                {hasAccess && menu === "league" && (
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
                        <LeagueSelector
                          selectedLeague={leagueState.selectedLeague}
                          onSelect={(league) => leagueDispatch({ type: "SET_SELECTED_LEAGUE", payload: league })}
                        />

                        <Button
                          type="button"
                          onClick={handleSaveLeague}
                          disabled={leagueState.leagueSubmitting || leagueState.selectedLeague === leagueState.leagueInfo.league_type}
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
