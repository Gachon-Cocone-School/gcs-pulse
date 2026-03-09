"use client";

import { useEffect, useReducer, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import {
  Team,
  TeamCreateRequest,
  TeamJoinRequest,
  TeamMeResponse,
  TeamRenameRequest,
  TeamLeaveResponse,
  TeamLeagueUpdateRequest,
  LeagueType,
} from "@/lib/types/auth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Copy, Users } from "lucide-react";
import { toast } from "sonner";

const LEAGUE_OPTIONS: Array<{ value: LeagueType; label: string; description: string }> = [
  { value: "undergrad", label: "학부제", description: "학부제 리그에 참여합니다." },
  { value: "semester", label: "학기제", description: "학기제 리그에 참여합니다." },
  { value: "none", label: "미참여", description: "리더보드 집계에서 제외됩니다." },
];

type TeamManagerState = {
  loading: boolean;
  submitting: boolean;
  team: Team | null;
  createName: string;
  joinCode: string;
  renameName: string;
  selectedLeague: LeagueType;
};

type TeamManagerAction =
  | { type: "FETCH_TEAM_START" }
  | { type: "FETCH_TEAM_SUCCESS"; payload: Team | null }
  | { type: "FETCH_TEAM_FAILURE" }
  | { type: "SET_SUBMITTING"; payload: boolean }
  | { type: "SET_CREATE_NAME"; payload: string }
  | { type: "SET_JOIN_CODE"; payload: string }
  | { type: "SET_RENAME_NAME"; payload: string }
  | { type: "SET_SELECTED_LEAGUE"; payload: LeagueType };

const initialState: TeamManagerState = {
  loading: true,
  submitting: false,
  team: null,
  createName: "",
  joinCode: "",
  renameName: "",
  selectedLeague: "none",
};

function reducer(state: TeamManagerState, action: TeamManagerAction): TeamManagerState {
  switch (action.type) {
    case "FETCH_TEAM_START":
      return { ...state, loading: true };
    case "FETCH_TEAM_SUCCESS":
      return {
        ...state,
        loading: false,
        team: action.payload,
        renameName: action.payload?.name ?? "",
        selectedLeague: action.payload?.league_type ?? "none",
      };
    case "FETCH_TEAM_FAILURE":
      return { ...state, loading: false };
    case "SET_SUBMITTING":
      return { ...state, submitting: action.payload };
    case "SET_CREATE_NAME":
      return { ...state, createName: action.payload };
    case "SET_JOIN_CODE":
      return { ...state, joinCode: action.payload };
    case "SET_RENAME_NAME":
      return { ...state, renameName: action.payload };
    case "SET_SELECTED_LEAGUE":
      return { ...state, selectedLeague: action.payload };
    default:
      return state;
  }
}

type UnaffiliatedTeamSectionProps = {
  createName: string;
  joinCode: string;
  submitting: boolean;
  onCreateNameChange: (value: string) => void;
  onJoinCodeChange: (value: string) => void;
  onCreateTeam: (e: FormEvent) => Promise<void>;
  onJoinTeam: (e: FormEvent) => Promise<void>;
};

function UnaffiliatedTeamSection({
  createName,
  joinCode,
  submitting,
  onCreateNameChange,
  onJoinCodeChange,
  onCreateTeam,
  onJoinTeam,
}: UnaffiliatedTeamSectionProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card className="border-border bg-card/70">
        <CardHeader>
          <CardTitle className="text-base">새 팀 만들기</CardTitle>
          <CardDescription>팀 이름으로 새 팀을 만들고 바로 참여합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onCreateTeam} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="team-name">팀 이름</Label>
              <Input
                id="team-name"
                value={createName}
                onChange={(e) => onCreateNameChange(e.target.value)}
                placeholder="예: GCS Team"
                maxLength={100}
                required
              />
            </div>
            <Button type="submit" disabled={submitting} className="w-full">
              팀 생성
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card className="border-border bg-card/70">
        <CardHeader>
          <CardTitle className="text-base">초대코드로 팀 참여</CardTitle>
          <CardDescription>초대코드를 입력해 기존 팀에 참여합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onJoinTeam} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="invite-code">초대코드</Label>
              <Input
                id="invite-code"
                value={joinCode}
                onChange={(e) => onJoinCodeChange(e.target.value)}
                placeholder="예: A1B2C3D4"
                required
              />
            </div>
            <Button type="submit" disabled={submitting} variant="outline" className="w-full">
              팀 참여
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

type CurrentTeamSectionProps = {
  team: Team;
  renameName: string;
  selectedLeague: LeagueType;
  submitting: boolean;
  onRenameNameChange: (value: string) => void;
  onSelectLeague: (league: LeagueType) => void;
  onRenameTeam: (e: FormEvent) => Promise<void>;
  onSaveLeague: () => Promise<void>;
  onLeaveTeam: () => Promise<void>;
  onCopyInviteCode: () => Promise<void>;
};

function CurrentTeamSection({
  team,
  renameName,
  selectedLeague,
  submitting,
  onRenameNameChange,
  onSelectLeague,
  onRenameTeam,
  onSaveLeague,
  onLeaveTeam,
  onCopyInviteCode,
}: CurrentTeamSectionProps) {
  return (
    <Card className="border-border bg-card/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Users className="h-4 w-4" />
          현재 팀 정보
        </CardTitle>
        <CardDescription>팀 소속 상태에서는 초대코드를 항상 조회할 수 있습니다.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">팀 이름</p>
          <p className="font-semibold text-foreground">{team.name}</p>
        </div>

        <div className="space-y-2">
          <Label>초대코드</Label>
          <div className="flex gap-2">
            <Input readOnly value={team.invite_code ?? ""} />
            <Button type="button" variant="outline" onClick={onCopyInviteCode} disabled={!team.invite_code}>
              <Copy className="h-4 w-4 mr-1" />
              복사
            </Button>
          </div>
        </div>

        <Separator />

        <form onSubmit={onRenameTeam} className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="rename-team">팀 이름 변경</Label>
            <Input
              id="rename-team"
              value={renameName}
              onChange={(e) => onRenameNameChange(e.target.value)}
              maxLength={100}
              required
            />
          </div>
          <Button type="submit" disabled={submitting} variant="outline">
            이름 변경
          </Button>
        </form>

        <Separator />

        <div className="space-y-3">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground">팀 리그 설정</p>
            <p className="text-sm text-muted-foreground">팀 소속 사용자 리더보드는 팀 리그를 기준으로 집계됩니다.</p>
          </div>

          <div className="grid gap-2">
            {LEAGUE_OPTIONS.map((option) => {
              const active = selectedLeague === option.value;
              return (
                <Button
                  key={option.value}
                  type="button"
                  variant="outline"
                  onClick={() => onSelectLeague(option.value)}
                  aria-pressed={active}
                  className={[
                    "h-auto justify-start rounded-lg px-4 py-3 text-left transition-colors",
                    active
                      ? "border-primary/40 bg-primary/10"
                      : "border-border bg-card hover:bg-muted/50",
                  ].join(" ")}
                >
                  <div>
                    <p className="text-sm font-semibold text-foreground">{option.label}</p>
                    <p className="text-xs text-muted-foreground">{option.description}</p>
                  </div>
                </Button>
              );
            })}
          </div>

          <Button
            type="button"
            onClick={onSaveLeague}
            disabled={submitting || selectedLeague === team.league_type}
          >
            팀 리그 저장
          </Button>
        </div>

        <Separator />

        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">소속 팀에서 탈퇴합니다. 마지막 팀원이 탈퇴하면 팀은 자동 삭제됩니다.</p>
          <Button type="button" variant="destructive" disabled={submitting} onClick={onLeaveTeam}>
            팀 탈퇴
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function TeamManager() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const fetchTeam = async () => {
    dispatch({ type: "FETCH_TEAM_START" });

    try {
      const data = await api.get<TeamMeResponse>("/teams/me");
      dispatch({ type: "FETCH_TEAM_SUCCESS", payload: data.team });
    } catch (error) {
      console.error("Failed to fetch team", error);
      toast.error("팀 정보를 불러오지 못했습니다");
      dispatch({ type: "FETCH_TEAM_FAILURE" });
    }
  };

  useEffect(() => {
    fetchTeam();
  }, []);

  const withRefresh = async (action: () => Promise<void>) => {
    dispatch({ type: "SET_SUBMITTING", payload: true });
    try {
      await action();
      await fetchTeam();
    } finally {
      dispatch({ type: "SET_SUBMITTING", payload: false });
    }
  };

  const handleCreateTeam = async (e: FormEvent) => {
    e.preventDefault();
    const name = state.createName.trim();
    if (!name) return;

    try {
      await withRefresh(async () => {
        await api.post<Team, TeamCreateRequest>("/teams", { name });
      });
      dispatch({ type: "SET_CREATE_NAME", payload: "" });
      toast.success("팀이 생성되었습니다");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        toast.error("다른 팀을 만들려면 먼저 현재 팀을 탈퇴해야 합니다");
        return;
      }
      if (error instanceof ApiError) {
        toast.error(error.message);
        return;
      }
      toast.error("팀 생성에 실패했습니다");
    }
  };

  const handleJoinTeam = async (e: FormEvent) => {
    e.preventDefault();
    const invite_code = state.joinCode.trim();
    if (!invite_code) return;

    try {
      await withRefresh(async () => {
        await api.post<Team, TeamJoinRequest>("/teams/join", { invite_code });
      });
      dispatch({ type: "SET_JOIN_CODE", payload: "" });
      toast.success("팀에 참여했습니다");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        toast.error("다른 팀에 참여하려면 먼저 현재 팀을 탈퇴해야 합니다");
        return;
      }
      if (error instanceof ApiError && error.status === 404) {
        toast.error("유효하지 않은 초대코드입니다");
        return;
      }
      if (error instanceof ApiError) {
        toast.error(error.message);
        return;
      }
      toast.error("팀 참여에 실패했습니다");
    }
  };

  const handleRenameTeam = async (e: FormEvent) => {
    e.preventDefault();
    const name = state.renameName.trim();
    if (!name || !state.team) return;

    try {
      await withRefresh(async () => {
        await api.patch<Team, TeamRenameRequest>("/teams/me", { name });
      });
      toast.success("팀 이름이 변경되었습니다");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
        return;
      }
      toast.error("팀 이름 변경에 실패했습니다");
    }
  };

  const handleSaveLeague = async () => {
    if (!state.team) return;

    try {
      await withRefresh(async () => {
        await api.patch<Team, TeamLeagueUpdateRequest>("/teams/me/league", {
          league_type: state.selectedLeague,
        });
      });
      toast.success("팀 리그 설정을 저장했습니다");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
        return;
      }
      toast.error("팀 리그 설정 저장에 실패했습니다");
    }
  };

  const handleLeaveTeam = async () => {
    if (!state.team) return;
    if (!confirm("정말 팀에서 탈퇴하시겠습니까?")) return;

    try {
      await withRefresh(async () => {
        await api.post<TeamLeaveResponse>("/teams/leave");
      });
      toast.success("팀에서 탈퇴했습니다");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
        return;
      }
      toast.error("팀 탈퇴에 실패했습니다");
    }
  };

  const copyInviteCode = async () => {
    if (!state.team?.invite_code) return;
    try {
      await navigator.clipboard.writeText(state.team.invite_code);
      toast.success("초대코드를 복사했습니다");
    } catch {
      toast.error("초대코드 복사에 실패했습니다");
    }
  };

  if (state.loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">팀 관리</h2>
        <p className="text-muted-foreground">팀 생성/참여/이름변경/탈퇴, 초대코드, 팀 리그 설정을 관리합니다.</p>
      </div>

      {!state.team ? (
        <UnaffiliatedTeamSection
          createName={state.createName}
          joinCode={state.joinCode}
          submitting={state.submitting}
          onCreateNameChange={(value) => dispatch({ type: "SET_CREATE_NAME", payload: value })}
          onJoinCodeChange={(value) => dispatch({ type: "SET_JOIN_CODE", payload: value })}
          onCreateTeam={handleCreateTeam}
          onJoinTeam={handleJoinTeam}
        />
      ) : (
        <CurrentTeamSection
          team={state.team}
          renameName={state.renameName}
          selectedLeague={state.selectedLeague}
          submitting={state.submitting}
          onRenameNameChange={(value) => dispatch({ type: "SET_RENAME_NAME", payload: value })}
          onSelectLeague={(league) => dispatch({ type: "SET_SELECTED_LEAGUE", payload: league })}
          onRenameTeam={handleRenameTeam}
          onSaveLeague={handleSaveLeague}
          onLeaveTeam={handleLeaveTeam}
          onCopyInviteCode={copyInviteCode}
        />
      )}
    </div>
  );
}
