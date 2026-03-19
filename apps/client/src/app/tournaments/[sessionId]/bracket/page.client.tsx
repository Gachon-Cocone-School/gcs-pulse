'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, Trophy } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';
import { createTournamentMatchStatusSse, tournamentsApi } from '@/lib/api';
import type { TournamentMatchItem } from '@/lib/types';

interface Props {
  sessionId: number;
}

const MATCH_CARD_W = 172;
const MATCH_CARD_H = 80;
const COL_GAP = 56;
const SLOT_BASE = MATCH_CARD_H + 20;

function getSlotHeight(round_no: number) {
  return SLOT_BASE * Math.pow(2, round_no - 1);
}


function statusBadge(status: string) {
  if (status === 'open')
    return (
      <Badge className="text-[10px] px-1.5 py-0 h-4 bg-yellow-400/20 text-yellow-700 border-yellow-400/40 dark:text-yellow-300">
        진행중
      </Badge>
    );
  if (status === 'closed')
    return (
      <Badge className="text-[10px] px-1.5 py-0 h-4 bg-green-500/20 text-green-700 border-green-500/40 dark:text-green-300">
        완료
      </Badge>
    );
  return (
    <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 text-muted-foreground">
      대기
    </Badge>
  );
}

/** WB(라운드순) → LB(라운드순) 순으로 1부터 전체 고유 번호 부여 */
function buildGlobalMatchNos(allMatches: TournamentMatchItem[]): Map<number, number> {
  const sorted = [...allMatches].sort((a, b) => {
    const ba = a.bracket_type === 'losers' ? 1 : 0;
    const bb = b.bracket_type === 'losers' ? 1 : 0;
    if (ba !== bb) return ba - bb;
    if (a.round_no !== b.round_no) return a.round_no - b.round_no;
    return a.match_no - b.match_no;
  });
  const map = new Map<number, number>();
  sorted.forEach((m, i) => map.set(m.id, i + 1));
  return map;
}

function buildFeederLabels(
  allMatches: TournamentMatchItem[],
  globalNos: Map<number, number>,
): Map<number, { team1?: string; team2?: string }> {
  const labels = new Map<number, { team1?: string; team2?: string }>();
  const get = (id: number) => {
    if (!labels.has(id)) labels.set(id, {});
    return labels.get(id)!;
  };
  const matchById = new Map(allMatches.map((m) => [m.id, m]));

  const loserFeeders = new Map<number, TournamentMatchItem[]>();
  const winnerFeeders = new Map<number, TournamentMatchItem[]>();

  for (const m of allMatches) {
    if (m.loser_next_match_id != null) {
      if (!loserFeeders.has(m.loser_next_match_id)) loserFeeders.set(m.loser_next_match_id, []);
      loserFeeders.get(m.loser_next_match_id)!.push(m);
    }
    if (m.next_match_id != null) {
      if (!winnerFeeders.has(m.next_match_id)) winnerFeeders.set(m.next_match_id, []);
      winnerFeeders.get(m.next_match_id)!.push(m);
    }
  }

  const gn = (m: TournamentMatchItem) => globalNos.get(m.id) ?? m.match_no;
  const allTargetIds = new Set([...Array.from(loserFeeders.keys()), ...Array.from(winnerFeeders.keys())]);

  for (const targetId of Array.from(allTargetIds)) {
    const losers = (loserFeeders.get(targetId) ?? []).sort((a, b) => gn(a) - gn(b));
    const winners = (winnerFeeders.get(targetId) ?? []).sort((a, b) => gn(a) - gn(b));
    const target = matchById.get(targetId);
    const entry = get(targetId);

    const hasMixedLb =
      target?.bracket_type === 'losers' && losers.length > 0 && winners.length > 0;

    if (hasMixedLb) {
      for (const src of winners) {
        if (entry.team1 == null) entry.team1 = `M${gn(src)} 승자`;
      }
      for (const src of losers) {
        if (entry.team2 == null) entry.team2 = `M${gn(src)} 패자`;
      }
    } else {
      const all = [
        ...losers.map((src) => `M${gn(src)} 패자`),
        ...winners.map((src) => `M${gn(src)} 승자`),
      ];
      for (const lbl of all) {
        if (entry.team1 == null) entry.team1 = lbl;
        else if (entry.team2 == null) entry.team2 = lbl;
      }
    }
  }

  return labels;
}

function MatchCard({
  match,
  isFinal,
  globalNo,
  team1Label,
  team2Label,
}: {
  match: TournamentMatchItem;
  isFinal: boolean;
  globalNo?: number;
  team1Label?: string;
  team2Label?: string;
}) {
  const isWinner1 = match.winner_team_id != null && match.winner_team_id === match.team1_id;
  const isWinner2 = match.winner_team_id != null && match.winner_team_id === match.team2_id;
  const name1 = match.team1_name ?? team1Label;
  const name2 = match.team2_name ?? team2Label;

  return (
    <div
      className="w-full rounded-lg border bg-card/90 shadow-sm text-left"
      style={{ height: MATCH_CARD_H, borderColor: isFinal ? 'var(--color-primary)' : undefined }}
    >
      <div className="flex flex-col h-full px-2 py-1.5 gap-0.5">
        <div className="flex items-center justify-between gap-1 mb-0.5">
          <span className="text-[10px] text-muted-foreground">
            {match.is_bye ? 'BYE' : `M${globalNo ?? match.match_no}`}
          </span>
          {statusBadge(match.status)}
        </div>
        <div
          className="text-xs font-medium truncate flex-1 flex items-center"
          style={isWinner1 ? { color: 'var(--color-primary)', fontWeight: 700 } : undefined}
        >
          {isWinner1 && <Trophy className="h-3 w-3 mr-1 flex-shrink-0" />}
          <span className={`truncate${match.team1_name == null && name1 != null ? ' text-muted-foreground italic' : ''}`}>
            {name1 ?? '—'}
          </span>
          {match.status === 'closed' && match.vote_count_team1 != null && (
            <span className="ml-auto text-[10px] text-muted-foreground pl-1">{match.vote_count_team1}</span>
          )}
        </div>
        <div className="border-t border-border/30 my-0.5" />
        <div
          className="text-xs font-medium truncate flex-1 flex items-center"
          style={isWinner2 ? { color: 'var(--color-primary)', fontWeight: 700 } : undefined}
        >
          {isWinner2 && <Trophy className="h-3 w-3 mr-1 flex-shrink-0" />}
          <span className={`truncate${match.team2_name == null && name2 != null ? ' text-muted-foreground italic' : ''}`}>
            {name2 ?? '—'}
          </span>
          {match.status === 'closed' && match.vote_count_team2 != null && (
            <span className="ml-auto text-[10px] text-muted-foreground pl-1">{match.vote_count_team2}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function BracketSection({
  title,
  rounds,
  matches,
  allMatches,
  finalRoundNo,
  finalLabel,
}: {
  title: string;
  rounds: number[];
  matches: TournamentMatchItem[];
  allMatches: TournamentMatchItem[];
  finalRoundNo: number;
  finalLabel?: string;
}) {
  const globalMatchNos = useMemo(() => buildGlobalMatchNos(allMatches), [allMatches]);
  const feederLabels = useMemo(() => buildFeederLabels(allMatches, globalMatchNos), [allMatches, globalMatchNos]);
  const matchesByRound = useMemo(() => {
    const m = new Map<number, TournamentMatchItem[]>();
    for (const match of matches) {
      if (!m.has(match.round_no)) m.set(match.round_no, []);
      m.get(match.round_no)!.push(match);
    }
    m.forEach((arr) => arr.sort((a: TournamentMatchItem, b: TournamentMatchItem) => a.match_no - b.match_no));
    return m;
  }, [matches]);

  // 각 라운드의 실제 경기 수 기반으로 slot 높이 균등 계산
  const { totalHeight, roundSlotHeights } = useMemo(() => {
    const maxCount = rounds.reduce((max, r) => Math.max(max, (matchesByRound.get(r) ?? []).length), 1);
    const h = Math.max(maxCount * SLOT_BASE, MATCH_CARD_H + 20);
    const heights = new Map<number, number>();
    for (const r of rounds) {
      const count = (matchesByRound.get(r) ?? []).length;
      heights.set(r, count > 0 ? h / count : h);
    }
    return { totalHeight: h, roundSlotHeights: heights };
  }, [rounds, matchesByRound]);

  // LB 라운드: LB 피더의 display position 기준으로 재정렬
  const matchDisplayPositions = useMemo(() => {
    const positions = new Map<number, number>();
    const lbFeedersOf = new Map<number, TournamentMatchItem[]>();
    for (const m of allMatches) {
      if (m.next_match_id != null && m.bracket_type === 'losers') {
        if (!lbFeedersOf.has(m.next_match_id)) lbFeedersOf.set(m.next_match_id, []);
        lbFeedersOf.get(m.next_match_id)!.push(m);
      }
    }
    for (const r of rounds) {
      const roundMatches = matchesByRound.get(r) ?? [];
      const hasLbFeeder = roundMatches.some((m) => lbFeedersOf.has(m.id));
      if (hasLbFeeder) {
        const sorted = [...roundMatches].sort((a, b) => {
          const feedersA = lbFeedersOf.get(a.id) ?? [];
          const feedersB = lbFeedersOf.get(b.id) ?? [];
          const minA = feedersA.length > 0 ? Math.min(...feedersA.map((f) => positions.get(f.id) ?? 9999)) : 9999;
          const minB = feedersB.length > 0 ? Math.min(...feedersB.map((f) => positions.get(f.id) ?? 9999)) : 9999;
          return minA - minB;
        });
        sorted.forEach((m, i) => positions.set(m.id, i + 1));
      } else {
        roundMatches.forEach((m) => positions.set(m.id, m.match_no));
      }
    }
    return positions;
  }, [rounds, matchesByRound, allMatches]);

  const slotCenter = (matchId: number, round_no: number) => {
    const pos = matchDisplayPositions.get(matchId) ?? 1;
    const sh = roundSlotHeights.get(round_no) ?? getSlotHeight(round_no);
    return sh * (pos - 1) + sh / 2;
  };

  const totalWidth = rounds.length * MATCH_CARD_W + (rounds.length - 1) * COL_GAP;

  const connectorPaths = useMemo(() => {
    const paths: string[] = [];
    const matchById = new Map<number, TournamentMatchItem>();
    for (const m of matches) matchById.set(m.id, m);

    const roundIndex = new Map<number, number>();
    rounds.forEach((r, ri) => roundIndex.set(r, ri));

    const sourcesByTarget = new Map<number, TournamentMatchItem[]>();
    for (const m of matches) {
      if (m.next_match_id == null) continue;
      if (!sourcesByTarget.has(m.next_match_id)) sourcesByTarget.set(m.next_match_id, []);
      sourcesByTarget.get(m.next_match_id)!.push(m);
    }

    for (const [targetId, sources] of Array.from(sourcesByTarget)) {
      const target = matchById.get(targetId);
      if (!target) continue;
      const tRi = roundIndex.get(target.round_no);
      if (tRi == null) continue;
      const xLeft = tRi * (MATCH_CARD_W + COL_GAP);
      const xMid = xLeft - COL_GAP / 2;
      const yTarget = slotCenter(target.id, target.round_no);

      let drew = false;
      for (const src of sources) {
        const sRi = roundIndex.get(src.round_no);
        if (sRi == null) continue;
        const xRight = sRi * (MATCH_CARD_W + COL_GAP) + MATCH_CARD_W;
        const ySrc = slotCenter(src.id, src.round_no);
        paths.push(`M ${xRight} ${ySrc} H ${xMid} V ${yTarget}`);
        drew = true;
      }
      if (drew) paths.push(`M ${xMid} ${yTarget} H ${xLeft}`);
    }

    return paths;
  }, [rounds, matches, roundSlotHeights]);

  return (
    <Card className="glass-card rounded-xl animate-entrance shadow-md">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-primary">{title}</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto pb-4">
        <div style={{ position: 'relative', width: totalWidth, height: totalHeight, minWidth: totalWidth }}>
          <svg
            style={{ position: 'absolute', inset: 0, width: totalWidth, height: totalHeight, pointerEvents: 'none' }}
          >
            {connectorPaths.map((d, i) => (
              <path key={i} d={d} fill="none" stroke="var(--color-border)" strokeWidth={1.5} />
            ))}
          </svg>

          {rounds.map((r, ri) => {
            const roundMatches = matchesByRound.get(r) ?? [];
            const x = ri * (MATCH_CARD_W + COL_GAP);
            const isFinalRound = r === finalRoundNo;
            const roundLabel = isFinalRound && finalLabel
              ? finalLabel
              : r === 1
              ? `${(roundMatches.length * 2)}강`
              : roundMatches.length === 1
              ? '결승'
              : `${roundMatches.length * 2}강`;

            return (
              <div key={r} style={{ position: 'absolute', left: x, top: 0, width: MATCH_CARD_W }}>
                <div className="text-[10px] text-center text-muted-foreground mb-1 font-medium">
                  {roundLabel}
                </div>
                {roundMatches.map((match) => {
                  const cy = slotCenter(match.id, r);
                  const fl = feederLabels.get(match.id);
                  return (
                    <div
                      key={match.id}
                      style={{ position: 'absolute', top: cy - MATCH_CARD_H / 2, left: 0, width: MATCH_CARD_W }}
                    >
                      <MatchCard match={match} isFinal={isFinalRound} globalNo={globalMatchNos.get(match.id)} team1Label={fl?.team1} team2Label={fl?.team2} />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default function StudentTournamentBracketPageClient({ sessionId }: Props) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  const [title, setTitle] = useState<string>('');
  const [matches, setMatches] = useState<TournamentMatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace('/login');
  }, [isLoading, isAuthenticated, router]);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const bracket = await tournamentsApi.getBracket(sessionId);
      setMatches(bracket.rounds.flatMap((r) => r.matches));
      setTitle(bracket.title);
    } catch {
      setError('대진표를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadPage();
  }, [isAuthenticated, loadPage]);

  // SSE 실시간 업데이트
  useEffect(() => {
    if (!isAuthenticated) return;
    const source = createTournamentMatchStatusSse((payload) => {
      if (payload.session_id !== sessionId) return;
      void loadPage();
    });
    return () => source.close();
  }, [isAuthenticated, sessionId, loadPage]);

  const { wbRounds, lbRounds } = useMemo(() => {
    const wbSet = new Set<number>();
    const lbSet = new Set<number>();
    for (const m of matches) {
      if (m.bracket_type === 'losers') lbSet.add(m.round_no);
      else wbSet.add(m.round_no);
    }
    return {
      wbRounds: Array.from(wbSet).sort((a, b) => a - b),
      lbRounds: Array.from(lbSet).sort((a, b) => a - b),
    };
  }, [matches]);

  const wbMatches = useMemo(() => matches.filter((m) => m.bracket_type !== 'losers'), [matches]);
  const lbMatches = useMemo(() => matches.filter((m) => m.bracket_type === 'losers'), [matches]);
  const lbFinalRoundNo = lbRounds.length > 0 ? Math.max(...lbRounds) : -1;

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }
  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-[1400px] px-6 py-8 space-y-6">
        <PageHeader
          title={title || '토너먼트 대진표'}
          description="실시간으로 대진표 현황을 확인할 수 있습니다."
          actions={
            <Button asChild type="button" size="icon" variant="outline" aria-label="목록으로">
              <Link href="/tournaments">
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

        {loading ? (
          <Card>
            <CardContent className="py-12 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </CardContent>
          </Card>
        ) : matches.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-sm text-muted-foreground text-center">
              아직 대진이 생성되지 않았습니다.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-8">
            {wbRounds.length > 0 ? (
              <BracketSection
                title="승자 조 — 최종 승자 1팀이 우승"
                rounds={wbRounds}
                matches={wbMatches}
                allMatches={matches}
                finalRoundNo={Math.max(...wbRounds)}
                finalLabel="결승"
              />
            ) : null}

            {lbRounds.length > 0 ? (
              <>
                <div className="flex items-center gap-3">
                  <div className="h-px flex-1 bg-border/40" />
                  <span className="text-xs text-muted-foreground font-medium">패자부활전 (Losers Bracket)</span>
                  <div className="h-px flex-1 bg-border/40" />
                </div>
                <BracketSection
                  title={`패자 조 — 최종 승자 2팀이 공동 3위`}
                  rounds={lbRounds}
                  matches={lbMatches}
                  allMatches={matches}
                  finalRoundNo={lbFinalRoundNo}
                  finalLabel="패자 결승 (공동 3위)"
                />
              </>
            ) : null}
          </div>
        )}

        {matches.length > 0 ? (
          <Card className="border-border/40">
            <CardContent className="py-3 flex flex-wrap gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Badge variant="outline" className="h-4 text-[10px] px-1.5">대기</Badge>경기 미시작
              </span>
              <span className="flex items-center gap-1.5">
                <Badge className="h-4 text-[10px] px-1.5 bg-yellow-400/20 text-yellow-700 border-yellow-400/40">진행중</Badge>투표 접수 중
              </span>
              <span className="flex items-center gap-1.5">
                <Badge className="h-4 text-[10px] px-1.5 bg-green-500/20 text-green-700 border-green-500/40">완료</Badge>결과 확정
              </span>
              <span className="flex items-center gap-1.5">
                <Trophy className="h-3 w-3 text-primary" />승자 팀
              </span>
            </CardContent>
          </Card>
        ) : null}
      </main>
    </div>
  );
}
