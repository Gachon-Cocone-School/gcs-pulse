'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';

import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/context/auth-context';
import { abPracticeApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';

export default function ABPracticeCreatePageClient({ sessionId }: { sessionId?: number }) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [title, setTitle] = useState('새 A/B 실습');
  const [question, setQuestion] = useState('A/B 중 어느게 좋나요?');
  const [seconds, setSeconds] = useState(5);
  const [loadingSession, setLoadingSession] = useState(Boolean(sessionId));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isProfessor = hasPrivilegedRole(user?.roles) && Boolean(user?.roles?.includes('교수'));

  useEffect(() => {
    if (!sessionId || !isAuthenticated || !isProfessor) return;
    let active = true;
    void abPracticeApi
      .getSession(sessionId)
      .then((session) => {
        if (!active) return;
        setTitle(session.title);
        setQuestion(session.question);
        setSeconds(session.exposure_seconds);
      })
      .catch((cause) => {
        console.error(cause);
        if (active) setError('A/B 실습 정보를 불러오지 못했습니다.');
      })
      .finally(() => {
        if (active) setLoadingSession(false);
      });
    return () => {
      active = false;
    };
  }, [isAuthenticated, isProfessor, sessionId]);

  const handleSave = useCallback(async () => {
    if (!title.trim() || !question.trim() || saving) return;
    setSaving(true);
    setError(null);
    try {
      const payload = {
        title: title.trim(),
        question: question.trim(),
        exposure_seconds: seconds,
      };
      const session = sessionId
        ? await abPracticeApi.updateSession(sessionId, payload)
        : await abPracticeApi.createSession(payload);
      if (!sessionId) router.replace(`/professor/ab-practice/${session.id}`);
      else setSaving(false);
    } catch (cause) {
      console.error(cause);
      setError('세션 저장에 실패했습니다. 입력 내용을 확인해 주세요.');
      setSaving(false);
    }
  }, [question, router, saving, seconds, sessionId, title]);

  if (isLoading || loadingSession)
    return <div className="flex min-h-screen items-center justify-center">불러오는 중...</div>;
  if (!isAuthenticated) return null;
  if (!isProfessor) return <AccessDeniedView reason="student-only" />;

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
        <PageHeader
          title={sessionId ? 'A/B 실습 수정' : 'A/B 실습 생성'}
          description="세션 질문과 A/B 테스트 항목별 노출 시간을 설정합니다."
          actions={
            <div className="flex gap-2">
              <Button
                type="button"
                size="icon"
                variant="outline"
                aria-label="목록으로"
                title="목록으로"
                disabled={saving}
                onClick={() => router.push('/professor/ab-practice')}
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving || !title.trim() || !question.trim()}
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
        <Card className="glass-card animate-entrance rounded-xl border-0 shadow-md">
          <CardHeader>
            <CardTitle className="text-base">세션 설정</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="ab-title">세션 제목</Label>
              <Input
                id="ab-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="세션 제목"
                disabled={saving}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ab-question">질문 텍스트</Label>
              <Input
                id="ab-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                maxLength={500}
                placeholder="A/B 중 어느게 좋나요?"
                disabled={saving}
              />
            </div>
            <div className="space-y-2 sm:max-w-sm">
              <Label htmlFor="ab-seconds">항목별 노출 시간 (초)</Label>
              <Input
                id="ab-seconds"
                type="number"
                min={0}
                max={300}
                value={seconds}
                onChange={(event) => setSeconds(Number(event.target.value))}
                disabled={saving}
              />
              <p className="text-xs text-muted-foreground">
                0초는 CVR 테스트(시간 제한 없음), 5초는 CTR 테스트를 권장합니다.
              </p>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
