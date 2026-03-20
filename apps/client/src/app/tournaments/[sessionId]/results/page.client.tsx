'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Loader2, ChevronLeft, Trophy, Medal, Users } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/context/auth-context';
import { tournamentsApi } from '@/lib/api';
import type { TournamentSessionResultsResponse, TournamentMatchResultItem } from '@/lib/types';

interface Props {
  sessionId: number;
}

function rankLabel(rank: number): string {
  switch (rank) {
    case 1: return '🥇 우승';
    case 2: return '🥈 준우승';
    case 3: return '🥉 공동 3위';
    default: return `공동 ${rank}위`;
  }
}

function bracketLabel(bracketType: string): string {
  return bracketType === 'losers' ? 'LB' : 'WB';
}

function MatchResultRow({ match }: { match: TournamentMatchResultItem }) {
  const team1Votes = match.vote_count_team1;
  const team2Votes = match.vote_count_team2;
  const totalVotes = team1Votes + team2Votes;
  const team1Pct = totalVotes > 0 ? Math.round((team1Votes / totalVotes) * 100) : 50;
  const team2Pct = 100 - team1Pct;
  const isTeam1Winner = match.winner_team_id === match.team1_id;
  const isTeam2Winner = match.winner_team_id === match.team2_id;

  return (
    <div className="rounded-lg border border-border/60 bg-card/70 px-4 py-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground font-mono">
          {match.global_match_no != null ? `M${match.global_match_no}` : `${bracketLabel(match.bracket_type)} R${match.round_no}.M${match.match_no}`}
        </span>
        <span className="text-xs text-muted-foreground">{bracketLabel(match.bracket_type)} R{match.round_no}</span>
      </div>

      <div className="flex items-center gap-2 text-sm">
        <span className={`flex-1 text-right font-medium ${isTeam1Winner ? 'text-primary' : 'text-muted-foreground'}`}>
          {match.team1_name ?? '-'}
          {isTeam1Winner && <span className="ml-1 text-xs">{match.is_tie ? '(판정승)' : '✓'}</span>}
        </span>
        <div className="flex flex-col items-center w-24 shrink-0">
          <div className="text-xs font-mono tabular-nums">
            {team1Votes} : {team2Votes}
          </div>
          <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden mt-1 flex">
            <div className="bg-primary rounded-l-full" style={{ width: `${team1Pct}%` }} />
            <div className="bg-muted-foreground/30 rounded-r-full" style={{ width: `${team2Pct}%` }} />
          </div>
        </div>
        <span className={`flex-1 font-medium ${isTeam2Winner ? 'text-primary' : 'text-muted-foreground'}`}>
          {match.team2_name ?? '-'}
          {isTeam2Winner && <span className="ml-1 text-xs">{match.is_tie ? '(판정승)' : '✓'}</span>}
        </span>
      </div>
    </div>
  );
}

export default function StudentTournamentResultsPageClient({ sessionId }: Props) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  const [data, setData] = useState<TournamentSessionResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace('/login');
  }, [isLoading, isAuthenticated, router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await tournamentsApi.getResults(sessionId);
      setData(res);
    } catch {
      setError('결과를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void load();
  }, [isAuthenticated, load]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const rankGroups: { rank: number; teams: NonNullable<typeof data>['team_rankings'] }[] = [];
  if (data) {
    let i = 0;
    while (i < data.team_rankings.length) {
      const rank = data.team_rankings[i].rank;
      const group = data.team_rankings.filter((t) => t.rank === rank);
      rankGroups.push({ rank, teams: group });
      i += group.length;
    }
  }

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-3xl px-6 py-8 space-y-6">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="icon" className="-ml-2">
            <Link href={`/tournaments/${sessionId}/bracket`}>
              <ChevronLeft className="h-5 w-5" />
            </Link>
          </Button>
          <PageHeader
            title={data?.title ?? '토너먼트 결과'}
            description="팀 순위 및 투표 결과"
            actions={null}
          />
        </div>

        {error ? (
          <Card className="border-destructive/40">
            <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
          </Card>
        ) : null}

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : data ? (
          <>
            {/* 팀 순위 */}
            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="h-4 w-4 text-yellow-500" />
                  팀 순위
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {rankGroups.map(({ rank, teams }) => (
                  <div key={rank} className="flex items-start gap-3 rounded-lg border border-border/50 bg-card/50 px-4 py-3">
                    <div className="w-24 shrink-0">
                      <Badge
                        variant={rank === 1 ? 'default' : rank === 2 ? 'secondary' : 'outline'}
                        className="text-xs"
                      >
                        {rankLabel(rank)}
                      </Badge>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {teams.map((t) => (
                        <span key={t.team_id} className="font-medium text-sm">{t.team_name}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* 경기 결과 */}
            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Medal className="h-4 w-4 text-primary" />
                  경기 결과
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.matches.length === 0 ? (
                  <div className="text-sm text-muted-foreground py-4 text-center">완료된 경기가 없습니다.</div>
                ) : (
                  data.matches.map((m) => <MatchResultRow key={m.id} match={m} />)
                )}
              </CardContent>
            </Card>

            {/* 투표자 순위 */}
            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-primary" />
                  투표자 득점 순위
                </CardTitle>
              </CardHeader>
              <CardContent>
                {data.voter_rankings.length === 0 ? (
                  <div className="text-sm text-muted-foreground py-4 text-center">투표 데이터가 없습니다.</div>
                ) : (
                  <div className="rounded-lg border border-border overflow-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left bg-muted/30">
                          <th className="px-3 py-2 text-muted-foreground font-medium">순위</th>
                          <th className="px-3 py-2 text-muted-foreground font-medium">이름</th>
                          <th className="px-3 py-2 text-muted-foreground font-medium text-right">점수</th>
                          <th className="px-3 py-2 text-muted-foreground font-medium text-right">총 응답시간</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.voter_rankings.map((v) => (
                          <tr key={v.voter_user_id} className="border-b border-border/50 last:border-b-0">
                            <td className="px-3 py-2 font-mono tabular-nums">
                              {v.rank === 1 ? '🥇' : v.rank === 2 ? '🥈' : v.rank === 3 ? '🥉' : ''} {v.rank}위
                            </td>
                            <td className="px-3 py-2">{v.voter_name}</td>
                            <td className="px-3 py-2 text-right tabular-nums font-medium">
                              {v.score}
                              <span className="text-muted-foreground font-normal">/{v.total_matches}</span>
                            </td>
                            <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                              {v.cumulative_response_seconds.toFixed(1)}초
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        ) : null}
      </main>
    </div>
  );
}
