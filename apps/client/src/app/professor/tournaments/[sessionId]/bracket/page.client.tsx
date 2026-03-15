'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';
import { tournamentsApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type { TournamentMatchItem, TournamentSessionResponse } from '@/lib/types';

interface ProfessorTournamentBracketPageClientProps {
  sessionId: number;
}

export default function ProfessorTournamentBracketPageClient({ sessionId }: ProfessorTournamentBracketPageClientProps) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const [session, setSession] = useState<TournamentSessionResponse | null>(null);
  const [matches, setMatches] = useState<TournamentMatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [recentWinners, setRecentWinners] = useState<number[]>([]);
  const markRecent = useCallback((id: number) => {
    setRecentWinners((prev) => [...prev, id]);
    setTimeout(() => {
      setRecentWinners((prev) => prev.filter((x) => x !== id));
    }, 3000);
  }, []);


  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sessionResponse, bracketResponse] = await Promise.all([
        tournamentsApi.getSession(sessionId),
        tournamentsApi.getBracket(sessionId),
      ]);
      setSession(sessionResponse);
      setMatches(bracketResponse.rounds.flatMap((round) => round.matches));
    } catch (e) {
      console.error(e);
      setError('대진표 정보를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadPage();
  }, [isAuthenticated, loadPage]);

  const bracketGroups = useMemo(() => {
    const groupedByBracket = new Map<string, Map<number, TournamentMatchItem[]>>();

    for (const match of matches) {
      if (!groupedByBracket.has(match.bracket_type)) {
        groupedByBracket.set(match.bracket_type, new Map<number, TournamentMatchItem[]>());
      }
      const roundsInBracket = groupedByBracket.get(match.bracket_type)!;
      if (!roundsInBracket.has(match.round_no)) {
        roundsInBracket.set(match.round_no, []);
      }
      roundsInBracket.get(match.round_no)!.push(match);
    }

    return Array.from(groupedByBracket.entries())
      .map(([bracketType, roundsMap]) => ({
        bracketType,
        rounds: Array.from(roundsMap.entries())
          .map(([roundNo, roundMatches]) => ({
            roundNo,
            matches: roundMatches.sort((a, b) => a.match_no - b.match_no),
          }))
          .sort((a, b) => a.roundNo - b.roundNo),
      }))
      .sort((a, b) => a.bracketType.localeCompare(b.bracketType));
  }, [matches]);

  const incomingMatchIds = useMemo(() => {
    const incoming = new Set<number>();
    for (const match of matches) {
      if (match.next_match_id) {
        incoming.add(match.next_match_id);
      }
    }
    return incoming;
  }, [matches]);


  const runAction = useCallback(
    async (
      action: () => Promise<void>,
      options?: {
        reload?: boolean;
        onSuccess?: () => void;
      },
    ) => {
      setBusy(true);
      setError(null);
      try {
        await action();
        options?.onSuccess?.();
        if (options?.reload ?? true) {
          await loadPage();
        }
      } catch (e) {
        console.error(e);
        setError('요청 처리에 실패했습니다.');
      } finally {
        setBusy(false);
      }
    },
    [loadPage],
  );

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
        <PageHeader
          title="토너먼트 대진표"
          description={session ? session.title : '대진표를 관리합니다.'}
          actions={
            <div className="flex flex-wrap gap-2">
              <Button asChild type="button" size="icon" variant="outline" aria-label="목록으로" title="목록으로" disabled={busy}>
                <Link href="/professor/tournaments">
                  <ArrowLeft className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={busy || !session}
                onClick={() => {
                  if (!session) return;
                  void runAction(async () => {
                    await tournamentsApi.updateSessionStatus(session.id, { is_open: !session.is_open });
                  });
                }}
              >
                {session?.is_open ? '세션 종료' : '세션 개시'}
              </Button>
              <Button
                type="button"
                disabled={busy}
                onClick={() => {
                  void runAction(async () => {
                    await tournamentsApi.generateMatches(sessionId);
                  });
                }}
              >
                대진 생성
              </Button>
            </div>
          }
        />

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {loading ? (
          <Card>
            <CardContent className="py-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </CardContent>
          </Card>
        ) : bracketGroups.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-sm text-muted-foreground text-center">
              생성된 경기가 없습니다. 먼저 팀/포맷을 저장한 뒤 대진 생성을 실행해 주세요.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {bracketGroups.map((bracketGroup) => (
              <Card key={bracketGroup.bracketType} className="glass-card rounded-xl animate-entrance shadow-md" style={{ borderColor: 'var(--color-primary)' }}>
                <CardHeader>
                  <CardTitle>{bracketGroup.bracketType} 브래킷</CardTitle>
                </CardHeader>
                <CardContent className="overflow-auto pb-2">
                  {(() => {
                    const rounds = bracketGroup.rounds;
                    const totalRounds = rounds.length;
                    const totalRows = 2 ** totalRounds;
                    const rowHeight = 24; // px per grid row
                    const colWidth = 168; // 240 * 0.7 (30% reduced)
                    return (
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: `repeat(${totalRounds}, ${colWidth}px)`,
                          gridTemplateRows: `repeat(${totalRows}, ${rowHeight}px)`,
                          gap: '24px 48px',
                          minWidth: `${totalRounds * colWidth + (totalRounds - 1) * 16}px`,
                        }}
                      >
                        {rounds.map((round, roundIndex) =>
                          round.matches.map((match, matchIndex) => {
                            const step = Math.pow(2, round.roundNo);
                            const rowStart = step / 2 + matchIndex * step;
                            return (
                              <div
                                key={match.id}
                                style={{ gridColumn: roundIndex + 1, gridRowStart: rowStart }}
                              >
                                <div
                                  role="button"
                                  tabIndex={0}
                                  onClick={() => router.push(`/professor/tournaments/matches/${match.id}/progress`)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') router.push(`/professor/tournaments/matches/${match.id}/progress`);
                                  }}
                                  className="rounded-lg border bg-card/90 p-3 shadow-sm cursor-pointer hover:shadow-md focus:outline-none" style={{ borderColor: 'var(--color-primary)' }}
                                >
                                  
                                  <div className="text-sm text-primary">{match.team1_name || '-'}</div>
                                  <div className="text-sm text-primary mt-2">{match.team2_name || '-'}</div>

                                  {match.is_bye ? <div className="mt-2 text-xs text-muted-foreground">BYE</div> : null}
                                </div>
                              </div>
                            );
                          }),
                        )}
                      </div>
                    );
                  })()}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
