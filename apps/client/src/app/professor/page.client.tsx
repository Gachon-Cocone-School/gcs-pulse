'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { redirect, useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, Loader2, Search } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { TeamSnippetCard } from '@/components/views/TeamSnippetCard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/context/auth-context';
import { professorApi } from '@/lib/api';
import { getWeekStartDateKey, toDateKey } from '@/lib/dateKeys';
import { hasPrivilegedRole } from '@/lib/types';
import type { ProfessorStudentSearchItem, TeamSnippetCardData } from '@/lib/types';

type SnippetKind = 'daily' | 'weekly';

interface ProfessorSnippetsPageClientProps {
  kindParam?: string;
  idParam?: string;
  dateParam?: string;
  weekParam?: string;
  queryParam?: string;
  studentUserIdParam?: string;
  highlightCommentIdParam?: string;
  testNowParam?: string;
}

function normalizeKind(kindParam?: string): SnippetKind {
  return kindParam === 'weekly' ? 'weekly' : 'daily';
}

export default function ProfessorSnippetsPageClient({
  kindParam,
  idParam,
  dateParam,
  weekParam,
  queryParam,
  studentUserIdParam,
  highlightCommentIdParam,
  testNowParam,
}: ProfessorSnippetsPageClientProps) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const kind = normalizeKind(kindParam);

  const [query, setQuery] = useState((queryParam ?? '').trim());
  const [isComposing, setIsComposing] = useState(false);
  const [candidates, setCandidates] = useState<ProfessorStudentSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<ProfessorStudentSearchItem | null>(null);

  const [snippet, setSnippet] = useState<TeamSnippetCardData | null>(null);
  const [prevId, setPrevId] = useState<number | null>(null);
  const [nextId, setNextId] = useState<number | null>(null);
  const [loadingSnippet, setLoadingSnippet] = useState(false);

  const baseNow = testNowParam ? new Date(testNowParam) : new Date();
  const fallbackDate = toDateKey(baseNow);
  const fallbackWeek = getWeekStartDateKey(baseNow);


  const normalizeKeyInput = useCallback(
    (value: string) => {
      if (kind === 'weekly') {
        const normalizedWeek = getWeekStartDateKey(new Date(`${value}T12:00:00`));
        return normalizedWeek > fallbackWeek ? fallbackWeek : normalizedWeek;
      }
      return value > fallbackDate ? fallbackDate : value;
    },
    [kind, fallbackDate, fallbackWeek],
  );

  const normalizedDateParam = useMemo(() => {
    if (!dateParam || kind !== 'daily') return null;
    return normalizeKeyInput(dateParam);
  }, [dateParam, kind, normalizeKeyInput]);

  const normalizedWeekParam = useMemo(() => {
    if (!weekParam || kind !== 'weekly') return null;
    return normalizeKeyInput(weekParam);
  }, [weekParam, kind, normalizeKeyInput]);

  const selectedKey =
    kind === 'daily'
      ? normalizedDateParam ?? snippet?.date ?? fallbackDate
      : normalizedWeekParam ?? snippet?.week ?? fallbackWeek;

  const snippetKey = kind === 'daily' ? snippet?.date ?? null : snippet?.week ?? null;
  const canGoBackToCurrent = kind === 'daily' && typeof snippetKey === 'string' && snippetKey < fallbackDate;

  const selectedStudentId = selectedStudent?.student_user_id ?? null;
  const highlightCommentId = useMemo(() => {
    if (!highlightCommentIdParam) return undefined;
    const parsed = Number(highlightCommentIdParam);
    if (!Number.isFinite(parsed) || parsed <= 0) return undefined;
    return parsed;
  }, [highlightCommentIdParam]);

  const navigateWithPreservedQuery = useCallback(
    (overrides: Record<string, string | number | null>, mode: 'push' | 'replace' = 'push') => {
      const params = new URLSearchParams(window.location.search);
      Object.entries(overrides).forEach(([k, v]) => {
        if (v == null) params.delete(k);
        else params.set(k, String(v));
      });

      const href = `/professor?${params.toString()}`;
      if (mode === 'replace') {
        router.replace(href);
        return;
      }
      router.push(href);
    },
    [router],
  );

  useEffect(() => {
    setQuery((queryParam ?? '').trim());
  }, [queryParam]);

  useEffect(() => {
    if (!studentUserIdParam) {
      setSelectedStudent(null);
      return;
    }

    const id = Number(studentUserIdParam);
    if (!Number.isFinite(id)) {
      setSelectedStudent(null);
      return;
    }

    const matched = candidates.find((candidate) => candidate.student_user_id === id);
    if (matched) {
      setSelectedStudent(matched);
      return;
    }

    setSelectedStudent(null);
  }, [studentUserIdParam, candidates]);

  useEffect(() => {
    if (!isAuthenticated || !hasAccess || !isProfessor || isComposing) return;

    const q = query.trim();
    if (!q) {
      setCandidates([]);
      setSearching(false);
      return;
    }

    let cancelled = false;
    const timeoutId = window.setTimeout(async () => {
      setSearching(true);
      try {
        const response = await professorApi.searchStudents(q, 20);
        if (cancelled) return;
        setCandidates(response.items);
      } catch (error) {
        if (!cancelled) {
          console.error(error);
          setCandidates([]);
        }
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 1000);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [query, isAuthenticated, hasAccess, isProfessor, isComposing]);

  const loadSnippetPageData = useCallback(async () => {
    if (!selectedStudentId) {
      setSnippet(null);
      setPrevId(null);
      setNextId(null);
      return;
    }

    setLoadingSnippet(true);
    try {
      const response =
        kind === 'daily'
          ? await professorApi.getDailySnippetPageData({
              studentUserId: selectedStudentId,
              id: idParam ?? null,
              date: normalizedDateParam,
            })
          : await professorApi.getWeeklySnippetPageData({
              studentUserId: selectedStudentId,
              id: idParam ?? null,
              week: normalizedWeekParam,
            });

      setSnippet((response.snippet ?? null) as TeamSnippetCardData | null);
      setPrevId(typeof response.prev_id === 'number' ? response.prev_id : null);
      setNextId(typeof response.next_id === 'number' ? response.next_id : null);
    } catch (error) {
      console.error(error);
      setSnippet(null);
      setPrevId(null);
      setNextId(null);
    } finally {
      setLoadingSnippet(false);
    }
  }, [kind, selectedStudentId, idParam, normalizedDateParam, normalizedWeekParam]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }

    if (isAuthenticated && hasAccess && isProfessor && selectedStudentId) {
      void loadSnippetPageData();
    }
  }, [isLoading, isAuthenticated, hasAccess, isProfessor, selectedStudentId, router, loadSnippetPageData]);

  const goToSnippet = useCallback(
    (snippetId: number) => {
      navigateWithPreservedQuery({
        id: snippetId,
        date: null,
        week: null,
      });
    },
    [navigateWithPreservedQuery],
  );

  const handleSelectKey = (value: string) => {
    if (!value || !selectedStudentId) return;

    const normalizedValue = normalizeKeyInput(value);

    navigateWithPreservedQuery({
      id: null,
      date: kind === 'daily' ? normalizedValue : null,
      week: kind === 'weekly' ? normalizedValue : null,
    });
  };

  const handleGoToNextSnippet = () => {
    if (nextId) {
      goToSnippet(nextId);
      return;
    }

    if (canGoBackToCurrent) {
      navigateWithPreservedQuery({ id: null, date: null, week: null });
    }
  };

  const handleSelectStudent = (student: ProfessorStudentSearchItem) => {
    setSelectedStudent(student);
    navigateWithPreservedQuery({
      q: query,
      student_user_id: student.student_user_id,
      id: null,
      date: null,
      week: null,
    });
  };

  const handleChangeQuery = (value: string) => {
    setQuery(value);
    setSelectedStudent(null);
    setSnippet(null);
    setPrevId(null);
    setNextId(null);

    navigateWithPreservedQuery(
      {
        q: value || null,
        student_user_id: null,
        id: null,
        date: null,
        week: null,
      },
      'replace',
    );
  };

  const handleChangeKind = (nextKind: SnippetKind) => {
    navigateWithPreservedQuery({
      kind: nextKind,
      id: null,
      date: null,
      week: null,
    });
  };

  const normalizedSnippet = useMemo(() => {
    if (!snippet) return null;

    return {
      ...snippet,
      content: snippet.content ?? '',
      comments_count: typeof snippet.comments_count === 'number' ? snippet.comments_count : 0,
      user: snippet.user ?? {
        id: selectedStudent?.student_user_id,
        name: selectedStudent?.student_name,
        email: selectedStudent?.student_email,
      },
    };
  }, [snippet, selectedStudent]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    redirect('/login');
  }

  if (!hasAccess || !isProfessor) {
    return <AccessDeniedView reason="student-only" />;
  }

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-7xl px-6 py-8 space-y-6">
        <PageHeader
          title="멘토링"
          description="학생을 1명 선택하면 일간/주간 스니펫을 조회할 수 있습니다."
          actions={
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant={kind === 'daily' ? 'default' : 'outline'}
                onClick={() => handleChangeKind('daily')}
              >
                일간
              </Button>
              <Button
                type="button"
                variant={kind === 'weekly' ? 'default' : 'outline'}
                onClick={() => handleChangeKind('weekly')}
              >
                주간
              </Button>
            </div>
          }
        />

        <Card className="glass-card rounded-xl animate-entrance">
          <CardHeader>
            <CardTitle className="text-base">학생 선택</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => handleChangeQuery(e.target.value)}
                onCompositionStart={() => setIsComposing(true)}
                onCompositionEnd={(e) => {
                  setIsComposing(false);
                  handleChangeQuery(e.currentTarget.value);
                }}
                className="pl-9 border-[var(--sys-current-border)]"
                placeholder="이름으로 학생 검색"
                aria-label="학생 검색"
              />
            </div>

            {searching ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                검색 중...
              </div>
            ) : null}

            {!searching && query.trim() && candidates.length === 0 ? (
              <div className="text-sm text-muted-foreground">검색 결과가 없습니다.</div>
            ) : null}

            {candidates.length > 0 ? (
              <div className="space-y-2" data-testid="professor-student-candidates">
                {candidates.map((candidate) => {
                  const checked = selectedStudent?.student_user_id === candidate.student_user_id;
                  return (
                    <label
                      key={candidate.student_user_id}
                      className="flex cursor-pointer items-center gap-3 rounded-lg border border-[var(--sys-current-border)] bg-card/80 px-3 py-2 text-sm"
                    >
                      <input
                        type="radio"
                        name="professor-student"
                        checked={checked}
                        onChange={() => handleSelectStudent(candidate)}
                      />
                      <span>
                        {candidate.student_name} ({candidate.student_email})
                        {candidate.team_name ? ` · ${candidate.team_name}` : ''}
                      </span>
                    </label>
                  );
                })}
              </div>
            ) : null}
          </CardContent>
        </Card>

        {!selectedStudent ? null : (
          <>
            <PageHeader
              title={`${kind === 'daily' ? '일간' : '주간'} : ${selectedKey}`}
              description={`${selectedStudent.student_name} (${selectedStudent.student_email})`}
              actions={
                <>
                  <Input
                    type="date"
                    className="w-[160px]"
                    value={selectedKey}
                    onChange={(e) => handleSelectKey(e.target.value)}
                    aria-label={kind === 'daily' ? '일간 조회 날짜 선택' : '주간 조회 날짜 선택'}
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={!prevId}
                    onClick={() => prevId && goToSnippet(prevId)}
                    title={kind === 'daily' ? '이전 스니펫' : '이전 주'}
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={!nextId && !canGoBackToCurrent}
                    onClick={handleGoToNextSnippet}
                    title={kind === 'daily' ? '다음 스니펫' : '다음 주'}
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </>
              }
            />

            <Card className="glass-card border-[var(--sys-current-border)] rounded-xl animate-entrance">
              <CardContent className="p-6">
                {loadingSnippet ? (
                  <div className="flex justify-center py-16">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                ) : normalizedSnippet ? (
                  <TeamSnippetCard
                    snippet={normalizedSnippet}
                    kind={kind}
                    highlightCommentId={highlightCommentId}
                    commentType="professor"
                    showDetails
                  />
                ) : null}
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
