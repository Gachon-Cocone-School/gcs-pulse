'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';

import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';
import { abPracticeApi } from '@/lib/api';
import { useImageFileSelection } from '@/hooks/useImageFileSelection';
import { hasPrivilegedRole } from '@/lib/types';
import type { ABPracticeProgressResponse, ABPracticeSessionResponse } from '@/lib/types';

import { RegistrationPanel, VotingPanel } from './SessionPanels';

function percent(count: number, total: number): number {
  return total > 0 ? Math.round((count / total) * 100) : 0;
}

export default function ABPracticeSessionPageClient({
  sessionId,
  mode = 'registration',
}: {
  sessionId: number;
  mode?: 'registration' | 'test';
}) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [session, setSession] = useState<ABPracticeSessionResponse | null>(null);
  const [progress, setProgress] = useState<ABPracticeProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const imageA = useImageFileSelection();
  const imageB = useImageFileSelection();
  const selectImageA = imageA.selectFile;
  const selectImageB = imageB.selectFile;
  const [pairTitle, setPairTitle] = useState('');
  const imageARef = useRef<HTMLInputElement>(null);
  const imageBRef = useRef<HTMLInputElement>(null);
  const loadRequestId = useRef(0);
  const isProfessor = hasPrivilegedRole(user?.roles) && Boolean(user?.roles?.includes('교수'));

  const load = useCallback(async () => {
    const requestId = ++loadRequestId.current;
    try {
      const [nextSession, nextProgress] = await Promise.all([
        abPracticeApi.getSession(sessionId),
        abPracticeApi.getProgress(sessionId),
      ]);
      if (requestId !== loadRequestId.current) return;
      setSession(nextSession);
      setProgress(nextProgress);
      setError(null);
    } catch (cause) {
      console.error(cause);
      if (requestId !== loadRequestId.current) return;
      setError('실습 정보를 불러오지 못했습니다.');
    } finally {
      if (requestId === loadRequestId.current) setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (isAuthenticated && isProfessor) void load();
    return () => {
      loadRequestId.current += 1;
    };
  }, [isAuthenticated, isProfessor, load]);
  const sessionStatus = session?.status;
  useEffect(() => {
    if (!['registration_open', 'voting_open'].includes(sessionStatus ?? '')) return;
    const timer = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(timer);
  }, [load, sessionStatus]);

  const hasCompletePair = Boolean(progress?.pairs.some((pair) => pair.complete));
  const runAction = useCallback(
    async (
      action: () => Promise<unknown>,
      failureMessage: string,
      clearPairForm = false,
    ) => {
      setBusy(true);
      setError(null);
      try {
        await action();
        if (clearPairForm) {
          selectImageA(null);
          selectImageB(null);
          setPairTitle('');
          if (imageARef.current) imageARef.current.value = '';
          if (imageBRef.current) imageBRef.current.value = '';
        }
        await load();
        return true;
      } catch (cause) {
        console.error(cause);
        setError(failureMessage);
        await load();
        return false;
      } finally {
        setBusy(false);
      }
    },
    [selectImageA, selectImageB, load],
  );

  const handleBack = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === 'registration' && session?.status === 'registration_open') {
        await abPracticeApi.endRegistration(sessionId);
      } else if (mode === 'test' && session?.status === 'voting_open') {
        await abPracticeApi.endVote(sessionId);
      }
      router.push('/professor/ab-practice');
    } catch (cause) {
      console.error(cause);
      setError(
        mode === 'registration' ? '등록을 종료하지 못했습니다.' : '테스트를 종료하지 못했습니다.',
      );
    } finally {
      setBusy(false);
    }
  }, [busy, mode, router, session?.status, sessionId]);

  if (isLoading || loading)
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin" />
      </div>
    );
  if (!isAuthenticated) return null;
  if (!isProfessor) return <AccessDeniedView reason="student-only" />;
  if (!session || !progress)
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <Card>
          <CardContent className="py-8 text-center text-sm text-destructive">
            {error ?? '실습을 찾을 수 없습니다.'}
          </CardContent>
        </Card>
      </main>
    );

  const totalVoters = progress.total_students;
  const votedPercent = percent(progress.completed_students, totalVoters);
  const registrationOpen = session.status === 'registration_open';
  const canStartTest = !registrationOpen && session.status !== 'voting_open' && hasCompletePair;
  const addPair = () => {
    if (!pairTitle.trim() || !imageA.file || !imageB.file) return;
    void runAction(
      () => abPracticeApi.createProfessorPair(sessionId, pairTitle, imageA.file!, imageB.file!),
      'A/B 테스트 항목을 등록하지 못했습니다.',
      true,
    );
  };

  return (
    <main className="min-h-screen bg-background bg-mesh">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6">
        <PageHeader
          title={mode === 'registration' ? 'A/B 테스트 등록 진행 현황' : 'A/B 테스트 진행 현황'}
          description={`${session.title} · 질문: ${session.question} · ${session.exposure_seconds === 0 ? '시간 제한 없음 (CVR 테스트)' : `항목별 노출 ${session.exposure_seconds}초 (CTR 테스트)`}`}
          actions={
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="icon"
                variant="outline"
                aria-label="목록으로"
                title="목록으로"
                disabled={busy}
                onClick={() => void handleBack()}
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              {mode === 'registration' ? (
                <>
                  <Button
                    disabled={busy || registrationOpen}
                    onClick={() =>
                      void runAction(
                        () => abPracticeApi.startRegistration(sessionId),
                        '등록을 시작하지 못했습니다.',
                      )
                    }
                  >
                    등록 개시
                  </Button>
                  <Button
                    variant="outline"
                    disabled={busy || !registrationOpen}
                    onClick={() =>
                      void runAction(
                        () => abPracticeApi.endRegistration(sessionId),
                        '등록을 종료하지 못했습니다.',
                      )
                    }
                  >
                    등록 종료
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    disabled={busy || !canStartTest}
                    onClick={() =>
                      void runAction(
                        () => abPracticeApi.startTest(sessionId),
                        'A/B 테스트를 시작하지 못했습니다.',
                      )
                    }
                  >
                    테스트 진행
                  </Button>
                  <Button
                    variant="outline"
                    disabled={busy || session.status !== 'voting_open'}
                    onClick={() =>
                      void runAction(
                        () => abPracticeApi.endVote(sessionId),
                        '테스트를 종료하지 못했습니다.',
                      )
                    }
                  >
                    테스트 종료
                  </Button>
                </>
              )}
            </div>
          }
        />
        {error ? (
          <Card>
            <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
          </Card>
        ) : null}
        {mode === 'registration' ? (
          <RegistrationPanel
            session={session}
            progress={progress}
            sessionId={sessionId}
            registrationOpen={registrationOpen}
            busy={busy}
            pairTitle={pairTitle}
            onPairTitleChange={setPairTitle}
            imageA={imageA}
            imageB={imageB}
            imageARef={imageARef}
            imageBRef={imageBRef}
            onAddPair={addPair}
            runAction={runAction}
          />
        ) : (
          <VotingPanel
            session={session}
            progress={progress}
            sessionId={sessionId}
            hasCompletePair={hasCompletePair}
            votedPercent={votedPercent}
            busy={busy}
            runAction={runAction}
          />
        )}
      </div>
    </main>
  );
}
