'use client';

import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createElement, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ComponentType } from 'react';
import { Loader2 } from 'lucide-react';
import QRCode from 'react-qr-code';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useAuth } from '@/context/auth-context';
import { peerEvaluationsApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type { PeerEvaluationSessionProgressResponse, PeerEvaluationSessionResponse } from '@/lib/types';

interface ProfessorPeerEvaluationsProgressPageClientProps {
  sessionId: number;
}

export default function ProfessorPeerEvaluationsProgressPageClient({
  sessionId,
}: ProfessorPeerEvaluationsProgressPageClientProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const [session, setSession] = useState<PeerEvaluationSessionResponse | null>(null);
  const [progress, setProgress] = useState<PeerEvaluationSessionProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isUpdatingSessionStatus, setIsUpdatingSessionStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollingInFlightRef = useRef(false);

  const sortedEvaluatorStatuses = useMemo(
    () =>
      [...(progress?.evaluator_statuses ?? [])].sort((a, b) =>
        a.evaluator_name.localeCompare(b.evaluator_name, 'ko'),
      ),
    [progress],
  );

  const submittedCount = useMemo(
    () => sortedEvaluatorStatuses.filter((item) => item.has_submitted).length,
    [sortedEvaluatorStatuses],
  );
  const totalCount = useMemo(() => sortedEvaluatorStatuses.length, [sortedEvaluatorStatuses]);
  const progressPercent = useMemo(() => (totalCount ? (submittedCount / totalCount) * 100 : 0), [submittedCount, totalCount]);

  const loadProgressOnly = useCallback(async () => {
    const refreshedProgress = await peerEvaluationsApi.getSessionProgress(sessionId);
    setProgress(refreshedProgress);
  }, [sessionId]);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sessionResponse, progressResponse] = await Promise.all([
        peerEvaluationsApi.getSession(sessionId),
        peerEvaluationsApi.getSessionProgress(sessionId),
      ]);
      setSession(sessionResponse);
      setProgress(progressResponse);
    } catch (e) {
      console.error(e);
      setError('투표 진행 화면을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleUpdateSessionStatus = useCallback(
    async (isOpen: boolean) => {
      setIsUpdatingSessionStatus(true);
      setError(null);
      try {
        const updatedSession = await peerEvaluationsApi.updateSessionStatus(sessionId, { is_open: isOpen });
        const refreshedProgress = await peerEvaluationsApi.getSessionProgress(sessionId);
        setSession(updatedSession);
        setProgress(refreshedProgress);
      } catch (e) {
        console.error(e);
        setError(isOpen ? '투표 개시에 실패했습니다.' : '투표 종료에 실패했습니다.');
      } finally {
        setIsUpdatingSessionStatus(false);
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

    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== 'visible' || pollingInFlightRef.current) {
        return;
      }
      pollingInFlightRef.current = true;
      loadProgressOnly()
        .catch((e) => {
          console.error(e);
        })
        .finally(() => {
          pollingInFlightRef.current = false;
        });
    }, 4000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [isAuthenticated, loadProgressOnly, session]);

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

  const isOpen = progress?.is_open ?? session?.is_open ?? false;

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col gap-6 px-6 py-8">
        <PageHeader
          title="동료 피드백 진행 현황"
          description="학생별 제출 현황과 진행률을 확인하고 투표를 개시/종료합니다."
          actions={
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline">
                <Link href="/professor/peer-reviews">메인으로 돌아가기</Link>
              </Button>
              <Button onClick={() => handleUpdateSessionStatus(true)} disabled={isUpdatingSessionStatus || isOpen}>
                투표 개시
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleUpdateSessionStatus(false)}
                disabled={isUpdatingSessionStatus || !isOpen}
              >
                투표 종료
              </Button>
            </div>
          }
        />

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {loading || !session || !progress ? (
          <Card>
            <CardContent className="py-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </CardContent>
          </Card>
        ) : (
          <div className="grid flex-1 gap-6 lg:grid-cols-[minmax(280px,1fr)_minmax(0,2fr)]">
            <Card className="glass-card h-full rounded-xl animate-entrance border-0 shadow-md min-h-[420px] lg:min-h-[500px]">
              <CardHeader>
                <CardTitle>{session.title}</CardTitle>
              </CardHeader>
              <CardContent className="flex h-full flex-col justify-between gap-4">
                <div className="flex flex-1 items-center justify-center" data-testid="peer-eval-progress-qr">
                  <div className="inline-flex rounded-md bg-white p-3">
                    {createElement(QRCode as unknown as ComponentType<{ value: string; size?: number }>, {
                      value: session.form_url,
                      size: 240,
                    })}
                  </div>
                </div>
                <div className="break-all text-xs text-muted-foreground">{session.form_url}</div>
              </CardContent>
            </Card>

            <Card className="glass-card h-full rounded-xl animate-entrance border-0 shadow-md min-h-[420px] lg:min-h-[500px]">
              <CardHeader className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <CardTitle>학생 제출 현황</CardTitle>
                  <div className="space-y-2 text-right" data-testid="peer-eval-progress-summary">
                    <div className="text-sm font-medium" data-testid="peer-eval-progress-count">
                      제출한 사람 {submittedCount}/{totalCount}
                    </div>
                    <Progress value={progressPercent} className="h-3 w-56" data-testid="peer-eval-progress-bar" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div
                  className="grid grid-cols-3 gap-1.5 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-7 2xl:grid-cols-8"
                  data-testid="peer-eval-progress-student-cards"
                >
                  {sortedEvaluatorStatuses.map((row) => (
                    <div
                      key={row.evaluator_user_id}
                      data-testid={`peer-eval-student-card-${row.evaluator_user_id}`}
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
          </div>
        )}
      </main>
    </div>
  );
}
