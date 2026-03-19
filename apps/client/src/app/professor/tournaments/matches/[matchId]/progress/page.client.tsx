'use client';

import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createElement, useCallback, useEffect, useMemo, useState } from 'react';
import type { ComponentType } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';
import QRCode from 'react-qr-code';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { TournamentVoteResultBarChart } from '@/components/views/TournamentVoteResultBarChart';
import { useAuth } from '@/context/auth-context';
import { createTournamentMatchStatusSse, createTournamentVoteProgressSse, tournamentsApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type { TournamentMatchProgressResponse } from '@/lib/types';

interface ProfessorTournamentMatchProgressPageClientProps {
  matchId: number;
}

export default function ProfessorTournamentMatchProgressPageClient({
  matchId,
}: ProfessorTournamentMatchProgressPageClientProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const [data, setData] = useState<TournamentMatchProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdatingMatchStatus, setIsUpdatingMatchStatus] = useState(false);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await tournamentsApi.getMatchProgress(matchId);
      setData(response);
    } catch (e) {
      console.error(e);
      setError('경기 진행 화면을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [matchId]);

  const loadProgressOnly = useCallback(async () => {
    try {
      const response = await tournamentsApi.getMatchProgress(matchId);
      setData(response);
    } catch (e) {
      console.error(e);
    }
  }, [matchId]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadPage();
  }, [isAuthenticated, loadPage]);

  // match status 변경 SSE (경기 개시/종료)
  useEffect(() => {
    if (!isAuthenticated || !data?.match.id) {
      return;
    }

    const currentMatchId = data.match.id;
    const source = createTournamentMatchStatusSse((payload) => {
      if (payload.match_id !== currentMatchId) {
        return;
      }
      void loadProgressOnly();
    });

    return () => {
      source.close();
    };
  }, [isAuthenticated, data?.match.id, loadProgressOnly]);

  // 투표 제출 SSE (학생이 투표할 때 제출 현황 실시간 갱신)
  useEffect(() => {
    if (!isAuthenticated || !data?.match.id) {
      return;
    }

    const currentMatchId = data.match.id;
    const source = createTournamentVoteProgressSse((payload) => {
      if (payload.match_id !== currentMatchId) {
        return;
      }
      void loadProgressOnly();
    });

    return () => {
      source.close();
    };
  }, [isAuthenticated, data?.match.id, loadProgressOnly]);

  const handleUpdateMatchStatus = useCallback(
    async (status: 'open' | 'closed') => {
      setIsUpdatingMatchStatus(true);
      setError(null);
      try {
        await tournamentsApi.updateMatchStatus(matchId, { status });
        await loadProgressOnly();
      } catch (e) {
        console.error(e);
        setError(status === 'open' ? '투표 개시에 실패했습니다.' : '투표 종료에 실패했습니다.');
      } finally {
        setIsUpdatingMatchStatus(false);
      }
    },
    [matchId, loadProgressOnly],
  );

  const match = data?.match;
  const isMatchOpen = match?.status === 'open';
  const showResult = Boolean(match && (match.status === 'closed' || data?.session_is_open === false));
  const progressPercent = data && data.total_count > 0 ? (data.submitted_count / data.total_count) * 100 : 0;
  const voteUrl = useMemo(() => {
    if (!data?.vote_url) return '';
    if (typeof window === 'undefined') return data.vote_url;
    return new URL(data.vote_url, window.location.origin).toString();
  }, [data?.vote_url]);

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
      <main className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col gap-6 px-6 py-8">
        <PageHeader
          title="토너먼트 경기 진행 현황"
          description="투표 QR과 제출 현황을 확인할 수 있습니다."
          actions={
            <div className="flex flex-wrap gap-2">
              {isMatchOpen ? (
                <Button type="button" size="icon" variant="outline" aria-label="대진표로 돌아가기" title="대진표로 돌아가기" disabled>
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              ) : (
                <Button asChild type="button" size="icon" variant="outline" aria-label="대진표로 돌아가기" title="대진표로 돌아가기">
                  <Link href={match ? `/professor/tournaments/${match.session_id}/bracket` : '/professor/tournaments'}>
                    <ArrowLeft className="h-4 w-4" />
                  </Link>
                </Button>
              )}
              <Button
                onClick={() => { void handleUpdateMatchStatus('open'); }}
                disabled={isUpdatingMatchStatus || isMatchOpen || !match}
              >
                투표 개시
              </Button>
              <Button
                variant="secondary"
                onClick={() => { void handleUpdateMatchStatus('closed'); }}
                disabled={isUpdatingMatchStatus || !isMatchOpen || !match}
              >
                투표 종료
              </Button>
            </div>
          }
        />

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {loading || !data || !match ? (
          <Card>
            <CardContent className="py-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </CardContent>
          </Card>
        ) : (
          <div className="grid flex-1 gap-6 lg:grid-cols-[minmax(300px,1fr)_minmax(0,2fr)]">
            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md min-h-[420px]">
              <CardHeader>
                <CardTitle>
                  Round {match.round_no} · Match {match.match_no}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex h-full flex-col gap-4">
                <div className="text-sm text-muted-foreground">
                  상태: {match.status} {match.is_bye ? '(BYE)' : ''}
                </div>
                {showResult ? (
                  match.vote_count_team1 !== null && match.vote_count_team2 !== null ? (
                    <TournamentVoteResultBarChart
                      team1Name={match.team1_name || (match.team1_id ? `Team ${match.team1_id}` : 'Team 1')}
                      team1Votes={match.vote_count_team1}
                      team2Name={match.team2_name || (match.team2_id ? `Team ${match.team2_id}` : 'Team 2')}
                      team2Votes={match.vote_count_team2}
                    />
                  ) : (
                    <div className="text-sm text-muted-foreground">결과를 집계 중입니다.</div>
                  )
                ) : (
                  <>
                    <div className="flex flex-1 items-center justify-center" data-testid="tournament-match-progress-qr">
                      <div className="inline-flex rounded-md bg-white p-3">
                        {voteUrl
                          ? createElement(QRCode as unknown as ComponentType<{ value: string; size?: number }>, {
                              value: voteUrl,
                              size: 280,
                            })
                          : null}
                      </div>
                    </div>
                    <div className="break-all text-xs text-muted-foreground">{voteUrl}</div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md min-h-[420px]">
              <CardHeader className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <CardTitle>제출 현황</CardTitle>
                  <div className="space-y-2 text-right">
                    <div className="text-sm font-medium">제출한 사람 {data.submitted_count}/{data.total_count}</div>
                    <Progress value={progressPercent} className="h-3 w-56" />
                  </div>
                </div>
                {!data.allow_self_vote ? (
                  <div className="text-xs text-muted-foreground">출전 팀원은 본인 경기에 투표할 수 없어 목록에서 제외됩니다.</div>
                ) : null}
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-6">
                  {data.voter_statuses.map((row) => (
                    <div
                      key={row.voter_user_id}
                      className="group relative rounded-md border border-border/70 bg-card/80 px-2.5 py-2"
                      style={
                        row.has_submitted
                          ? {
                              borderColor: 'var(--sys-current-border)',
                              backgroundColor: 'var(--sys-current-bg)',
                              color: 'var(--sys-current-fg)',
                            }
                          : undefined
                      }
                    >
                      <div className="truncate text-center text-sm font-medium">
                        {row.voter_name}
                      </div>
                      <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded bg-slate-900 px-2 py-1 text-xs text-white shadow-md opacity-0 transition-opacity group-hover:opacity-100">
                        {row.voter_name}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
