'use client';

import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { createElement, useCallback, useEffect, useMemo, useState } from 'react';
import type { ComponentType } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';
import QRCode from 'react-qr-code';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useAuth } from '@/context/auth-context';
import { createPeerReviewProgressSse, peerReviewsApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type {
  PeerReviewProgressUpdatedSseEvent,
  PeerReviewSessionProgressResponse,
  PeerReviewSessionResponse,
  PeerReviewSessionResultsResponse,
} from '@/lib/types';

interface ProfessorPeerReviewsProgressPageClientProps {
  sessionId: number;
}

type ProgressPageState = {
  session: PeerReviewSessionResponse | null;
  progress: PeerReviewSessionProgressResponse | null;
  results: PeerReviewSessionResultsResponse | null;
  resultsLoading: boolean;
  resultsError: string | null;
  ui: {
    loading: boolean;
    isUpdatingSessionStatus: boolean;
    error: string | null;
  };
};

function formatPercent(value: number | null): string {
  if (value === null) {
    return '-';
  }
  return `${value.toFixed(1)}%`;
}

const ContributionBarChart = dynamic(
  () => import('./ContributionBarChart').then((mod) => mod.ContributionBarChart),
  {
    loading: () => (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    ),
  },
);

function PeerReviewProgressLeftCard({
  session,
  isOpen,
  resultsLoading,
  resultsError,
  mySelfContributionAverage,
  othersContributionAverage,
  contributionComparisonData,
  overallFitAverageExcludingSelf,
  chartAxisColor,
  chartGridColor,
  chartMyBarColor,
  chartOthersBarColor,
  chartValueColor,
  chartTooltipBg,
  chartTooltipFg,
  chartTooltipBorder,
}: {
  session: PeerReviewSessionResponse;
  isOpen: boolean;
  resultsLoading: boolean;
  resultsError: string | null;
  mySelfContributionAverage: number | null;
  othersContributionAverage: number | null;
  contributionComparisonData: Array<{ name: string; value: number | null }>;
  overallFitAverageExcludingSelf: number | null;
  chartAxisColor: string;
  chartGridColor: string;
  chartMyBarColor: string;
  chartOthersBarColor: string;
  chartValueColor: string;
  chartTooltipBg: string;
  chartTooltipFg: string;
  chartTooltipBorder: string;
}) {
  return (
    <Card className="glass-card h-full rounded-xl animate-entrance border-0 shadow-md min-h-[420px] lg:min-h-[500px]">
      <CardHeader>
        <CardTitle>{session.title}</CardTitle>
      </CardHeader>
      {isOpen ? (
        <CardContent className="flex h-full flex-col justify-between gap-4">
          <div className="flex flex-1 items-center justify-center" data-testid="peer-review-progress-qr">
            <div className="inline-flex rounded-md bg-white p-3">
              {createElement(QRCode as unknown as ComponentType<{ value: string; size?: number }>, {
                value: session.form_url,
                size: 280,
              })}
            </div>
          </div>
          <div className="break-all text-xs text-muted-foreground">{session.form_url}</div>
        </CardContent>
      ) : (
        <CardContent className="flex h-full flex-col gap-4 animate-entrance" data-testid="peer-review-progress-results-panel">
          {resultsLoading ? (
            <div className="flex flex-1 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : resultsError ? (
            <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">{resultsError}</div>
          ) : (
            <>
              <div
                className="h-64 w-full rounded-lg border bg-card/80 p-3"
                data-testid="peer-review-progress-results-bar-chart"
                style={{ borderColor: chartMyBarColor }}
              >
                {mySelfContributionAverage === null && othersContributionAverage === null ? (
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    기여율 평균 집계 데이터가 없습니다.
                  </div>
                ) : (
                  <ContributionBarChart
                    contributionComparisonData={contributionComparisonData}
                    chartAxisColor={chartAxisColor}
                    chartGridColor={chartGridColor}
                    chartMyBarColor={chartMyBarColor}
                    chartOthersBarColor={chartOthersBarColor}
                    chartValueColor={chartValueColor}
                    chartTooltipBg={chartTooltipBg}
                    chartTooltipFg={chartTooltipFg}
                    chartTooltipBorder={chartTooltipBorder}
                  />
                )}
              </div>
              <div
                className="rounded-lg border bg-card/80 p-3 text-sm"
                data-testid="peer-review-progress-results-fit-average"
                style={{ borderColor: chartMyBarColor }}
              >
                <div className="text-xs text-muted-foreground">적합도 평균</div>
                <div className="mt-1 text-xl font-semibold text-foreground">{formatPercent(overallFitAverageExcludingSelf)}</div>
              </div>
              {overallFitAverageExcludingSelf === null ? (
                <div className="text-xs text-muted-foreground">적합도 평균을 계산할 제출 데이터가 없습니다.</div>
              ) : null}
            </>
          )}
        </CardContent>
      )}
    </Card>
  );
}

function PeerReviewProgressRightCard({
  submittedCount,
  totalCount,
  progressPercent,
  sortedEvaluatorStatuses,
}: {
  submittedCount: number;
  totalCount: number;
  progressPercent: number;
  sortedEvaluatorStatuses: PeerReviewSessionProgressResponse['evaluator_statuses'];
}) {
  return (
    <Card className="glass-card h-full rounded-xl animate-entrance border-0 shadow-md min-h-[420px] lg:min-h-[500px]">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>제출 현황</CardTitle>
          <div className="space-y-2 text-right" data-testid="peer-review-progress-summary">
            <div className="text-sm font-medium" data-testid="peer-review-progress-count">
              제출한 사람 {submittedCount}/{totalCount}
            </div>
            <Progress value={progressPercent} className="h-3 w-56" data-testid="peer-review-progress-bar" />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div
          className="grid grid-cols-3 gap-1.5 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-7 2xl:grid-cols-8"
          data-testid="peer-review-progress-student-cards"
        >
          {sortedEvaluatorStatuses.map((row) => (
            <div
              key={row.evaluator_user_id}
              data-testid={`peer-review-student-card-${row.evaluator_user_id}`}
              className="rounded-md border border-border/70 bg-card/80 px-2 py-1.5"
              style={
                row.has_submitted
                  ? {
                      borderColor: 'var(--sys-current-border)',
                      backgroundColor: 'var(--sys-current-bg)',
                      color: 'var(--sys-current-fg)',
                    }
                  : undefined
              }
            >
              <div className="truncate text-center text-xs font-medium" title={row.evaluator_name}>
                {row.evaluator_name}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function usePeerReviewProgressPageState(sessionId: number, isAuthenticated: boolean, isLoading: boolean) {
  const [state, setState] = useState<ProgressPageState>({
    session: null,
    progress: null,
    results: null,
    resultsLoading: false,
    resultsError: null,
    ui: {
      loading: true,
      isUpdatingSessionStatus: false,
      error: null,
    },
  });

  const { session, progress, results, resultsLoading, resultsError, ui: uiState } = state;

  const sortedEvaluatorStatuses = useMemo(
    () =>
      [...(progress?.evaluator_statuses ?? [])].sort((a, b) =>
        a.evaluator_name.localeCompare(b.evaluator_name, 'ko'),
      ),
    [progress],
  );

  const submittedCount = sortedEvaluatorStatuses.filter((item) => item.has_submitted).length;
  const totalCount = sortedEvaluatorStatuses.length;
  const progressPercent = totalCount ? (submittedCount / totalCount) * 100 : 0;

  const loadProgressOnly = useCallback(async () => {
    const refreshedProgress = await peerReviewsApi.getSessionProgress(sessionId);
    setState((prev) => ({ ...prev, progress: refreshedProgress }));
  }, [sessionId]);

  const handleProgressUpdated = useCallback(
    (payload: PeerReviewProgressUpdatedSseEvent) => {
      if (payload.session_id !== sessionId) {
        return;
      }

      void loadProgressOnly().catch((e) => {
        console.error(e);
      });
    },
    [loadProgressOnly, sessionId],
  );

  const loadPage = useCallback(async () => {
    setState((prev) => ({
      ...prev,
      ui: { ...prev.ui, loading: true, error: null },
      resultsError: null,
      resultsLoading: false,
    }));

    try {
      const [sessionResponse, progressResponse] = await Promise.all([
        peerReviewsApi.getSession(sessionId),
        peerReviewsApi.getSessionProgress(sessionId),
      ]);

      setState((prev) => ({
        ...prev,
        session: sessionResponse,
        progress: progressResponse,
      }));

      const shouldLoadResults = !progressResponse.is_open;
      if (shouldLoadResults) {
        setState((prev) => ({ ...prev, resultsLoading: true }));
        try {
          const resultsResponse = await peerReviewsApi.getResults(sessionId);
          setState((prev) => ({
            ...prev,
            results: resultsResponse,
            resultsError: null,
            resultsLoading: false,
          }));
        } catch (e) {
          console.error(e);
          setState((prev) => ({
            ...prev,
            results: null,
            resultsError: '결과 데이터를 불러오지 못했습니다.',
            resultsLoading: false,
          }));
        }
      } else {
        setState((prev) => ({ ...prev, results: null }));
      }
    } catch (e) {
      console.error(e);
      setState((prev) => ({
        ...prev,
        ui: { ...prev.ui, error: '설문 진행 화면을 불러오지 못했습니다.' },
      }));
    } finally {
      setState((prev) => ({ ...prev, ui: { ...prev.ui, loading: false } }));
    }
  }, [sessionId]);

  const handleUpdateSessionStatus = useCallback(
    async (isOpen: boolean) => {
      setState((prev) => ({
        ...prev,
        ui: { ...prev.ui, isUpdatingSessionStatus: true, error: null },
        resultsError: null,
      }));

      try {
        const updatedSession = await peerReviewsApi.updateSessionStatus(sessionId, { is_open: isOpen });
        const refreshedProgress = await peerReviewsApi.getSessionProgress(sessionId);

        setState((prev) => ({
          ...prev,
          session: updatedSession,
          progress: refreshedProgress,
        }));

        if (isOpen) {
          setState((prev) => ({
            ...prev,
            results: null,
            resultsLoading: false,
            resultsError: null,
          }));
        } else {
          setState((prev) => ({ ...prev, resultsLoading: true }));
          try {
            const resultsResponse = await peerReviewsApi.getResults(sessionId);
            setState((prev) => ({
              ...prev,
              results: resultsResponse,
              resultsError: null,
              resultsLoading: false,
            }));
          } catch (e) {
            console.error(e);
            setState((prev) => ({
              ...prev,
              results: null,
              resultsError: '결과 데이터를 불러오지 못했습니다.',
              resultsLoading: false,
            }));
          }
        }
      } catch (e) {
        console.error(e);
        setState((prev) => ({
          ...prev,
          ui: { ...prev.ui, error: isOpen ? '설문 개시에 실패했습니다.' : '설문 종료에 실패했습니다.' },
        }));
      } finally {
        setState((prev) => ({
          ...prev,
          ui: { ...prev.ui, isUpdatingSessionStatus: false },
        }));
      }
    },
    [sessionId],
  );

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      void loadPage();
    }
  }, [isAuthenticated, isLoading, loadPage]);

  useEffect(() => {
    if (!isAuthenticated || !session) {
      return;
    }

    const source = createPeerReviewProgressSse(handleProgressUpdated);
    source.onerror = () => {
      // reconnect is handled by EventSource automatically
    };

    return () => {
      source.close();
    };
  }, [handleProgressUpdated, isAuthenticated, session]);

  const isOpen = progress?.is_open ?? session?.is_open ?? false;
  const resultRows = results?.rows ?? [];

  const mySelfContributionAverage = useMemo(() => {
    const selfRows = resultRows.filter((row) => row.evaluator_user_id === row.evaluatee_user_id);
    if (!selfRows.length) return null;
    return selfRows.reduce((sum, row) => sum + row.contribution_percent, 0) / selfRows.length;
  }, [resultRows]);

  const othersContributionAverage = useMemo(() => {
    const otherRows = resultRows.filter((row) => row.evaluator_user_id !== row.evaluatee_user_id);
    if (!otherRows.length) return null;
    return otherRows.reduce((sum, row) => sum + row.contribution_percent, 0) / otherRows.length;
  }, [resultRows]);

  const overallFitAverageExcludingSelf = useMemo(() => {
    const otherRows = resultRows.filter((row) => row.evaluator_user_id !== row.evaluatee_user_id);
    if (!otherRows.length) return null;
    const yesCount = otherRows.filter((row) => row.fit_yes_no).length;
    return (yesCount / otherRows.length) * 100;
  }, [resultRows]);

  const contributionComparisonData = useMemo(
    () => [
      { name: '나의 기여율 평균', value: mySelfContributionAverage },
      { name: '타인의 기여율 평균', value: othersContributionAverage },
    ],
    [mySelfContributionAverage, othersContributionAverage],
  );

  return {
    session,
    progress,
    resultsLoading,
    resultsError,
    uiState,
    isOpen,
    sortedEvaluatorStatuses,
    submittedCount,
    totalCount,
    progressPercent,
    mySelfContributionAverage,
    othersContributionAverage,
    overallFitAverageExcludingSelf,
    contributionComparisonData,
    handleUpdateSessionStatus,
  };
}

export default function ProfessorPeerReviewsProgressPageClient({
  sessionId,
}: ProfessorPeerReviewsProgressPageClientProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const {
    session,
    progress,
    resultsLoading,
    resultsError,
    uiState,
    isOpen,
    sortedEvaluatorStatuses,
    submittedCount,
    totalCount,
    progressPercent,
    mySelfContributionAverage,
    othersContributionAverage,
    overallFitAverageExcludingSelf,
    contributionComparisonData,
    handleUpdateSessionStatus,
  } = usePeerReviewProgressPageState(sessionId, isAuthenticated, isLoading);

  const chartAxisColor = 'var(--color-muted-foreground)';
  const chartGridColor = 'var(--color-border)';
  const chartMyBarColor = 'var(--color-primary)';
  const chartOthersBarColor = 'var(--color-accent-600)';
  const chartValueColor = 'var(--color-foreground)';
  const chartTooltipBg = 'var(--color-card)';
  const chartTooltipFg = 'var(--color-card-foreground)';
  const chartTooltipBorder = 'var(--color-border)';

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
      <main className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col gap-6 px-6 py-8">
        <PageHeader
          title="팀 피드백 세션 진행 현황"
          description="제출 현황과 진행률을 확인하고 설문을 개시/종료합니다."
          actions={
            <div className="flex flex-wrap gap-2">
              {isOpen ? (
                <Button type="button" size="icon" variant="outline" aria-label="메인으로 돌아가기" title="메인으로 돌아가기" disabled>
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              ) : (
                <Button asChild type="button" size="icon" variant="outline" aria-label="메인으로 돌아가기" title="메인으로 돌아가기">
                  <Link href="/professor/peer-reviews">
                    <ArrowLeft className="h-4 w-4" />
                  </Link>
                </Button>
              )}
              <Button onClick={() => handleUpdateSessionStatus(true)} disabled={uiState.isUpdatingSessionStatus || isOpen}>
                설문 개시
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleUpdateSessionStatus(false)}
                disabled={uiState.isUpdatingSessionStatus || !isOpen}
              >
                설문 종료
              </Button>
            </div>
          }
        />

        {uiState.error ? (
          <Alert variant="destructive">
            <AlertDescription>{uiState.error}</AlertDescription>
          </Alert>
        ) : null}

        {uiState.loading || !session || !progress ? (
          <Card>
            <CardContent className="py-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </CardContent>
          </Card>
        ) : (
          <div className="grid flex-1 gap-6 lg:grid-cols-[minmax(280px,1fr)_minmax(0,2fr)]">
            <PeerReviewProgressLeftCard
              session={session}
              isOpen={isOpen}
              resultsLoading={resultsLoading}
              resultsError={resultsError}
              mySelfContributionAverage={mySelfContributionAverage}
              othersContributionAverage={othersContributionAverage}
              contributionComparisonData={contributionComparisonData}
              overallFitAverageExcludingSelf={overallFitAverageExcludingSelf}
              chartAxisColor={chartAxisColor}
              chartGridColor={chartGridColor}
              chartMyBarColor={chartMyBarColor}
              chartOthersBarColor={chartOthersBarColor}
              chartValueColor={chartValueColor}
              chartTooltipBg={chartTooltipBg}
              chartTooltipFg={chartTooltipFg}
              chartTooltipBorder={chartTooltipBorder}
            />
            <PeerReviewProgressRightCard
              submittedCount={submittedCount}
              totalCount={totalCount}
              progressPercent={progressPercent}
              sortedEvaluatorStatuses={sortedEvaluatorStatuses}
            />
          </div>
        )}
      </main>
    </div>
  );
}
