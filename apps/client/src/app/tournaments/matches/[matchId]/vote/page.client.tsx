'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';
import { ApiError, createTournamentMatchStatusSse, tournamentsApi } from '@/lib/api';
import type { TournamentMatchItem } from '@/lib/types';
import { TournamentVoteResultBarChart } from '@/components/views/TournamentVoteResultBarChart';

interface TournamentMatchVotePageClientProps {
  matchId: number;
}

export default function TournamentMatchVotePageClient({ matchId }: TournamentMatchVotePageClientProps) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  const [match, setMatch] = useState<TournamentMatchItem | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  const loadMatch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await tournamentsApi.getMatch(matchId);
      setMatch(response);
      setSelectedTeamId((prev) => prev ?? response.team1_id ?? response.team2_id ?? null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) {
        setError('서버에 연결하지 못했습니다. 네트워크 또는 브라우저 CORS/쿠키 설정을 확인해 주세요.');
      } else {
        console.error(e);
        setError('경기 정보를 불러오지 못했습니다.');
      }
    } finally {
      setLoading(false);
    }
  }, [matchId]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadMatch();
  }, [isAuthenticated, loadMatch]);

  useEffect(() => {
    if (!isAuthenticated || !match?.id) {
      return;
    }

    const currentMatchId = match.id;
    const source = createTournamentMatchStatusSse((payload) => {
      if (payload.match_id !== currentMatchId) {
        return;
      }

      setMatch((prev) => {
        if (!prev || prev.id !== payload.match_id) {
          return prev;
        }
        return {
          ...prev,
          status: payload.match_status,
          session_is_open: payload.session_is_open,
        };
      });

      if (!payload.session_is_open || payload.match_status !== 'open') {
        setError((prev) => prev ?? '현재 투표 가능한 경기가 아닙니다.');
        setSuccess(null);
        void loadMatch();
      } else {
        setError(null);
      }
    });

    return () => {
      source.close();
    };
  }, [isAuthenticated, match?.id, loadMatch]);

  const handleSubmit = useCallback(async () => {
    if (!match || selectedTeamId === null) {
      setError('투표 팀을 선택해 주세요.');
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await tournamentsApi.submitVote(match.id, { selected_team_id: selectedTeamId });
      setMatch(response.match);
      setSuccess('투표가 제출되었습니다.');
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError('현재 투표 가능한 경기가 아닙니다.');
        await loadMatch();
      } else {
        console.error(e);
        setError('투표 제출에 실패했습니다.');
      }
    } finally {
      setSubmitting(false);
    }
  }, [match, selectedTeamId, loadMatch]);

  const canVote = Boolean(match && match.session_is_open !== false && match.status === 'open' && !match.is_bye);

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

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-3xl px-6 py-8 space-y-6">
        <PageHeader title="토너먼트 경기 투표" description="개시된 경기에서만 투표할 수 있습니다." />

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {success ? (
          <Alert>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        ) : null}

        {loading || !match ? (
          <Card>
            <CardContent className="py-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </CardContent>
          </Card>
        ) : (
          <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
            <CardHeader>
              <CardTitle>
                Round {match.round_no} · Match {match.match_no}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-muted-foreground">
                상태: {match.status} {match.is_bye ? '(BYE)' : ''}
              </div>

              {canVote ? (
                <>
                  <div className="space-y-2">
                    {match.team1_id ? (
                      <label className="flex items-center gap-2 rounded-lg border border-border/70 p-3">
                        <input
                          type="radio"
                          checked={selectedTeamId === match.team1_id}
                          onChange={() => setSelectedTeamId(match.team1_id ?? null)}
                          disabled={submitting}
                        />
                        <span>{match.team1_name || `Team ${match.team1_id}`}</span>
                      </label>
                    ) : null}

                    {match.team2_id ? (
                      <label className="flex items-center gap-2 rounded-lg border border-border/70 p-3">
                        <input
                          type="radio"
                          checked={selectedTeamId === match.team2_id}
                          onChange={() => setSelectedTeamId(match.team2_id ?? null)}
                          disabled={submitting}
                        />
                        <span>{match.team2_name || `Team ${match.team2_id}`}</span>
                      </label>
                    ) : null}
                  </div>

                  <Button
                    type="button"
                    onClick={() => {
                      void handleSubmit();
                    }}
                    disabled={submitting}
                  >
                    {submitting ? '제출 중...' : '투표 제출'}
                  </Button>
                </>
              ) : (
                <>
                  <div className="text-sm text-muted-foreground">투표가 종료되어 결과를 표시합니다.</div>
                  {match.vote_count_team1 !== null && match.vote_count_team2 !== null ? (
                    <TournamentVoteResultBarChart
                      team1Name={match.team1_name || (match.team1_id ? `Team ${match.team1_id}` : 'Team 1')}
                      team1Votes={match.vote_count_team1}
                      team2Name={match.team2_name || (match.team2_id ? `Team ${match.team2_id}` : 'Team 2')}
                      team2Votes={match.vote_count_team2}
                    />
                  ) : (
                    <div className="text-sm text-muted-foreground">결과를 집계 중입니다.</div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
