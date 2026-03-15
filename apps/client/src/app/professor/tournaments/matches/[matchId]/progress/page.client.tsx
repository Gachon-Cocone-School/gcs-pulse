'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
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
import { useAuth } from '@/context/auth-context';
import { createTournamentMatchStatusSse, tournamentsApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type { TournamentMatchProgressResponse } from '@/lib/types';
import { TournamentVoteResultBarChart } from '@/components/views/TournamentVoteResultBarChart';

interface ProfessorTournamentMatchProgressPageClientProps {
  matchId: number;
}

export default function ProfessorTournamentMatchProgressPageClient({
  matchId,
}: ProfessorTournamentMatchProgressPageClientProps) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const [data, setData] = useState<TournamentMatchProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

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

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadPage();
  }, [isAuthenticated, loadPage]);

  useEffect(() => {
    if (!isAuthenticated || !data?.match.id) {
      return;
    }

    const currentMatchId = data.match.id;
    const source = createTournamentMatchStatusSse((payload) => {
      if (payload.match_id !== currentMatchId) {
        return;
      }
      void loadPage();
    });

    return () => {
      source.close();
    };
  }, [isAuthenticated, data?.match.id, loadPage]);

  const match = data?.match;
  const showResult = Boolean(match && (match.status === 'closed' || data.session_is_open === false));
  const progressPercent = data && data.total_count > 0 ? (data.submitted_count / data.total_count) * 100 : 0;
  const voteUrl = useMemo(() => {
    if (!data?.vote_url) return '';
    if (typeof window === 'undefined') return data.vote_url;
    return new URL(data.vote_url, window.location.origin).toString();
  }, [data?.vote_url]);

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
            <Button asChild type="button" size="icon" variant="outline" aria-label="대진표로 돌아가기" title="대진표로 돌아가기">
              <Link href={match ? `/professor/tournaments/${match.session_id}/bracket` : '/professor/tournaments'}>
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
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
              <CardContent className="space-y-4">
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
                    <div className="flex items-center justify-center py-2">
                      <div className="inline-flex rounded-md bg-white p-3" data-testid="tournament-match-progress-qr">
                        {voteUrl
                          ? createElement(QRCode as unknown as ComponentType<{ value: string; size?: number }>, {
                              value: voteUrl,
                              size: 220,
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
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-7 2xl:grid-cols-8">
                  {data.voter_statuses.map((row) => (
                    <div
                      key={row.voter_user_id}
                      className="rounded-md border border-border/70 bg-card/80 px-2 py-1.5"
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
                      <div className="truncate text-center text-xs font-medium" title={row.voter_name}>
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
