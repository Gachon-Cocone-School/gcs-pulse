'use client';

import Link from 'next/link';
import { redirect, useRouter } from 'next/navigation';
import { useCallback, useEffect, useReducer } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/context/auth-context';
import { tournamentsApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type {
  TournamentParsePreviewMember,
  TournamentParseUnresolvedItem,
  TournamentSessionResponse,
  TournamentTeamItem,
  TournamentTeamMemberItem,
} from '@/lib/types';

interface ProfessorTournamentEditPageClientProps {
  sessionId: number | null;
}

const BRACKET_SIZES = [4, 8, 16, 32] as const;
type BracketSize = (typeof BRACKET_SIZES)[number];

function flattenTeams(teams: Record<string, TournamentParsePreviewMember[]>): TournamentParsePreviewMember[] {
  return Object.values(teams).flat();
}

function toMembersFromSession(session: TournamentSessionResponse): TournamentParsePreviewMember[] {
  return session.teams.flatMap((team: TournamentTeamItem) =>
    team.members.map((member: TournamentTeamMemberItem) => ({
      team_name: team.team_name,
      raw_name: member.student_name,
      student_user_id: member.student_user_id,
      student_name: member.student_name,
      student_email: member.student_email,
      can_attend_vote: member.can_attend_vote,
    })),
  );
}

function serializeMembersAsRawText(members: TournamentParsePreviewMember[]): string {
  const grouped = new Map<string, string[]>();
  for (const member of members) {
    if (!grouped.has(member.team_name)) {
      grouped.set(member.team_name, []);
    }
    grouped.get(member.team_name)!.push(member.student_name);
  }

  return Array.from(grouped.entries())
    .map(([teamName, names]) => `${teamName}: ${names.join(', ')}`)
    .join('\n');
}

function resolveReasonLabel(reason: string): string {
  if (reason === 'name_not_found') return '이름을 찾을 수 없음';
  if (reason === 'ambiguous_name') return '동명이인 후보 다수';
  if (reason === 'student_in_multiple_teams') return '한 학생이 여러 팀에 배정됨';
  return reason;
}

function unresolvedKey(item: TournamentParseUnresolvedItem): string {
  return `${item.team_name}::${item.raw_name}::${item.reason}`;
}

function parseBracketSize(value: unknown): BracketSize {
  const n = Number(value);
  return (BRACKET_SIZES as readonly number[]).includes(n) ? (n as BracketSize) : 8;
}

type EditState = {
  loading: boolean;
  saving: boolean;
  parsingMembers: boolean;
  title: string;
  rawMembersText: string;
  bracketSize: BracketSize;
  repechage: boolean;
  allowSelfVote: boolean;
  parsedMembers: TournamentParsePreviewMember[];
  unresolvedMembers: TournamentParseUnresolvedItem[];
  unresolvedSelections: Record<string, number | null>;
  error: string | null;
};

type EditAction =
  | { type: 'LOADING_DONE' }
  | { type: 'SESSION_LOADED'; title: string; bracketSize: BracketSize; repechage: boolean; allowSelfVote: boolean; parsedMembers: TournamentParsePreviewMember[]; rawMembersText: string }
  | { type: 'SESSION_LOAD_ERROR' }
  | { type: 'SET_TITLE'; value: string }
  | { type: 'SET_RAW_MEMBERS_TEXT'; value: string }
  | { type: 'SET_BRACKET_SIZE'; value: BracketSize }
  | { type: 'SET_REPECHAGE'; value: boolean }
  | { type: 'SET_ALLOW_SELF_VOTE'; value: boolean }
  | { type: 'PARSE_START' }
  | { type: 'PARSE_SUCCESS'; parsedMembers: TournamentParsePreviewMember[]; unresolvedMembers: TournamentParseUnresolvedItem[] }
  | { type: 'PARSE_ERROR' }
  | { type: 'RESOLVE_UNRESOLVED'; key: string; studentUserId: number }
  | { type: 'SAVE_START' }
  | { type: 'SAVE_ERROR' }
  | { type: 'SET_ERROR'; error: string };

function editReducer(state: EditState, action: EditAction): EditState {
  switch (action.type) {
    case 'LOADING_DONE':
      return { ...state, loading: false };
    case 'SESSION_LOADED':
      return { ...state, loading: false, title: action.title, bracketSize: action.bracketSize, repechage: action.repechage, allowSelfVote: action.allowSelfVote, parsedMembers: action.parsedMembers, rawMembersText: action.rawMembersText, unresolvedMembers: [], unresolvedSelections: {}, error: null };
    case 'SESSION_LOAD_ERROR':
      return { ...state, loading: false, error: '세션 정보를 불러오지 못했습니다.' };
    case 'SET_TITLE':
      return { ...state, title: action.value };
    case 'SET_RAW_MEMBERS_TEXT':
      return { ...state, rawMembersText: action.value };
    case 'SET_BRACKET_SIZE': {
      // 브라켓이 8 미만이 되면 패자부활전 자동 해제
      const repechage = action.value >= 8 ? state.repechage : false;
      return { ...state, bracketSize: action.value, repechage };
    }
    case 'SET_REPECHAGE':
      return { ...state, repechage: action.value };
    case 'SET_ALLOW_SELF_VOTE':
      return { ...state, allowSelfVote: action.value };
    case 'PARSE_START':
      return { ...state, parsingMembers: true, error: null };
    case 'PARSE_SUCCESS': {
      const selections: Record<string, number | null> = {};
      for (const item of action.unresolvedMembers) {
        if (item.reason === 'ambiguous_name') {
          const key = unresolvedKey(item);
          selections[key] = item.candidates.length === 1 ? item.candidates[0].student_user_id : null;
        }
      }
      return { ...state, parsingMembers: false, parsedMembers: action.parsedMembers, unresolvedMembers: action.unresolvedMembers, unresolvedSelections: selections };
    }
    case 'PARSE_ERROR':
      return { ...state, parsingMembers: false, error: '팀 구성 파싱에 실패했습니다.' };
    case 'RESOLVE_UNRESOLVED':
      return { ...state, unresolvedSelections: { ...state.unresolvedSelections, [action.key]: action.studentUserId } };
    case 'SAVE_START':
      return { ...state, saving: true, error: null };
    case 'SAVE_ERROR':
      return { ...state, saving: false, error: '저장에 실패했습니다.' };
    case 'SET_ERROR':
      return { ...state, error: action.error };
    default:
      return state;
  }
}

export default function ProfessorTournamentEditPageClient({ sessionId }: ProfessorTournamentEditPageClientProps) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const [state, dispatch] = useReducer(editReducer, {
    loading: true,
    saving: false,
    parsingMembers: false,
    title: '',
    rawMembersText: '',
    bracketSize: 8,
    repechage: false,
    allowSelfVote: true,
    parsedMembers: [],
    unresolvedMembers: [],
    unresolvedSelections: {},
    error: null,
  });
  const { loading, saving, parsingMembers, title, rawMembersText, bracketSize, repechage, allowSelfVote, parsedMembers, unresolvedMembers, unresolvedSelections, error } = state;

  const loadSession = useCallback(async () => {
    if (sessionId === null) {
      dispatch({ type: 'LOADING_DONE' });
      return;
    }

    try {
      const session = await tournamentsApi.getSession(sessionId);
      const members = toMembersFromSession(session);
      const fj = session.format_json as Record<string, unknown> | null | undefined;
      const bs = parseBracketSize(fj?.bracket_size);
      const rep = Boolean((fj?.repechage as Record<string, unknown> | undefined)?.enabled);
      dispatch({
        type: 'SESSION_LOADED',
        title: session.title,
        bracketSize: bs,
        repechage: rep,
        allowSelfVote: session.allow_self_vote ?? true,
        parsedMembers: members,
        rawMembersText: serializeMembersAsRawText(members),
      });
    } catch (e) {
      console.error(e);
      dispatch({ type: 'SESSION_LOAD_ERROR' });
    }
  }, [sessionId]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadSession();
  }, [isAuthenticated, loadSession]);

  const parseMembers = useCallback(async () => {
    const normalizedText = rawMembersText.trim();
    if (!normalizedText) {
      dispatch({ type: 'SET_ERROR', error: '팀 구성을 입력해 주세요.' });
      return;
    }

    dispatch({ type: 'PARSE_START' });
    try {
      const response = sessionId === null
        ? await tournamentsApi.parseMembersDraft({ raw_text: normalizedText })
        : await tournamentsApi.parseMembers(sessionId, { raw_text: normalizedText });

      dispatch({ type: 'PARSE_SUCCESS', parsedMembers: flattenTeams(response.teams), unresolvedMembers: response.unresolved_members });
    } catch (e) {
      console.error(e);
      dispatch({ type: 'PARSE_ERROR' });
    }
  }, [sessionId, rawMembersText]);

  const saveAll = useCallback(async () => {
    const normalizedTitle = title.trim();

    if (!normalizedTitle) {
      dispatch({ type: 'SET_ERROR', error: '세션 제목을 입력해 주세요.' });
      return;
    }
    if (parsedMembers.length === 0 && unresolvedMembers.length === 0) {
      dispatch({ type: 'SET_ERROR', error: '팀 구성 체크를 먼저 실행해 주세요.' });
      return;
    }

    const nonAmbiguous = unresolvedMembers.filter((i) => i.reason !== 'ambiguous_name');
    if (nonAmbiguous.length > 0) {
      dispatch({ type: 'SET_ERROR', error: '미해결 팀원이 있어 저장할 수 없습니다. 원문을 수정해 다시 체크해 주세요.' });
      return;
    }

    const ambiguous = unresolvedMembers.filter((i) => i.reason === 'ambiguous_name');
    const unselected = ambiguous.filter((i) => !unresolvedSelections[unresolvedKey(i)]);
    if (unselected.length > 0) {
      dispatch({ type: 'SET_ERROR', error: '동명이인 후보를 모두 선택해 주세요.' });
      return;
    }

    const resolvedMembers: TournamentParsePreviewMember[] = ambiguous.map((item) => {
      const selectedId = unresolvedSelections[unresolvedKey(item)];
      const candidate = item.candidates.find((c) => c.student_user_id === selectedId)!;
      return {
        team_name: item.team_name,
        raw_name: item.raw_name,
        student_user_id: candidate.student_user_id,
        student_name: candidate.student_name,
        student_email: candidate.student_email,
        can_attend_vote: true,
      };
    });

    dispatch({ type: 'SAVE_START' });

    try {
      let targetSessionId = sessionId;

      if (targetSessionId === null) {
        const created = await tournamentsApi.createSession({ title: normalizedTitle, allow_self_vote: allowSelfVote });
        targetSessionId = created.id;
      } else {
        await tournamentsApi.updateSession(targetSessionId, { title: normalizedTitle, allow_self_vote: allowSelfVote });
      }

      await Promise.all([
        tournamentsApi.confirmMembers(targetSessionId, {
          members: [...parsedMembers, ...resolvedMembers],
          unresolved_members: [],
        }),
        tournamentsApi.setFormat(targetSessionId, {
          bracket_size: bracketSize,
          repechage,
        }),
      ]);

      router.replace(`/professor/tournaments/${targetSessionId}/edit`);
    } catch (e) {
      console.error(e);
      dispatch({ type: 'SAVE_ERROR' });
    }
  }, [sessionId, bracketSize, repechage, parsedMembers, unresolvedMembers, unresolvedSelections, router, title, allowSelfVote]);

  const ambiguousCount = unresolvedMembers.filter((i) => i.reason === 'ambiguous_name').length;
  const teamCount = new Set(parsedMembers.map((member) => member.team_name)).size;
  const isBusy = saving || parsingMembers;

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
        <PageHeader
          title="토너먼트 세션 편집"
          description="팀 구성과 대진 방식을 확인한 뒤 저장합니다."
          actions={
            <div className="flex flex-wrap gap-2">
              <Button asChild type="button" size="icon" variant="outline" aria-label="목록으로" title="목록으로" disabled={isBusy}>
                <Link href="/professor/tournaments">
                  <ArrowLeft className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                type="button"
                onClick={() => {
                  void saveAll();
                }}
                disabled={isBusy}
              >
                {saving ? '저장 중...' : '저장'}
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
        ) : (
          <>
            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
              <CardHeader>
                <CardTitle className="text-base">기본 설정</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="tournament-title">세션 제목</Label>
                  <Input
                    id="tournament-title"
                    value={title}
                    onChange={(event) => dispatch({ type: 'SET_TITLE', value: event.target.value })}
                    placeholder="세션 제목"
                    disabled={isBusy}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tournament-members-raw">팀 구성</Label>
                  <Textarea
                    id="tournament-members-raw"
                    value={rawMembersText}
                    onChange={(event) => dispatch({ type: 'SET_RAW_MEMBERS_TEXT', value: event.target.value })}
                    placeholder="예) A팀: 홍길동, 김민수\nB팀: 박서연, 이수민"
                    className="min-h-36"
                    disabled={isBusy}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tournament-bracket-size">브라켓 크기</Label>
                  <select
                    id="tournament-bracket-size"
                    value={bracketSize}
                    onChange={(e) => dispatch({ type: 'SET_BRACKET_SIZE', value: parseBracketSize(e.target.value) })}
                    disabled={isBusy}
                    className="flex h-9 w-full max-w-[160px] rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
                  >
                    {BRACKET_SIZES.map((n) => (
                      <option key={n} value={n}>{n}강</option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-3">
                    <input
                      id="tournament-repechage"
                      type="checkbox"
                      checked={repechage}
                      onChange={(e) => dispatch({ type: 'SET_REPECHAGE', value: e.target.checked })}
                      disabled={isBusy || bracketSize < 8}
                      className="h-4 w-4 accent-primary"
                    />
                    <Label htmlFor="tournament-repechage" className={`cursor-pointer ${bracketSize < 8 ? 'text-muted-foreground' : ''}`}>
                      패자부활전 (더블 엘리미네이션){bracketSize < 8 ? ' — 8강 이상에서만 사용 가능' : ''}
                    </Label>
                  </div>

                  <div className="flex items-center gap-3">
                    <input
                      id="tournament-allow-self-vote"
                      type="checkbox"
                      checked={allowSelfVote}
                      onChange={(e) => dispatch({ type: 'SET_ALLOW_SELF_VOTE', value: e.target.checked })}
                      disabled={isBusy}
                      className="h-4 w-4 accent-primary"
                    />
                    <Label htmlFor="tournament-allow-self-vote" className="cursor-pointer">
                      출전 팀원도 본인 경기에 투표 가능
                    </Label>
                  </div>
                </div>

                <Button
                  type="button"
                  onClick={() => {
                    void parseMembers();
                  }}
                  disabled={saving || parsingMembers}
                >
                  {parsingMembers ? '팀 구성 체크 중...' : '팀 구성 체크하기'}
                </Button>
              </CardContent>
            </Card>

            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
              <CardHeader>
                <CardTitle className="text-base">파싱 결과</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>확정 가능한 팀: {teamCount}개</div>
                <div>확정 가능한 팀원: {parsedMembers.length}명</div>
                <div>미해결 팀원: {unresolvedMembers.length}명</div>
                {unresolvedMembers.length > 0 ? (
                  <div className="space-y-3">
                    {unresolvedMembers.map((item) => {
                      const key = unresolvedKey(item);
                      return (
                        <div key={key} className="rounded-lg border border-border/70 bg-card/80 p-3 space-y-2">
                          <div className="text-sm">
                            {item.team_name} · {item.raw_name} ({resolveReasonLabel(item.reason)})
                          </div>
                          {item.reason === 'ambiguous_name' && item.candidates.length > 0 ? (
                            <div className="flex flex-col gap-2">
                              {item.candidates.map((candidate) => (
                                <label key={`${key}-${candidate.student_user_id}`} className="flex items-center gap-2 text-sm">
                                  <input
                                    type="radio"
                                    name={key}
                                    value={candidate.student_user_id}
                                    checked={unresolvedSelections[key] === candidate.student_user_id}
                                    onChange={() => dispatch({ type: 'RESOLVE_UNRESOLVED', key, studentUserId: candidate.student_user_id })}
                                    disabled={isBusy}
                                    className="accent-primary"
                                  />
                                  <span>{candidate.student_name}</span>
                                  <span className="text-muted-foreground text-xs">{candidate.student_email}</span>
                                </label>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                ) : null}
                {ambiguousCount > 0 ? (
                  <div className="text-xs text-muted-foreground">동명이인 항목을 선택하면 저장할 수 있습니다.</div>
                ) : null}
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
