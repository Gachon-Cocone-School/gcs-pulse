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
import { peerReviewsApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type {
  PeerReviewParsePreviewMember,
  PeerReviewParseUnresolvedItem,
  PeerReviewSessionResponse,
} from '@/lib/types';

interface ProfessorPeerReviewsEditPageClientProps {
  sessionId: number | null;
}

type UnresolvedSelection = {
  key: string;
  team_label: string;
  raw_name: string;
  selected_student_user_id: number | null;
  reason: string;
  candidates: PeerReviewParseUnresolvedItem['candidates'];
};

type MultiTeamWarning = {
  student_user_id: number;
  student_name: string;
  team_labels: string[];
};

type PageState = {
  session: PeerReviewSessionResponse | null;
  loading: boolean;
  error: string | null;
  title: string;
  rawText: string;
};

type ParseState = {
  parsedMembers: PeerReviewParsePreviewMember[];
  unresolvedSelections: UnresolvedSelection[];
  parseCompleted: boolean;
  parsingMembers: boolean;
  saving: boolean;
};

function flattenTeams(teams: Record<string, PeerReviewParsePreviewMember[]>): PeerReviewParsePreviewMember[] {
  return Object.values(teams).flat();
}

function buildCanonicalRawText(members: PeerReviewParsePreviewMember[]): string {
  const grouped = new Map<string, string[]>();
  for (const member of members) {
    if (!grouped.has(member.team_label)) {
      grouped.set(member.team_label, []);
    }
    grouped.get(member.team_label)!.push(member.student_name);
  }

  return Array.from(grouped.entries())
    .map(([teamLabel, names]) => `${teamLabel}: ${names.join(', ')}`)
    .join('\r\n');
}

function resolveReasonLabel(reason: string): string {
  if (reason === 'name_not_found') return '이름을 찾을 수 없음';
  if (reason === 'email_not_found') return '이메일을 찾을 수 없음';
  if (reason === 'ambiguous_name') return '동명이인 후보 다수';
  if (reason === 'student_in_multiple_teams') return '한 학생이 여러 팀에 배정됨';
  return reason;
}

function usePeerReviewEditPageState(
  sessionId: number | null,
  isAuthenticated: boolean,
  isLoading: boolean,
  onCreatedSession?: (sessionId: number) => void,
) {
  const [pageState, setPageState] = useState<PageState>({
    session: null,
    loading: true,
    error: null,
    title: '',
    rawText: '',
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
      setPageState((prev) => ({
        ...prev,
        session: null,
        loading: false,
        error: null,
        title: prev.title || '새 팀 피드백 세션',
        rawText: prev.rawText,
      }));
      setParseState((prev) => ({
        ...prev,
        parsedMembers: [],
        unresolvedSelections: [],
        parseCompleted: false,
      }));
      return;
    }

    setPageState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response = await peerReviewsApi.getSession(sessionId);
      setPageState({
        session: response,
        loading: false,
        error: null,
        title: response.title,
        rawText: response.raw_text ?? '',
      });
      setParseState((prev) => ({
        ...prev,
        parsedMembers: [],
        unresolvedSelections: [],
        parseCompleted: false,
      }));
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
      .map((item): PeerReviewParsePreviewMember | null => {
        if (!item.selected_student_user_id) return null;
        const selectedCandidate = item.candidates.find((candidate) => candidate.student_user_id === item.selected_student_user_id);
        if (!selectedCandidate) return null;
        return {
          team_label: item.team_label,
          raw_name: item.raw_name,
          student_user_id: selectedCandidate.student_user_id,
          student_name: selectedCandidate.student_name,
          student_email: selectedCandidate.student_email,
        };
      })
      .filter((member): member is PeerReviewParsePreviewMember => member !== null);
  }, [parseState.unresolvedSelections]);

  const candidateOptionsByKey = useMemo(() => {
    const assignedTeamByStudent = new Map<number, string>();

    for (const member of parseState.parsedMembers) {
      assignedTeamByStudent.set(member.student_user_id, member.team_label);
    }

    for (const item of parseState.unresolvedSelections) {
      if (item.selected_student_user_id) {
        assignedTeamByStudent.set(item.selected_student_user_id, item.team_label);
      }
    }

    const options = new Map<string, PeerReviewParseUnresolvedItem['candidates']>();
    for (const item of parseState.unresolvedSelections) {
      options.set(
        item.key,
        item.candidates.filter((candidate) => {
          const assignedTeam = assignedTeamByStudent.get(candidate.student_user_id);
          return !assignedTeam || assignedTeam === item.team_label;
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
    const byStudent = new Map<number, { student_name: string; team_labels: Set<string> }>();

    for (const member of combinedMembers) {
      if (!byStudent.has(member.student_user_id)) {
        byStudent.set(member.student_user_id, {
          student_name: member.student_name,
          team_labels: new Set<string>(),
        });
      }
      byStudent.get(member.student_user_id)!.team_labels.add(member.team_label);
    }

    return Array.from(byStudent.entries())
      .map(([student_user_id, info]) => ({
        student_user_id,
        student_name: info.student_name,
        team_labels: Array.from(info.team_labels),
      }))
      .filter((item) => item.team_labels.length > 1);
  }, [combinedMembers]);

  const warningsResolved =
    parseState.parseCompleted &&
    unresolvedNoCandidates.length === 0 &&
    unresolvedNeedSelection.length === 0 &&
    multiTeamWarnings.length === 0 &&
    combinedMembers.length > 0;

  const canonicalRawText = useMemo(
    () => (warningsResolved ? buildCanonicalRawText(combinedMembers) : null),
    [combinedMembers, warningsResolved],
  );

  const canSave =
    pageState.title.trim().length > 0 &&
    !parseState.parsingMembers &&
    !parseState.saving &&
    Boolean(canonicalRawText) &&
    warningsResolved;

  const isBusy = parseState.parsingMembers || parseState.saving;

  const handleTitleChange = useCallback((value: string) => {
    setPageState((prev) => ({ ...prev, title: value }));
  }, []);

  const handleRawTextChange = useCallback((value: string) => {
    setPageState((prev) => ({ ...prev, rawText: value }));
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
          ? await peerReviewsApi.parseMembersDraft({ raw_text: normalizedText }, { signal: controller.signal })
          : await peerReviewsApi.parseMembers(sessionId, { raw_text: normalizedText }, { signal: controller.signal });

      if (parseRequestIdRef.current !== requestId) {
        return;
      }

      setParseState((prev) => ({
        ...prev,
        parsedMembers: flattenTeams(parsed.teams),
        unresolvedSelections: parsed.unresolved_members.map((item, index) => ({
          key: `${item.team_label}::${item.raw_name}::${index}`,
          team_label: item.team_label,
          raw_name: item.raw_name,
          selected_student_user_id: item.candidates.length === 1 ? item.candidates[0].student_user_id : null,
          reason: item.reason,
          candidates: item.candidates,
        })),
        parseCompleted: true,
      }));
    } catch (e) {
      if (parseRequestIdRef.current !== requestId) {
        return;
      }
      if (e instanceof DOMException && e.name === 'AbortError') {
        return;
      }
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
          item.selected_student_user_id && !candidates.some((candidate) => candidate.student_user_id === item.selected_student_user_id)
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

    if (!canonicalRawText || !warningsResolved) {
      setPageState((prev) => ({ ...prev, error: '팀 구성 경고를 모두 해소한 뒤 저장해 주세요.' }));
      return;
    }

    setParseState((prev) => ({ ...prev, saving: true }));
    setPageState((prev) => ({ ...prev, error: null }));

    try {
      let targetSessionId = sessionId;
      let updatedSession: PeerReviewSessionResponse;

      if (targetSessionId === null) {
        updatedSession = await peerReviewsApi.createSession({ title: normalizedTitle });
        targetSessionId = updatedSession.id;
      } else {
        updatedSession = await peerReviewsApi.updateSession(targetSessionId, { title: normalizedTitle });
      }

      await peerReviewsApi.confirmMembers(targetSessionId, {
        members: combinedMembers,
        unresolved_members: [],
      });

      setPageState((prev) => ({
        ...prev,
        session: updatedSession,
        rawText: updatedSession.raw_text ?? canonicalRawText,
      }));

      if (sessionId === null) {
        onCreatedSession?.(updatedSession.id);
      }
    } catch (e) {
      console.error(e);
      setPageState((prev) => ({ ...prev, error: '저장에 실패했습니다.' }));
    } finally {
      setParseState((prev) => ({ ...prev, saving: false }));
    }
  }, [canonicalRawText, combinedMembers, onCreatedSession, pageState.title, sessionId, warningsResolved]);

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
    handleParseMembers,
    handleCancelParse,
    handleResolveSelect,
    handleSaveAll,
  };
}

function EditSessionSettingsCard({
  title,
  rawText,
  isBusy,
  saving,
  parsingMembers,
  onTitleChange,
  onRawTextChange,
  onParse,
  onCancelParse,
}: {
  title: string;
  rawText: string;
  isBusy: boolean;
  saving: boolean;
  parsingMembers: boolean;
  onTitleChange: (value: string) => void;
  onRawTextChange: (value: string) => void;
  onParse: () => void;
  onCancelParse: () => void;
}) {
  return (
    <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
      <CardHeader>
        <CardTitle className="text-base">세션 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="peer-review-title">세션 제목</Label>
          <Input
            id="peer-review-title"
            value={title}
            onChange={(event) => onTitleChange(event.target.value)}
            placeholder="세션 제목"
            disabled={isBusy}
            data-testid="peer-review-edit-title-input"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="peer-review-raw-members">팀 구성</Label>
          <Textarea
            id="peer-review-raw-members"
            value={rawText}
            onChange={(event) => onRawTextChange(event.target.value)}
            placeholder="예) 1조: 김민수, 김민지\n2조: 박서준, 최유진"
            className="min-h-36"
            disabled={isBusy}
            data-testid="peer-review-edit-raw-input"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button onClick={onParse} disabled={saving} data-testid="peer-review-edit-parse-button">
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
            <Button type="button" variant="outline" onClick={onCancelParse} data-testid="peer-review-edit-parse-cancel">
              취소
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

function EditParseResultsCard({
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
  candidateOptionsByKey: Map<string, PeerReviewParseUnresolvedItem['candidates']>;
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
          <div className="space-y-3" data-testid="peer-review-edit-unresolved-list">
            <div className="text-sm font-medium">확인 필요한 항목</div>
            {unresolvedSelections.map((item) => {
              const candidates = candidateOptionsByKey.get(item.key) ?? [];
              return (
                <div key={item.key} className="rounded-lg border border-border/70 bg-card/80 p-3 space-y-2">
                  <div className="text-sm">
                    {item.team_label} · {item.raw_name} ({resolveReasonLabel(item.reason)})
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
          <Alert variant="destructive" data-testid="peer-review-edit-duplicate-team-warning">
            <AlertDescription>
              <div className="space-y-2">
                <div className="text-sm font-medium">동일 학생 다중 팀 소속 경고</div>
                <ul className="space-y-1 text-sm">
                  {multiTeamWarnings.map((item) => (
                    <li key={item.student_user_id}>
                      {item.student_name}: {item.team_labels.join(', ')}
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
            data-testid="peer-review-edit-parse-clean"
          >
            모든 경고가 해소되어 팀 구성을 정리했습니다.
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function ProfessorPeerReviewsEditPageClient({
  sessionId,
}: ProfessorPeerReviewsEditPageClientProps) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const handleCreatedSession = useCallback(
    (createdSessionId: number) => {
      router.replace(`/professor/peer-reviews/${createdSessionId}/edit`);
    },
    [router],
  );

  const model = usePeerReviewEditPageState(sessionId, isAuthenticated, isLoading, handleCreatedSession);

  const handleBackToList = useCallback(() => {
    router.push('/professor/peer-reviews');
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
          title="팀 피드백 세션 편집"
          description="팀구성 원문을 검증한 뒤 저장합니다."
          actions={
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="icon"
                variant="outline"
                aria-label="메인으로 돌아가기"
                title="메인으로 돌아가기"
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
                data-testid="peer-review-edit-save-all"
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
            <EditSessionSettingsCard
              title={model.pageState.title}
              rawText={model.pageState.rawText}
              isBusy={model.isBusy}
              saving={model.parseState.saving}
              parsingMembers={model.parseState.parsingMembers}
              onTitleChange={model.handleTitleChange}
              onRawTextChange={model.handleRawTextChange}
              onParse={() => {
                void model.handleParseMembers();
              }}
              onCancelParse={model.handleCancelParse}
            />

            <EditParseResultsCard
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
