"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";
import { Input } from "@/components/Input";
import {
  Users,
  Search,
  Edit2,
  Trash2,
  Plus,
  Check,
  X,
  UserPlus,
  UserMinus,
  Loader2,
} from "lucide-react";

interface TeamMember {
  id: number;
  name: string;
  email: string;
  picture: string;
}

interface Team {
  id: number;
  name: string;
  created_at: string;
  members: TeamMember[];
}

export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const [isCreating, setIsCreating] = useState(false);
  const [newTeamName, setNewTeamName] = useState("");

  const [editingTeam, setEditingTeam] = useState<Team | null>(null);
  const [editTeamName, setEditTeamName] = useState("");

  const [managingMembersTeam, setManagingMembersTeam] = useState<Team | null>(
    null
  );
  const [memberSearchQuery, setMemberSearchQuery] = useState("");
  const [userSearchResults, setUserSearchResults] = useState<TeamMember[]>([]);

  const fetchTeams = async () => {
    try {
      const data = await api.get<Team[]>("/admin/teams");
      setTeams(data);
    } catch (error) {
      console.error("Failed to fetch teams:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  const handleCreate = async () => {
    if (!newTeamName.trim()) return;
    try {
      await api.post("/admin/teams", { name: newTeamName });
      setNewTeamName("");
      setIsCreating(false);
      fetchTeams();
    } catch (error) {
      alert("팀 생성에 실패했습니다.");
    }
  };

  const handleUpdate = async () => {
    if (!editingTeam || !editTeamName.trim()) return;
    try {
      await api.put(`/admin/teams/${editingTeam.id}`, { name: editTeamName });
      setEditingTeam(null);
      setEditTeamName("");
      fetchTeams();
    } catch (error) {
      alert("팀 수정에 실패했습니다.");
    }
  };

  const handleSearchUsers = async (query: string) => {
    setMemberSearchQuery(query);
    if (query.length < 2) {
      setUserSearchResults([]);
      return;
    }
    try {
      const users = await api.get<any[]>(
        `/admin/users?q=${encodeURIComponent(query)}`
      );

      setUserSearchResults(
        users.map((u) => ({
          id: u.id,
          name: u.name || "이름 없음",
          email: u.email,
          picture: u.picture || "",
        }))
      );
    } catch (error) {
      console.error("User search failed", error);
    }
  };

  const handleAddMember = async (teamId: number, userId: number) => {
    try {
      await api.post(`/admin/teams/${teamId}/members/${userId}`);
      setMemberSearchQuery("");
      setUserSearchResults([]);
      
      // Parallelize refreshing the list and the current managing team
      await Promise.all([
        fetchTeams(),
        (async () => {
          const updatedTeam = await api.get<Team>(`/admin/teams/${teamId}`);
          setManagingMembersTeam(updatedTeam);
        })()
      ]);
    } catch (error) {
      alert("멤버 추가에 실패했습니다.");
    }
  };

  const handleRemoveMember = async (teamId: number, userId: number) => {
    if (!confirm("팀에서 제외하시겠습니까?")) return;
    try {
      await api.delete(`/admin/teams/${teamId}/members/${userId}`);
      
      // Parallelize refreshing the list and the current managing team
      await Promise.all([
        fetchTeams(),
        (async () => {
          const updatedTeam = await api.get<Team>(`/admin/teams/${teamId}`);
          setManagingMembersTeam(updatedTeam);
        })()
      ]);
    } catch (error) {
      alert("멤버 제외에 실패했습니다.");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("정말 이 팀을 삭제하시겠습니까?")) return;
    try {
      await api.delete(`/admin/teams/${id}`);
      fetchTeams();
    } catch (error) {
      alert("팀 삭제에 실패했습니다.");
    }
  };

  const filteredTeams = teams.filter((t) =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredMembers = managingMembersTeam
    ? managingMembersTeam.members.filter(
        (m) =>
          m.name.toLowerCase().includes(memberSearchQuery.toLowerCase()) ||
          m.email.toLowerCase().includes(memberSearchQuery.toLowerCase())
      )
    : [];

  if (loading)
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
        <p className="text-slate-500 font-medium">팀 목록을 불러오는 중…</p>
      </div>
    );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight mb-0">
            팀 관리
          </h2>
        </div>
        <Button onClick={() => setIsCreating(true)} className="gap-2">
          <Plus className="w-4 h-4" /> 팀 생성
        </Button>
      </div>

      {isCreating && (
        <Card className="animate-in slide-in-from-top-2 duration-300 border-primary-200 ring-4 ring-primary-50">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                새로운 팀 이름
              </label>
              <Input
                autoFocus
                value={newTeamName}
                onChange={(e) => setNewTeamName(e.target.value)}
                placeholder="예: 마케팅팀, 개발 1팀…"
                className="bg-white"
              />
            </div>
            <div className="flex items-end gap-2 h-full pb-0.5">
              <Button
                onClick={() => setIsCreating(false)}
                variant="ghost"
                size="sm"
              >
                취소
              </Button>
              <Button onClick={handleCreate} disabled={!newTeamName.trim()}>
                생성하기
              </Button>
            </div>
          </div>
        </Card>
      )}

      <div className="bg-white border border-slate-100 shadow-sm flex items-center px-4 gap-3 h-10 group focus-within:border-primary-400 transition-all rounded-xl">
        <Search className="w-4 h-4 text-slate-300 group-focus-within:text-primary-500 transition-colors shrink-0" />
        <input
          type="text"
          placeholder="팀 이름으로 검색…"
          aria-label="팀 검색"
          className="w-full bg-transparent outline-none font-medium text-slate-600 placeholder:text-slate-300 border-none ring-0 focus:ring-0 text-sm"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-1 gap-3">
        {filteredTeams.length > 0 ? (
          filteredTeams.map((team) => (
            <div key={team.id} className="w-full">
              <Card
                padding="lg"
                className={`w-full flex items-center justify-between border border-slate-100 transition-all group overflow-hidden ${
                  editingTeam?.id === team.id
                    ? "rounded-b-none border-b-0 shadow-none ring-1 ring-primary-100 relative z-10"
                    : "hover:border-primary-100"
                }`}
              >
                <div className="flex items-center gap-4">
                    <div>
                        <h6 className="font-bold text-base text-slate-900 mb-0.5">
                          {team.name}
                        </h6>
                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <Users className="w-3 h-3" /> {team.members.length}명
                          </span>
                          <span className="w-0.5 h-0.5 rounded-full bg-slate-300" />
                          <span>
                            생성일:{" "}
                            {new Date(team.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                  </div>

                  <div className="flex items-center gap-2 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        if (managingMembersTeam?.id === team.id) {
                          setManagingMembersTeam(null);
                          setMemberSearchQuery("");
                          setUserSearchResults([]);
                        } else {
                          setManagingMembersTeam(team);
                          setEditingTeam(null);
                        }
                      }}
                      className={`gap-2 transition-all ${
                        managingMembersTeam?.id === team.id
                          ? "text-indigo-600 bg-indigo-50"
                          : "text-slate-400 hover:text-indigo-600 hover:bg-indigo-50"
                      }`}
                    >
                      <UserPlus className="w-3.5 h-3.5" /> 멤버 관리
                    </Button>
                    <div className="w-px h-3 bg-slate-200 mx-1" />
                    <button
                      onClick={() => {
                        if (editingTeam?.id === team.id) {
                          setEditingTeam(null);
                          setEditTeamName("");
                        } else {
                          setEditingTeam(team);
                          setEditTeamName(team.name);
                        }
                      }}
                      className={`p-2 rounded-md transition-all ${
                        editingTeam?.id === team.id
                          ? "bg-primary-500 text-white shadow-sm"
                          : "text-slate-400 hover:text-primary-600 hover:bg-primary-50"
                      }`}
                      aria-label={`${team.name} 팀 수정`}
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(team.id)}
                      className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-all"
                      aria-label={`${team.name} 팀 삭제`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
              </Card>

              {editingTeam?.id === team.id && (
                <div className="w-full animate-in slide-in-from-top-1 duration-200">
                  <div className="bg-slate-50/50 border-x border-primary-100 border-b border-primary-100 rounded-b-xl border-t-0 p-5 space-y-4 ring-1 ring-primary-100 ring-t-0 relative z-0">
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1 mb-2">
                        팀 이름 수정
                      </label>
                      <div className="flex gap-2">
                        <Input
                          value={editTeamName}
                          onChange={(e) => setEditTeamName(e.target.value)}
                          className="bg-white"
                        />
                        <Button onClick={handleUpdate} className="gap-2">
                          <Check className="w-4 h-4" /> 저장
                        </Button>
                        <Button
                          variant="ghost"
                          onClick={() => setEditingTeam(null)}
                        >
                          취소
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {managingMembersTeam?.id === team.id && (
                <div className="w-full animate-in slide-in-from-top-1 duration-200">
                  <div className="bg-slate-50/50 border-x border-indigo-100 border-b border-indigo-100 rounded-b-xl border-t-0 p-5 space-y-6 ring-1 ring-indigo-100 ring-t-0 relative z-0">
                    <div className="flex justify-between items-center mb-2">
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">
                        멤버 관리 ({managingMembersTeam.members.length}명)
                      </label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setManagingMembersTeam(null)}
                      >
                        닫기
                      </Button>
                    </div>

                    <div className="relative">
                      <div className="flex gap-2">
                        <div className="flex-1 bg-white border border-slate-100 shadow-sm flex items-center px-4 gap-3 h-10 group focus-within:border-primary-400 transition-all rounded-xl">
                          <Search className="w-4 h-4 text-slate-300 group-focus-within:text-primary-500 transition-colors shrink-0" />
                          <input
                            type="text"
                            placeholder="사용자 검색 (이름, 이메일)…"
                            aria-label="사용자 검색"
                            className="w-full bg-transparent outline-none font-medium text-slate-600 placeholder:text-slate-300 border-none ring-0 focus:ring-0 text-sm"
                            value={memberSearchQuery}
                            onChange={(e) => handleSearchUsers(e.target.value)}
                          />
                        </div>
                      </div>

                      {userSearchResults.length > 0 && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-20 max-h-60 overflow-y-auto">
                          {userSearchResults.map((user) => {
                            const isMember = managingMembersTeam.members.some(
                              (m) => m.id === user.id
                            );
                            return (
                              <div
                                key={user.id}
                                className="flex items-center justify-between p-3 hover:bg-slate-50 border-b border-slate-100 last:border-0"
                              >
                                <div className="flex items-center gap-3">
                                  {user.picture ? (
                                    <img
                                      src={user.picture}
                                      alt=""
                                      className="w-8 h-8 rounded-full"
                                    />
                                  ) : (
                                    <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
                                      <Users className="w-4 h-4 text-slate-400" />
                                    </div>
                                  )}
                                  <div>
                                    <p className="text-sm font-medium text-slate-900">
                                      {user.name}
                                    </p>
                                    <p className="text-xs text-slate-500">
                                      {user.email}
                                    </p>
                                  </div>
                                </div>
                                <Button
                                  size="sm"
                                  disabled={isMember}
                                  variant={isMember ? "ghost" : "primary"}
                                  onClick={() =>
                                    !isMember &&
                                    handleAddMember(
                                      managingMembersTeam.id,
                                      user.id
                                    )
                                  }
                                >
                                  {isMember ? "이미 멤버임" : "추가"}
                                </Button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      {filteredMembers.length > 0 ? (
                        filteredMembers.map((member) => (
                          <div
                            key={member.id}
                            className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-lg"
                          >
                            <div className="flex items-center gap-3">
                              {member.picture ? (
                                <img
                                  src={member.picture}
                                  alt=""
                                  className="w-8 h-8 rounded-full"
                                />
                              ) : (
                                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
                                  <Users className="w-4 h-4 text-slate-400" />
                                </div>
                              )}
                              <div>
                                <p className="text-sm font-medium text-slate-900">
                                  {member.name}
                                </p>
                                <p className="text-xs text-slate-500">
                                  {member.email}
                                </p>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-rose-500 hover:bg-rose-50 hover:text-rose-600"
                              onClick={() =>
                                handleRemoveMember(
                                  managingMembersTeam.id,
                                  member.id
                                )
                              }
                            >
                              제외
                            </Button>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-slate-400 text-center py-4">
                          {managingMembersTeam.members.length === 0
                            ? "멤버가 없습니다."
                            : "검색 결과가 없습니다."}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="text-center py-20 bg-white border border-dashed border-slate-200 rounded-2xl">
            <Users className="w-12 h-12 text-slate-200 mx-auto mb-4" />
            <p className="text-slate-900 font-bold mb-1">
              등록된 팀이 없습니다
            </p>
            <p className="text-sm text-slate-500">
              새로운 팀을 생성하여 멤버를 관리해보세요.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
