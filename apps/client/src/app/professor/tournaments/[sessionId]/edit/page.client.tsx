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
} from '@/lib/types';

interface ProfessorTournamentEditPageClientProps {
  sessionId: number | null;
}

function flattenTeams(teams: Record<string, TournamentParsePreviewMember[]>): TournamentParsePreviewMember[] {
  return Object.values(teams).flat();
}

function toMembersFromSession(session: TournamentSessionResponse): TournamentParsePreviewMember[] {
  return session.teams.flatMap((team) =>
    team.members.map((member) => ({
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

type EditState = {
  loading: boolean;
  saving: boolean;
  parsingMembers: boolean;
  title: string;
  rawMembersText: string;
  formatText: string;
  allowSelfVote: boolean;
  parsedMembers: TournamentParsePreviewMember[];
  unresolvedMembers: TournamentParseUnresolvedItem[];
  error: string | null;
};

type EditAction =
  | { type: 'LOADING_DONE' }
  | { type: 'SESSION_LOADED'; title: string; formatText: string; allowSelfVote: boolean; parsedMembers: TournamentParsePreviewMember[]; rawMembersText: string }
  | { type: 'SESSION_LOAD_ERROR' }
  | { type: 'SET_TITLE'; value: string }
  | { type: 'SET_RAW_MEMBERS_TEXT'; value: string }
  | { type: 'SET_FORMAT_TEXT'; value: string }
  | { type: 'SET_ALLOW_SELF_VOTE'; value: boolean }
  | { type: 'PARSE_START' }
  | { type: 'PARSE_SUCCESS'; parsedMembers: TournamentParsePreviewMember[]; unresolvedMembers: TournamentParseUnresolvedItem[] }
  | { type: 'PARSE_ERROR' }
  | { type: 'SAVE_START' }
  | { type: 'SAVE_ERROR' }
  | { type: 'SET_ERROR'; error: string };

function editReducer(state: EditState, action: EditAction): EditState {
  switch (action.type) {
    case 'LOADING_DONE':
      return { ...state, loading: false };
    case 'SESSION_LOADED':
      return { ...state, loading: false, title: action.title, formatText: action.formatText, allowSelfVote: action.allowSelfVote, parsedMembers: action.parsedMembers, rawMembersText: action.rawMembersText, unresolvedMembers: [], error: null };
    case 'SESSION_LOAD_ERROR':
      return { ...state, loading: false, error: '세션 정보를 불러오지 못했습니다.' };
    case 'SET_TITLE':
      return { ...state, title: action.value };
    case 'SET_RAW_MEMBERS_TEXT':
      return { ...state, rawMembersText: action.value };
    case 'SET_FORMAT_TEXT':
      return { ...state, formatText: action.value };
    case 'SET_ALLOW_SELF_VOTE':
      return { ...state, allowSelfVote: action.value };
    case 'PARSE_START':
      return { ...state, parsingMembers: true, error: null };
    case 'PARSE_SUCCESS':
      return { ...state, parsingMembers: false, parsedMembers: action.parsedMembers, unresolvedMembers: action.unresolvedMembers };
    case 'PARSE_ERROR':
      return { ...state, parsingMembers: false, error: '팀 구성 파싱에 실패했습니다.' };
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
    formatText: '2자대결 16강 패자부활전',
    allowSelfVote: true,
    parsedMembers: [],
    unresolvedMembers: [],
    error: null,
  });
  const { loading, saving, parsingMembers, title, rawMembersText, formatText, allowSelfVote, parsedMembers, unresolvedMembers, error } = state;

  const loadSession = useCallback(async () => {
    if (sessionId === null) {
      dispatch({ type: 'LOADING_DONE' });
      return;
    }

    try {
      const session = await tournamentsApi.getSession(sessionId);
      const members = toMembersFromSession(session);
      dispatch({
        type: 'SESSION_LOADED',
        title: session.title,
        formatText: session.format_text || '2자대결 16강 패자부활전',
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
    const normalizedFormatText = formatText.trim();

    if (!normalizedTitle) {
      dispatch({ type: 'SET_ERROR', error: '세션 제목을 입력해 주세요.' });
      return;
    }
    if (!normalizedFormatText) {
      dispatch({ type: 'SET_ERROR', error: '대진 방식 텍스트를 입력해 주세요.' });
      return;
    }
    if (parsedMembers.length === 0) {
      dispatch({ type: 'SET_ERROR', error: '팀 구성 체크를 먼저 실행해 주세요.' });
      return;
    }
    if (unresolvedMembers.length > 0) {
      dispatch({ type: 'SET_ERROR', error: '미해결 팀원이 있어 저장할 수 없습니다. 원문을 수정해 다시 체크해 주세요.' });
      return;
    }

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
          members: parsedMembers,
          unresolved_members: [],
        }),
        tournamentsApi.parseFormat(targetSessionId, {
          format_text: normalizedFormatText,
        }),
      ]);

      router.replace(`/professor/tournaments/${targetSessionId}/edit`);
    } catch (e) {
      console.error(e);
      dispatch({ type: 'SAVE_ERROR' });
    }
  }, [sessionId, formatText, parsedMembers, router, title, unresolvedMembers.length, allowSelfVote]);

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
                  <Label htmlFor="tournament-format-text">대진 방식 텍스트</Label>
                  <Input
                    id="tournament-format-text"
                    value={formatText}
                    onChange={(event) => dispatch({ type: 'SET_FORMAT_TEXT', value: event.target.value })}
                    placeholder="예) 2자대결 16강 패자부활전"
                    disabled={isBusy}
                  />
                </div>

                <div className="flex items-center gap-3">
                  <input
                    id="tournament-allow-self-vote"
                    type="checkbox"
                    checked={allowSelfVote}
                    onChange={(event) => dispatch({ type: 'SET_ALLOW_SELF_VOTE', value: event.target.checked })}
                    disabled={isBusy}
                    className="h-4 w-4 accent-primary"
                  />
                  <Label htmlFor="tournament-allow-self-vote" className="cursor-pointer">
                    출전 팀원도 본인 경기에 투표 가능
                  </Label>
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
                  <div className="rounded-lg border border-destructive/40 p-3 space-y-2">
                    {unresolvedMembers.map((item) => (
                      <div key={`${item.team_name}::${item.raw_name}::${item.reason}`}>
                        {item.team_name} · {item.raw_name} ({resolveReasonLabel(item.reason)})
                      </div>
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
