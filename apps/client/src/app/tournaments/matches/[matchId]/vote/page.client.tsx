'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useReducer, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TournamentVoteResultBarChart } from '@/components/views/TournamentVoteResultBarChart';
import { useAuth } from '@/context/auth-context';
import { ApiError, createTournamentMatchStatusSse, tournamentsApi } from '@/lib/api';
import type { TournamentMatchItem, TournamentMyScoreResponse } from '@/lib/types';

interface TournamentMatchVotePageClientProps {
  matchId: number;
}

type State = {
  match: TournamentMatchItem | null;
  selectedTeamId: number | null;
  loading: boolean;
  submitting: boolean;
  error: string | null;
  success: string | null;
  hasVoted: boolean;
};

type Action =
  | { type: 'LOAD_START' }
  | { type: 'LOAD_SUCCESS'; match: TournamentMatchItem }
  | { type: 'LOAD_ERROR'; error: string }
  | { type: 'SELECT_TEAM'; teamId: number | null }
  | { type: 'SUBMIT_START' }
  | { type: 'SUBMIT_SUCCESS'; match: TournamentMatchItem }
  | { type: 'SUBMIT_ERROR'; error: string }
  | { type: 'SSE_CLOSED' }
  | { type: 'SSE_OPENED' }
  | { type: 'SET_HAS_VOTED'; selectedTeamId: number | null };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'LOAD_START':
      return { ...state, loading: true, error: null };
    case 'LOAD_SUCCESS':
      return {
        ...state,
        loading: false,
        match: action.match,
        selectedTeamId: state.selectedTeamId ?? action.match.team1_id ?? action.match.team2_id ?? null,
      };
    case 'LOAD_ERROR':
      return { ...state, loading: false, error: action.error };
    case 'SELECT_TEAM':
      return { ...state, selectedTeamId: action.teamId };
    case 'SUBMIT_START':
      return { ...state, submitting: true, error: null, success: null };
    case 'SUBMIT_SUCCESS':
      return { ...state, submitting: false, match: action.match, success: '투표가 제출되었습니다.', hasVoted: true };
    case 'SUBMIT_ERROR':
      return { ...state, submitting: false, error: action.error };
    case 'SSE_CLOSED':
      return { ...state, error: state.error ?? '현재 투표 가능한 경기가 아닙니다.', success: null };
    case 'SSE_OPENED':
      return { ...state, error: null };
    case 'SET_HAS_VOTED':
      return {
        ...state,
        hasVoted: true,
        success: '투표가 제출되었습니다.',
        selectedTeamId: action.selectedTeamId ?? state.selectedTeamId,
      };
    default:
      return state;
  }
}

const initialState: State = {
  match: null,
  selectedTeamId: null,
  loading: true,
  submitting: false,
  error: null,
  success: null,
  hasVoted: false,
};

export default function TournamentMatchVotePageClient({ matchId }: TournamentMatchVotePageClientProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [state, dispatch] = useReducer(reducer, initialState);
  const { match, selectedTeamId, loading, submitting, error, success, hasVoted } = state;
  const [myScore, setMyScore] = useState<TournamentMyScoreResponse | null>(null);

  const loadMatch = useCallback(async () => {
    dispatch({ type: 'LOAD_START' });
    try {
      const response = await tournamentsApi.getMatch(matchId);
      dispatch({ type: 'LOAD_SUCCESS', match: response });
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) {
        dispatch({ type: 'LOAD_ERROR', error: '서버에 연결하지 못했습니다. 네트워크 또는 브라우저 CORS/쿠키 설정을 확인해 주세요.' });
      } else {
        console.error(e);
        dispatch({ type: 'LOAD_ERROR', error: '경기 정보를 불러오지 못했습니다.' });
      }
    }
  }, [matchId]);

  const loadMyScore = useCallback(async (sessionId: number) => {
    try {
      const response = await tournamentsApi.getMyScore(sessionId);
      setMyScore(response);
    } catch {
      // 점수 로드 실패는 무시
    }
  }, []);

  const loadMyVote = useCallback(async () => {
    try {
      const response = await tournamentsApi.getMyVote(matchId);
      if (response.has_voted) {
        dispatch({ type: 'SET_HAS_VOTED', selectedTeamId: response.selected_team_id });
      }
    } catch {
      // 투표 여부 조회 실패는 무시
    }
  }, [matchId]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login?next=' + encodeURIComponent('/tournaments/matches/' + matchId + '/vote'));
    }
  }, [isLoading, isAuthenticated, router, matchId]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadMatch();
  }, [isAuthenticated, loadMatch]);

  // match가 로드된 후 점수/랭킹 + 내 투표 여부 조회
  useEffect(() => {
    if (!isAuthenticated || !match?.session_id) return;
    void loadMyScore(match.session_id);
    void loadMyVote();
  }, [isAuthenticated, match?.session_id, loadMyScore, loadMyVote]);

  useEffect(() => {
    if (!isAuthenticated || !match?.id) {
      return;
    }

    const currentMatchId = match.id;
    const currentSessionId = match.session_id;
    const source = createTournamentMatchStatusSse((payload) => {
      if (payload.match_id !== currentMatchId) {
        return;
      }

      if (payload.match_status === 'open') {
        dispatch({ type: 'SSE_OPENED' });
      } else {
        dispatch({ type: 'SSE_CLOSED' });
      }
      void loadMatch();
      void loadMyScore(currentSessionId);
    });

    return () => {
      source.close();
    };
  }, [isAuthenticated, match?.id, match?.session_id, loadMatch, loadMyScore]);

  const handleSubmit = useCallback(async () => {
    if (!match || selectedTeamId === null) {
      dispatch({ type: 'SUBMIT_ERROR', error: '투표 팀을 선택해 주세요.' });
      return;
    }

    dispatch({ type: 'SUBMIT_START' });
    try {
      const response = await tournamentsApi.submitVote(match.id, { selected_team_id: selectedTeamId });
      dispatch({ type: 'SUBMIT_SUCCESS', match: response.match });
      void loadMyScore(match.session_id);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        dispatch({ type: 'SUBMIT_ERROR', error: e.message || '현재 투표 가능한 경기가 아닙니다.' });
        await loadMatch();
      } else {
        console.error(e);
        dispatch({ type: 'SUBMIT_ERROR', error: '투표 제출에 실패했습니다.' });
      }
    }
  }, [match, selectedTeamId, loadMatch, loadMyScore]);

  const hasFullTeams = Boolean(match?.team1_id && match?.team2_id);
  const canVote = Boolean(match && match.status === 'open' && !match.is_bye && hasFullTeams);

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
        <PageHeader
          title="토너먼트 경기 투표"
          description=""
          actions={null}
        />

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

        {myScore ? (
          <Card className="glass-card rounded-xl border-0 shadow-md">
            <CardContent className="py-4 flex items-center justify-between gap-4">
              <div className="text-center">
                <div className="text-xs text-muted-foreground mb-1">내 점수</div>
                <div className="text-2xl font-bold tabular-nums">
                  {myScore.my_score}
                  <span className="text-sm font-normal text-muted-foreground">/{myScore.total_matches}</span>
                </div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div className="text-center">
                <div className="text-xs text-muted-foreground mb-1">내 등수</div>
                <div className="text-2xl font-bold tabular-nums">
                  {myScore.my_rank}
                  <span className="text-sm font-normal text-muted-foreground">위</span>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  ({myScore.cumulative_response_seconds.toFixed(1)}초)
                </div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div className="text-center">
                <div className="text-xs text-muted-foreground mb-1">참여자</div>
                <div className="text-2xl font-bold tabular-nums">
                  {myScore.total_voters}
                  <span className="text-sm font-normal text-muted-foreground">명</span>
                </div>
              </div>
            </CardContent>
          </Card>
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
              {match.status === 'pending' || (!hasFullTeams && match.status !== 'closed') ? (
                <div className="text-sm text-muted-foreground">
                  {!hasFullTeams
                    ? '대진 상대가 아직 결정되지 않았습니다. 상위 라운드가 완료되면 투표가 시작됩니다.'
                    : '아직 투표가 시작되지 않았습니다.'}
                </div>
              ) : canVote ? (
                <>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 rounded-lg border border-border/70 p-3">
                      <input
                        type="radio"
                        checked={selectedTeamId === match.team1_id}
                        onChange={() => dispatch({ type: 'SELECT_TEAM', teamId: match.team1_id ?? null })}
                        disabled={submitting}
                      />
                      <span>{match.team1_name || `Team ${match.team1_id}`}</span>
                    </label>
                    <label className="flex items-center gap-2 rounded-lg border border-border/70 p-3">
                      <input
                        type="radio"
                        checked={selectedTeamId === match.team2_id}
                        onChange={() => dispatch({ type: 'SELECT_TEAM', teamId: match.team2_id ?? null })}
                        disabled={submitting}
                      />
                      <span>{match.team2_name || `Team ${match.team2_id}`}</span>
                    </label>
                  </div>

                  <Button
                    type="button"
                    onClick={() => { void handleSubmit(); }}
                    disabled={submitting}
                  >
                    {submitting ? '제출 중...' : hasVoted ? '다시 제출' : '투표 제출'}
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
