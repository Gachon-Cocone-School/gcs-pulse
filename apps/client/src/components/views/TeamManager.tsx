"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
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
import { ApiError } from "@/lib/api";

const LEAGUE_OPTIONS: Array<{ value: LeagueType; label: string; description: string }> = [
  { value: "undergrad", label: "학부제", description: "학부제 리그에 참여합니다." },
  { value: "semester", label: "학기제", description: "학기제 리그에 참여합니다." },
  { value: "none", label: "미참여", description: "리더보드 집계에서 제외됩니다." },
];

export function TeamManager() {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [team, setTeam] = useState<Team | null>(null);
  const [createName, setCreateName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [renameName, setRenameName] = useState("");
  const [selectedLeague, setSelectedLeague] = useState<LeagueType>("none");

  const fetchTeam = async () => {
    setLoading(true);
    try {
      const data = await api.get<TeamMeResponse>("/teams/me");
      setTeam(data.team);
      setRenameName(data.team?.name ?? "");
      setSelectedLeague(data.team?.league_type ?? "none");
    } catch (error) {
      console.error("Failed to fetch team", error);
      toast.error("팀 정보를 불러오지 못했습니다");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeam();
  }, []);

  const withRefresh = async (action: () => Promise<void>) => {
    setSubmitting(true);
    try {
      await action();
      await fetchTeam();
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = createName.trim();
    if (!name) return;

    try {
      await withRefresh(async () => {
        await api.post<Team, TeamCreateRequest>("/teams", { name });
      });
      setCreateName("");
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

  const handleJoinTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    const invite_code = joinCode.trim();
    if (!invite_code) return;

    try {
      await withRefresh(async () => {
        await api.post<Team, TeamJoinRequest>("/teams/join", { invite_code });
      });
      setJoinCode("");
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

  const handleRenameTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = renameName.trim();
    if (!name || !team) return;

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
    if (!team) return;

    try {
      await withRefresh(async () => {
        await api.patch<Team, TeamLeagueUpdateRequest>("/teams/me/league", {
          league_type: selectedLeague,
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
    if (!team) return;
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
    if (!team?.invite_code) return;
    try {
      await navigator.clipboard.writeText(team.invite_code);
      toast.success("초대코드를 복사했습니다");
    } catch (error) {
      toast.error("초대코드 복사에 실패했습니다");
    }
  };

  if (loading) {
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
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">팀 관리</h2>
        <p className="text-slate-600">팀 생성/참여/이름변경/탈퇴, 초대코드, 팀 리그 설정을 관리합니다.</p>
      </div>

      {!team ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="border-slate-200 bg-white/70">
            <CardHeader>
              <CardTitle className="text-base">새 팀 만들기</CardTitle>
              <CardDescription>팀 이름으로 새 팀을 만들고 바로 참여합니다.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateTeam} className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="team-name">팀 이름</Label>
                  <Input
                    id="team-name"
                    value={createName}
                    onChange={(e) => setCreateName(e.target.value)}
                    placeholder="예: GCS Team"
                    maxLength={100}
                    required
                  />
                </div>
                <Button type="submit" disabled={submitting} className="w-full bg-rose-500 hover:bg-rose-600 text-white">
                  팀 생성
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="border-slate-200 bg-white/70">
            <CardHeader>
              <CardTitle className="text-base">초대코드로 팀 참여</CardTitle>
              <CardDescription>초대코드를 입력해 기존 팀에 참여합니다.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleJoinTeam} className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="invite-code">초대코드</Label>
                  <Input
                    id="invite-code"
                    value={joinCode}
                    onChange={(e) => setJoinCode(e.target.value)}
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
      ) : (
        <Card className="border-slate-200 bg-white/70">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4" />
              현재 팀 정보
            </CardTitle>
            <CardDescription>팀 소속 상태에서는 초대코드를 항상 조회할 수 있습니다.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-1">
              <p className="text-sm text-slate-500">팀 이름</p>
              <p className="font-semibold text-slate-900">{team.name}</p>
            </div>

            <div className="space-y-2">
              <Label>초대코드</Label>
              <div className="flex gap-2">
                <Input readOnly value={team.invite_code ?? ""} className="font-mono" />
                <Button type="button" variant="outline" onClick={copyInviteCode} disabled={!team.invite_code}>
                  <Copy className="h-4 w-4 mr-1" />
                  복사
                </Button>
              </div>
            </div>

            <Separator />

            <form onSubmit={handleRenameTeam} className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="rename-team">팀 이름 변경</Label>
                <Input
                  id="rename-team"
                  value={renameName}
                  onChange={(e) => setRenameName(e.target.value)}
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
                <p className="text-sm font-semibold text-slate-900">팀 리그 설정</p>
                <p className="text-sm text-slate-500">팀 소속 사용자 리더보드는 팀 리그를 기준으로 집계됩니다.</p>
              </div>

              <div className="grid gap-2">
                {LEAGUE_OPTIONS.map((option) => {
                  const active = selectedLeague === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSelectedLeague(option.value)}
                      className={[
                        "rounded-lg border px-4 py-3 text-left transition-colors",
                        active
                          ? "border-rose-300 bg-rose-50"
                          : "border-slate-200 bg-white hover:bg-slate-50",
                      ].join(" ")}
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
                disabled={submitting || selectedLeague === team.league_type}
                className="bg-rose-500 hover:bg-rose-600 text-white"
              >
                팀 리그 저장
              </Button>
            </div>

            <Separator />

            <div className="space-y-2">
              <p className="text-sm text-slate-500">소속 팀에서 탈퇴합니다. 마지막 팀원이 탈퇴하면 팀은 자동 삭제됩니다.</p>
              <Button type="button" variant="destructive" disabled={submitting} onClick={handleLeaveTeam}>
                팀 탈퇴
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
