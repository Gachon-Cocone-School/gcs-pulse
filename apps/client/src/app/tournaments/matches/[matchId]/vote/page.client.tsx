'use client';

import { redirect } from 'next/navigation';
import { useCallback, useEffect, useReducer } from 'react';
import { Loader2 } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TournamentVoteResultBarChart } from '@/components/views/TournamentVoteResultBarChart';
import { useAuth } from '@/context/auth-context';
import { ApiError, createTournamentMatchStatusSse, tournamentsApi } from '@/lib/api';
import type { TournamentMatchItem } from '@/lib/types';

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
  | { type: 'SSE_OPENED' };

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
      return { ...state, submitting: false, match: action.match, success: '투표가 제출되었습니다.' };
    case 'SUBMIT_ERROR':
      return { ...state, submitting: false, error: action.error };
    case 'SSE_CLOSED':
      return { ...state, error: state.error ?? '현재 투표 가능한 경기가 아닙니다.', success: null };
    case 'SSE_OPENED':
      return { ...state, error: null };
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
};

export default function TournamentMatchVotePageClient({ matchId }: TournamentMatchVotePageClientProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const [state, dispatch] = useReducer(reducer, initialState);
  const { match, selectedTeamId, loading, submitting, error, success } = state;

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

      if (payload.session_is_open && payload.match_status === 'open') {
        dispatch({ type: 'SSE_OPENED' });
      } else {
        dispatch({ type: 'SSE_CLOSED' });
      }
      void loadMatch();
    });

    return () => {
      source.close();
    };
  }, [isAuthenticated, match?.id, loadMatch]);

  const handleSubmit = useCallback(async () => {
    if (!match || selectedTeamId === null) {
      dispatch({ type: 'SUBMIT_ERROR', error: '투표 팀을 선택해 주세요.' });
      return;
    }

    dispatch({ type: 'SUBMIT_START' });
    try {
      const response = await tournamentsApi.submitVote(match.id, { selected_team_id: selectedTeamId });
      dispatch({ type: 'SUBMIT_SUCCESS', match: response.match });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        dispatch({ type: 'SUBMIT_ERROR', error: e.message || '현재 투표 가능한 경기가 아닙니다.' });
        await loadMatch();
      } else {
        console.error(e);
        dispatch({ type: 'SUBMIT_ERROR', error: '투표 제출에 실패했습니다.' });
      }
    }
  }, [match, selectedTeamId, loadMatch]);

  const canVote = Boolean(match && match.session_is_open !== false && match.status === 'open' && !match.is_bye);

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

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-3xl px-6 py-8 space-y-6">
        <PageHeader
          title="토너먼트 경기 투표"
          description="개시된 경기에서만 투표할 수 있습니다."
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
                          onChange={() => dispatch({ type: 'SELECT_TEAM', teamId: match.team1_id ?? null })}
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
                          onChange={() => dispatch({ type: 'SELECT_TEAM', teamId: match.team2_id ?? null })}
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
