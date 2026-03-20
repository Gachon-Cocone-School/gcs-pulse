'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { redirect, useRouter } from 'next/navigation';
import { BarChart3, Loader2, Pencil, Play, Trash2 } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';
import { tournamentsApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type { TournamentSessionListItem } from '@/lib/types';

function formatUpdatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export default function ProfessorTournamentsPageClient() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const [sessions, setSessions] = useState<TournamentSessionListItem[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [actionState, setActionState] = useState<{ creating: boolean; deletingSessionId: number | null }>({
    creating: false,
    deletingSessionId: null,
  });
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const response = await tournamentsApi.listSessions();
      setSessions(response.items);
    } catch (e) {
      console.error(e);
      setError('세션 목록을 불러오지 못했습니다.');
    } finally {
      setLoadingSessions(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadSessions();
  }, [isAuthenticated, loadSessions]);

  const isBusy = actionState.creating || actionState.deletingSessionId !== null;

  const handleCreateSession = useCallback(async () => {
    setActionState((prev) => ({ ...prev, creating: true }));
    setError(null);
    router.push('/professor/tournaments/new/edit');
  }, [router]);

  const handleDeleteSession = useCallback(
    async (sessionId: number) => {
      const confirmed = window.confirm('이 토너먼트 세션을 삭제하시겠습니까?');
      if (!confirmed) return;

      setActionState((prev) => ({ ...prev, deletingSessionId: sessionId }));
      setError(null);
      try {
        await tournamentsApi.deleteSession(sessionId);
        await loadSessions();
      } catch (e) {
        console.error(e);
        setError('세션 삭제에 실패했습니다.');
      } finally {
        setActionState((prev) => ({ ...prev, deletingSessionId: null }));
      }
    },
    [loadSessions],
  );

  if (!isLoading && !isAuthenticated) {
    redirect('/login');
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (!hasAccess || !isProfessor) {
    return <AccessDeniedView reason="student-only" />;
  }

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-7xl px-6 py-8 space-y-6">
        <PageHeader title="토너먼트 세션 리스트" description="세션을 생성하고 편집/대진표/삭제를 관리합니다." />

        {error ? (
          <Card className="border-destructive/40">
            <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
          </Card>
        ) : null}

        <Card className="glass-card rounded-xl animate-entrance">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle>내 토너먼트 목록</CardTitle>
              <Button onClick={handleCreateSession} disabled={isBusy} className="w-full sm:w-auto">
                {actionState.creating ? '생성 중...' : '생성하기'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {loadingSessions ? <div className="py-2 text-sm text-muted-foreground">세션 목록을 불러오는 중...</div> : null}

            {!loadingSessions && sessions.length === 0 ? (
              <div className="rounded-lg border border-border/60 bg-card/70 px-4 py-8 text-center text-sm text-muted-foreground">
                생성된 세션이 없습니다.
              </div>
            ) : null}

            {sessions.length > 0 ? (
              <div className="rounded-lg border border-border overflow-auto bg-card/70">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="p-2">제목</th>
                      <th className="p-2">마지막 수정일</th>
                      <th className="p-2">팀 수</th>
                      <th className="p-2">경기 수</th>
                      <th className="p-2">액션</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((item) => {
                      const isDeleting = actionState.deletingSessionId === item.id;
                      const rowDisabled = isBusy;

                      return (
                        <tr key={item.id} className="border-b border-border/50 last:border-b-0">
                          <td className="p-2 min-w-[220px]">{item.title}</td>
                          <td className="p-2">{formatUpdatedAt(item.updated_at)}</td>
                          <td className="p-2">{item.team_count}</td>
                          <td className="p-2">{item.match_count}</td>
                          <td className="p-2">
                            <div className="flex gap-1">
                              <Button asChild type="button" size="icon" variant="secondary" title="대진표" aria-label="대진표">
                                <Link href={`/professor/tournaments/${item.id}/bracket`}>
                                  <Play className="h-4 w-4" />
                                </Link>
                              </Button>
                              <Button asChild type="button" size="icon" variant="outline" title="결과 보기" aria-label="결과 보기">
                                <Link href={`/professor/tournaments/${item.id}/results?ref=list`}>
                                  <BarChart3 className="h-4 w-4" />
                                </Link>
                              </Button>
                              <Button asChild type="button" size="icon" variant="outline" title="편집" aria-label="편집">
                                <Link href={`/professor/tournaments/${item.id}/edit`}>
                                  <Pencil className="h-4 w-4" />
                                </Link>
                              </Button>
                              <Button
                                type="button"
                                size="icon"
                                variant="destructive"
                                title={isDeleting ? '삭제 중...' : '삭제'}
                                aria-label={isDeleting ? '삭제 중...' : '삭제'}
                                onClick={() => {
                                  void handleDeleteSession(item.id);
                                }}
                                disabled={rowDisabled || isDeleting}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
