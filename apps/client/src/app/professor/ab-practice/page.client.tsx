'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BarChart3, ImagePlus, Loader2, Pencil, Play, Plus, Trash2 } from 'lucide-react';

import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';
import { abPracticeApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type { ABPracticeSessionListItem } from '@/lib/types';

export default function ABPracticeListPageClient() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [sessions, setSessions] = useState<ABPracticeSessionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<number | null>(null);
  const isProfessor = hasPrivilegedRole(user?.roles) && Boolean(user?.roles?.includes('교수'));

  const load = useCallback(async () => {
    try {
      const result = await abPracticeApi.listSessions();
      setSessions(result.items);
      setError(null);
    } catch (cause) {
      console.error(cause);
      setError('A/B 실습 목록을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleDelete = useCallback(async (session: ABPracticeSessionListItem) => {
    if (
      !window.confirm(
        `“${session.title}” 실습을 삭제할까요? 등록된 항목 이미지와 투표 데이터도 함께 삭제됩니다.`,
      )
    )
      return;
    setDeletingSessionId(session.id);
    try {
      await abPracticeApi.deleteSession(session.id);
      setSessions((current) => current.filter((item) => item.id !== session.id));
    } catch (cause) {
      console.error(cause);
      setError('A/B 실습을 삭제하지 못했습니다.');
    } finally {
      setDeletingSessionId(null);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && isProfessor) void load();
  }, [isAuthenticated, isProfessor, load]);

  if (isLoading)
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin" />
      </div>
    );
  if (!isAuthenticated) return null;
  if (!isProfessor) return <AccessDeniedView reason="student-only" />;

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <main className="mx-auto max-w-7xl px-6 py-8 space-y-6">
        <PageHeader
          title="A/B 실습 세션 리스트"
          description="세션을 생성하고 목록에서 등록·투표·결과를 관리합니다."
        />

        {error ? (
          <Card className="border-destructive/40">
            <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
          </Card>
        ) : null}

        <Card className="glass-card rounded-xl animate-entrance">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle>내 A/B 실습 목록</CardTitle>
              <Button asChild className="w-full text-white sm:w-auto">
                <Link href="/professor/ab-practice/new" style={{ color: '#fff' }}>
                  <Plus className="mr-2 h-4 w-4" />
                  생성하기
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="py-2 text-sm text-muted-foreground">실습 목록을 불러오는 중...</div>
            ) : null}

            {!loading && sessions.length === 0 ? (
              <div className="rounded-lg border border-border/60 bg-card/70 px-4 py-8 text-center text-sm text-muted-foreground">
                생성된 A/B 실습이 없습니다.
              </div>
            ) : null}

            {sessions.length > 0 ? (
              <div className="rounded-lg border border-border overflow-auto bg-card/70">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="p-2">제목</th>
                      <th className="p-2">마지막 수정일</th>
                      <th className="p-2">항목 수</th>
                      <th className="p-2">제출 수</th>
                      <th className="p-2">액션</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((session) => (
                      <tr key={session.id} className="border-b border-border/50 last:border-b-0">
                        <td className="p-2 min-w-[220px]">{session.title}</td>
                        <td className="p-2">
                          {new Date(session.updated_at).toLocaleString('ko-KR', {
                            timeZone: 'Asia/Seoul',
                          })}
                        </td>
                        <td className="p-2">{session.pair_count}</td>
                        <td className="p-2">{session.submission_count}</td>
                        <td className="p-2">
                          <div className="flex items-center gap-1">
                            <Button
                              asChild
                              type="button"
                              size="icon"
                              variant="secondary"
                              title="A/B 테스트 진행"
                              aria-label="A/B 테스트 진행"
                            >
                              <Link href={`/professor/ab-practice/${session.id}/test`}>
                                <Play className="h-4 w-4" />
                              </Link>
                            </Button>
                            <Button
                              asChild
                              type="button"
                              size="icon"
                              variant="outline"
                              title="결과 보기"
                              aria-label={`${session.title} 결과 보기`}
                            >
                              <Link href={`/professor/ab-practice/${session.id}/results`}>
                                <BarChart3 className="h-4 w-4" />
                              </Link>
                            </Button>
                            <Button
                              asChild
                              type="button"
                              size="icon"
                              variant="outline"
                              title="A/B 테스트 등록"
                              aria-label="A/B 테스트 등록"
                            >
                              <Link href={`/professor/ab-practice/${session.id}`}>
                                <ImagePlus className="h-4 w-4" />
                              </Link>
                            </Button>
                            <Button
                              type="button"
                              size="icon"
                              variant="outline"
                              title="수정"
                              aria-label={`${session.title} 수정`}
                              onClick={() =>
                                router.push(`/professor/ab-practice/${session.id}/edit`)
                              }
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              type="button"
                              size="icon"
                              variant="outline"
                              title="삭제"
                              aria-label={`${session.title} 삭제`}
                              disabled={deletingSessionId === session.id}
                              onClick={() => void handleDelete(session)}
                            >
                              {deletingSessionId === session.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4" />
                              )}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
