'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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

type UnresolvedSelection = {
  key: string;
  team_name: string;
  raw_name: string;
  selected_student_user_id: number | null;
  reason: string;
  candidates: TournamentParseUnresolvedItem['candidates'];
};

type MultiTeamWarning = {
  student_user_id: number;
  student_name: string;
  team_names: string[];
};

type PageState = {
  session: TournamentSessionResponse | null;
  loading: boolean;
  error: string | null;
  title: string;
  rawText: string;
  bracketSize: BracketSize;
  repechage: boolean;
  allowSelfVote: boolean;
};

type ParseState = {
  parsedMembers: TournamentParsePreviewMember[];
  unresolvedSelections: UnresolvedSelection[];
  parseCompleted: boolean;
  parsingMembers: boolean;
  saving: boolean;
};

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
    if (!grouped.has(member.team_name)) grouped.set(member.team_name, []);
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

function parseBracketSize(value: unknown): BracketSize {
  const n = Number(value);
  return (BRACKET_SIZES as readonly number[]).includes(n) ? (n as BracketSize) : 8;
}

function useTournamentEditPageState(
  sessionId: number | null,
  isAuthenticated: boolean,
  isLoading: boolean,
  onCreatedSession?: (newSessionId: number) => void,
) {
  const [pageState, setPageState] = useState<PageState>({
    session: null,
    loading: true,
    error: null,
    title: '',
    rawText: '',
    bracketSize: 8,
    repechage: false,
    allowSelfVote: true,
  });
  const [parseState, setParseState] = useState<ParseState>({
    parsedMembers: [],
    unresolvedSelections: [],
    parseCompleted: false,
    parsingMembers: false,
    saving: false,
  });

  const parseAbortControllerRef = useRef<AbortController | null>(null);
  const parseRequestIdRef = useRef(0);

  const loadPage = useCallback(async () => {
    if (sessionId === null) {
      setPageState((prev) => ({ ...prev, loading: false, error: null }));
      setParseState((prev) => ({ ...prev, parsedMembers: [], unresolvedSelections: [], parseCompleted: false }));
      return;
    }

    setPageState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const session = await tournamentsApi.getSession(sessionId);
      const members = toMembersFromSession(session);
      const fj = session.format_json as Record<string, unknown> | null | undefined;
      const bs = parseBracketSize(fj?.bracket_size);
      const rep = Boolean((fj?.repechage as Record<string, unknown> | undefined)?.enabled);
      setPageState({
        session,
        loading: false,
        error: null,
        title: session.title,
        rawText: serializeMembersAsRawText(members),
        bracketSize: bs,
        repechage: rep,
        allowSelfVote: session.allow_self_vote ?? true,
      });
      setParseState((prev) => ({ ...prev, parsedMembers: [], unresolvedSelections: [], parseCompleted: false }));
    } catch (e) {
      console.error(e);
      setPageState((prev) => ({ ...prev, loading: false, error: '세션 정보를 불러오지 못했습니다.' }));
    }
  }, [sessionId]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      void loadPage();
    }
  }, [isAuthenticated, isLoading, loadPage]);

  const resolvedUnresolvedMembers = useMemo(() => {
    return parseState.unresolvedSelections
      .map((item): TournamentParsePreviewMember | null => {
        if (!item.selected_student_user_id) return null;
        const selectedCandidate = item.candidates.find((c) => c.student_user_id === item.selected_student_user_id);
        if (!selectedCandidate) return null;
        return {
          team_name: item.team_name,
          raw_name: item.raw_name,
          student_user_id: selectedCandidate.student_user_id,
          student_name: selectedCandidate.student_name,
          student_email: selectedCandidate.student_email,
          can_attend_vote: true,
        };
      })
      .filter((member): member is TournamentParsePreviewMember => member !== null);
  }, [parseState.unresolvedSelections]);

  const candidateOptionsByKey = useMemo(() => {
    const assignedTeamByStudent = new Map<number, string>();

    for (const member of parseState.parsedMembers) {
      assignedTeamByStudent.set(member.student_user_id, member.team_name);
    }
    for (const item of parseState.unresolvedSelections) {
      if (item.selected_student_user_id) {
        assignedTeamByStudent.set(item.selected_student_user_id, item.team_name);
      }
    }

    const options = new Map<string, TournamentParseUnresolvedItem['candidates']>();
    for (const item of parseState.unresolvedSelections) {
      options.set(
        item.key,
        item.candidates.filter((candidate) => {
          const assignedTeam = assignedTeamByStudent.get(candidate.student_user_id);
          return !assignedTeam || assignedTeam === item.team_name;
        }),
      );
    }

    return options;
  }, [parseState.parsedMembers, parseState.unresolvedSelections]);

  const combinedMembers = useMemo(
    () => [...parseState.parsedMembers, ...resolvedUnresolvedMembers],
    [parseState.parsedMembers, resolvedUnresolvedMembers],
  );

  const unresolvedNoCandidates = useMemo(
    () => parseState.unresolvedSelections.filter((item) => (candidateOptionsByKey.get(item.key) ?? []).length === 0),
    [candidateOptionsByKey, parseState.unresolvedSelections],
  );

  const unresolvedNeedSelection = useMemo(
    () =>
      parseState.unresolvedSelections.filter(
        (item) => (candidateOptionsByKey.get(item.key) ?? []).length > 0 && !item.selected_student_user_id,
      ),
    [candidateOptionsByKey, parseState.unresolvedSelections],
  );

  const multiTeamWarnings = useMemo<MultiTeamWarning[]>(() => {
    const byStudent = new Map<number, { student_name: string; team_names: Set<string> }>();
    for (const member of combinedMembers) {
      if (!byStudent.has(member.student_user_id)) {
        byStudent.set(member.student_user_id, { student_name: member.student_name, team_names: new Set<string>() });
      }
      byStudent.get(member.student_user_id)!.team_names.add(member.team_name);
    }
    return Array.from(byStudent.entries())
      .map(([student_user_id, info]) => ({
        student_user_id,
        student_name: info.student_name,
        team_names: Array.from(info.team_names),
      }))
      .filter((item) => item.team_names.length > 1);
  }, [combinedMembers]);

  const warningsResolved =
    parseState.parseCompleted &&
    unresolvedNoCandidates.length === 0 &&
    unresolvedNeedSelection.length === 0 &&
    multiTeamWarnings.length === 0 &&
    combinedMembers.length > 0;

  const canSave =
    pageState.title.trim().length > 0 &&
    !parseState.parsingMembers &&
    !parseState.saving &&
    warningsResolved;

  const isBusy = parseState.parsingMembers || parseState.saving;

  const handleTitleChange = useCallback((value: string) => {
    setPageState((prev) => ({ ...prev, title: value }));
  }, []);

  const handleRawTextChange = useCallback((value: string) => {
    setPageState((prev) => ({ ...prev, rawText: value }));
  }, []);

  const handleBracketSizeChange = useCallback((value: BracketSize) => {
    setPageState((prev) => ({ ...prev, bracketSize: value, repechage: value >= 8 ? prev.repechage : false }));
  }, []);

  const handleRepechageChange = useCallback((value: boolean) => {
    setPageState((prev) => ({ ...prev, repechage: value }));
  }, []);

  const handleAllowSelfVoteChange = useCallback((value: boolean) => {
    setPageState((prev) => ({ ...prev, allowSelfVote: value }));
  }, []);

  const handleParseMembers = useCallback(async () => {
    const normalizedText = pageState.rawText.trim();
    if (!normalizedText) {
      setPageState((prev) => ({ ...prev, error: '팀 구성을 입력해 주세요.' }));
      return;
    }

    parseAbortControllerRef.current?.abort();
    const controller = new AbortController();
    parseAbortControllerRef.current = controller;
    const requestId = parseRequestIdRef.current + 1;
    parseRequestIdRef.current = requestId;

    setParseState((prev) => ({ ...prev, parsingMembers: true, parseCompleted: false }));
    setPageState((prev) => ({ ...prev, error: null }));

    try {
      const parsed =
        sessionId === null
          ? await tournamentsApi.parseMembersDraft({ raw_text: normalizedText })
          : await tournamentsApi.parseMembers(sessionId, { raw_text: normalizedText });

      if (parseRequestIdRef.current !== requestId) return;

      setParseState((prev) => ({
        ...prev,
        parsedMembers: flattenTeams(parsed.teams),
        unresolvedSelections: parsed.unresolved_members.map((item, index) => ({
          key: `${item.team_name}::${item.raw_name}::${index}`,
          team_name: item.team_name,
          raw_name: item.raw_name,
          selected_student_user_id: item.candidates.length === 1 ? item.candidates[0].student_user_id : null,
          reason: item.reason,
          candidates: item.candidates,
        })),
        parseCompleted: true,
      }));
    } catch (e) {
      if (parseRequestIdRef.current !== requestId) return;
      if (e instanceof DOMException && e.name === 'AbortError') return;
      console.error(e);
      setPageState((prev) => ({ ...prev, error: '팀 구성 파싱에 실패했습니다.' }));
    } finally {
      if (parseAbortControllerRef.current === controller) {
        parseAbortControllerRef.current = null;
      }
      if (parseRequestIdRef.current === requestId) {
        setParseState((prev) => ({ ...prev, parsingMembers: false }));
      }
    }
  }, [pageState.rawText, sessionId]);

  const handleCancelParse = useCallback(() => {
    parseAbortControllerRef.current?.abort();
  }, []);

  useEffect(() => {
    setParseState((prev) => {
      let changed = false;
      const next = prev.unresolvedSelections.map((item) => {
        const candidates = candidateOptionsByKey.get(item.key) ?? [];
        const nextSelected =
          item.selected_student_user_id && !candidates.some((c) => c.student_user_id === item.selected_student_user_id)
            ? candidates.length === 1
              ? candidates[0].student_user_id
              : null
            : !item.selected_student_user_id && candidates.length === 1
              ? candidates[0].student_user_id
              : item.selected_student_user_id;

        if (nextSelected !== item.selected_student_user_id) {
          changed = true;
          return { ...item, selected_student_user_id: nextSelected };
        }
        return item;
      });

      if (!changed) return prev;
      return { ...prev, unresolvedSelections: next };
    });
  }, [candidateOptionsByKey]);

  const handleResolveSelect = useCallback((key: string, studentUserId: number) => {
    setParseState((prev) => ({
      ...prev,
      unresolvedSelections: prev.unresolvedSelections.map((item) =>
        item.key === key ? { ...item, selected_student_user_id: studentUserId } : item,
      ),
    }));
  }, []);

  const handleSaveAll = useCallback(async () => {
    const normalizedTitle = pageState.title.trim();
    if (!normalizedTitle) {
      setPageState((prev) => ({ ...prev, error: '세션 제목을 입력해 주세요.' }));
      return;
    }
    if (!warningsResolved) {
      setPageState((prev) => ({ ...prev, error: '팀 구성 경고를 모두 해소한 뒤 저장해 주세요.' }));
      return;
    }

    setParseState((prev) => ({ ...prev, saving: true }));
    setPageState((prev) => ({ ...prev, error: null }));

    try {
      let targetSessionId = sessionId;

      if (targetSessionId === null) {
        const created = await tournamentsApi.createSession({ title: normalizedTitle, allow_self_vote: pageState.allowSelfVote });
        targetSessionId = created.id;
      } else {
        await tournamentsApi.updateSession(targetSessionId, { title: normalizedTitle, allow_self_vote: pageState.allowSelfVote });
      }

      await Promise.all([
        tournamentsApi.confirmMembers(targetSessionId, {
          members: combinedMembers,
          unresolved_members: [],
        }),
        tournamentsApi.setFormat(targetSessionId, {
          bracket_size: pageState.bracketSize,
          repechage: pageState.repechage,
        }),
      ]);

      await tournamentsApi.generateMatches(targetSessionId);

      if (sessionId === null) {
        onCreatedSession?.(targetSessionId);
      } else {
        void loadPage();
      }
    } catch (e) {
      console.error(e);
      setPageState((prev) => ({ ...prev, error: '저장에 실패했습니다.' }));
    } finally {
      setParseState((prev) => ({ ...prev, saving: false }));
    }
  }, [pageState, warningsResolved, sessionId, combinedMembers, onCreatedSession, loadPage]);

  return {
    pageState,
    parseState,
    candidateOptionsByKey,
    multiTeamWarnings,
    warningsResolved,
    canSave,
    isBusy,
    handleTitleChange,
    handleRawTextChange,
    handleBracketSizeChange,
    handleRepechageChange,
    handleAllowSelfVoteChange,
    handleParseMembers,
    handleCancelParse,
    handleResolveSelect,
    handleSaveAll,
  };
}

function TournamentSettingsCard({
  title,
  rawText,
  bracketSize,
  repechage,
  allowSelfVote,
  isBusy,
  saving,
  parsingMembers,
  onTitleChange,
  onRawTextChange,
  onBracketSizeChange,
  onRepechageChange,
  onAllowSelfVoteChange,
  onParse,
  onCancelParse,
}: {
  title: string;
  rawText: string;
  bracketSize: BracketSize;
  repechage: boolean;
  allowSelfVote: boolean;
  isBusy: boolean;
  saving: boolean;
  parsingMembers: boolean;
  onTitleChange: (value: string) => void;
  onRawTextChange: (value: string) => void;
  onBracketSizeChange: (value: BracketSize) => void;
  onRepechageChange: (value: boolean) => void;
  onAllowSelfVoteChange: (value: boolean) => void;
  onParse: () => void;
  onCancelParse: () => void;
}) {
  return (
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
            onChange={(e) => onTitleChange(e.target.value)}
            placeholder="세션 제목"
            disabled={isBusy}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="tournament-members-raw">팀 구성</Label>
          <Textarea
            id="tournament-members-raw"
            value={rawText}
            onChange={(e) => onRawTextChange(e.target.value)}
            placeholder="예) A팀: 홍길동, 김민수&#10;B팀: 박서연, 이수민"
            className="min-h-36"
            disabled={isBusy}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="tournament-bracket-size">브라켓 크기</Label>
          <select
            id="tournament-bracket-size"
            value={bracketSize}
            onChange={(e) => onBracketSizeChange(parseBracketSize(e.target.value))}
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
              onChange={(e) => onRepechageChange(e.target.checked)}
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
              onChange={(e) => onAllowSelfVoteChange(e.target.checked)}
              disabled={isBusy}
              className="h-4 w-4 accent-primary"
            />
            <Label htmlFor="tournament-allow-self-vote" className="cursor-pointer">
              출전 팀원도 본인 경기에 투표 가능
            </Label>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button onClick={onParse} disabled={saving}>
            {parsingMembers ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                분석 중...
              </span>
            ) : (
              '팀 구성 체크하기'
            )}
          </Button>
          {parsingMembers ? (
            <Button type="button" variant="outline" onClick={onCancelParse}>
              취소
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

function TournamentParseResultsCard({
  parseCompleted,
  unresolvedSelections,
  candidateOptionsByKey,
  onResolveSelect,
  isBusy,
  multiTeamWarnings,
  warningsResolved,
}: {
  parseCompleted: boolean;
  unresolvedSelections: UnresolvedSelection[];
  candidateOptionsByKey: Map<string, TournamentParseUnresolvedItem['candidates']>;
  onResolveSelect: (key: string, studentUserId: number) => void;
  isBusy: boolean;
  multiTeamWarnings: MultiTeamWarning[];
  warningsResolved: boolean;
}) {
  return (
    <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
      <CardHeader>
        <CardTitle className="text-base">팀 구성 체크 결과</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!parseCompleted ? (
          <div className="text-sm text-muted-foreground">팀 구성 체크하기를 실행하면 경고 항목을 확인할 수 있습니다.</div>
        ) : null}

        {unresolvedSelections.length > 0 ? (
          <div className="space-y-3">
            <div className="text-sm font-medium">확인 필요한 항목</div>
            {unresolvedSelections.map((item) => {
              const candidates = candidateOptionsByKey.get(item.key) ?? [];
              return (
                <div key={item.key} className="rounded-lg border border-border/70 bg-card/80 p-3 space-y-2">
                  <div className="text-sm">
                    {item.team_name} · {item.raw_name} ({resolveReasonLabel(item.reason)})
                  </div>
                  {candidates.length > 0 ? (
                    <div className="flex flex-col gap-2">
                      {candidates.map((candidate) => (
                        <label key={`${item.key}-${candidate.student_user_id}`} className="flex items-center gap-2 text-sm">
                          <input
                            type="radio"
                            name={`candidate-${item.key}`}
                            value={candidate.student_user_id}
                            checked={item.selected_student_user_id === candidate.student_user_id}
                            onChange={() => onResolveSelect(item.key, candidate.student_user_id)}
                            disabled={isBusy}
                          />
                          {candidate.student_name} ({candidate.student_email})
                        </label>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-destructive">후보 없음: 원문을 수정해 다시 불러와 주세요.</div>
                  )}
                </div>
              );
            })}
          </div>
        ) : null}

        {multiTeamWarnings.length > 0 ? (
          <Alert variant="destructive">
            <AlertDescription>
              <div className="space-y-2">
                <div className="text-sm font-medium">동일 학생 다중 팀 소속 경고</div>
                <ul className="space-y-1 text-sm">
                  {multiTeamWarnings.map((item) => (
                    <li key={item.student_user_id}>
                      {item.student_name}: {item.team_names.join(', ')}
                    </li>
                  ))}
                </ul>
              </div>
            </AlertDescription>
          </Alert>
        ) : null}

        {parseCompleted && warningsResolved ? (
          <div
            className="rounded-lg border px-3 py-2 text-sm"
            style={{
              borderColor: 'var(--sys-current-border)',
              backgroundColor: 'var(--sys-current-bg)',
              color: 'var(--sys-current-fg)',
            }}
          >
            모든 경고가 해소되어 팀 구성을 정리했습니다.
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function ProfessorTournamentEditPageClient({ sessionId }: ProfessorTournamentEditPageClientProps) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const handleCreatedSession = useCallback(
    (createdSessionId: number) => {
      router.replace(`/professor/tournaments/${createdSessionId}/edit`);
    },
    [router],
  );

  const model = useTournamentEditPageState(sessionId, isAuthenticated, isLoading, handleCreatedSession);

  const handleBackToList = useCallback(() => {
    router.push('/professor/tournaments');
  }, [router]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

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
              <Button
                type="button"
                size="icon"
                variant="outline"
                aria-label="목록으로"
                title="목록으로"
                disabled={model.isBusy}
                onClick={handleBackToList}
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                onClick={() => {
                  void model.handleSaveAll();
                }}
                disabled={!model.canSave}
              >
                {model.parseState.saving ? '저장 중...' : '저장'}
              </Button>
            </div>
          }
        />

        {model.pageState.error ? (
          <Alert variant="destructive">
            <AlertDescription>{model.pageState.error}</AlertDescription>
          </Alert>
        ) : null}

        {model.pageState.loading ? (
          <Card>
            <CardContent className="py-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </CardContent>
          </Card>
        ) : (
          <>
            <TournamentSettingsCard
              title={model.pageState.title}
              rawText={model.pageState.rawText}
              bracketSize={model.pageState.bracketSize}
              repechage={model.pageState.repechage}
              allowSelfVote={model.pageState.allowSelfVote}
              isBusy={model.isBusy}
              saving={model.parseState.saving}
              parsingMembers={model.parseState.parsingMembers}
              onTitleChange={model.handleTitleChange}
              onRawTextChange={model.handleRawTextChange}
              onBracketSizeChange={model.handleBracketSizeChange}
              onRepechageChange={model.handleRepechageChange}
              onAllowSelfVoteChange={model.handleAllowSelfVoteChange}
              onParse={() => {
                void model.handleParseMembers();
              }}
              onCancelParse={model.handleCancelParse}
            />

            <TournamentParseResultsCard
              parseCompleted={model.parseState.parseCompleted}
              unresolvedSelections={model.parseState.unresolvedSelections}
              candidateOptionsByKey={model.candidateOptionsByKey}
              onResolveSelect={model.handleResolveSelect}
              isBusy={model.isBusy}
              multiTeamWarnings={model.multiTeamWarnings}
              warningsResolved={model.warningsResolved}
            />
          </>
        )}
      </main>
    </div>
  );
}
