'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, BarChart3, Download, Loader2 } from 'lucide-react';

import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';
import { API_URL, abPracticeApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type { ABPracticeResultsResponse, ABPracticeSessionResponse } from '@/lib/types';

function absoluteAssetUrl(path: string): string {
  return path.startsWith('http') ? path : `${API_URL.replace(/\/+$/, '')}${path}`;
}

export default function ABPracticeResultsPageClient({ sessionId }: { sessionId: number }) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [session, setSession] = useState<ABPracticeSessionResponse | null>(null);
  const [results, setResults] = useState<ABPracticeResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ url: string; label: string } | null>(null);
  const isProfessor = hasPrivilegedRole(user?.roles) && Boolean(user?.roles?.includes('교수'));

  const load = useCallback(async () => {
    try {
      const nextSession = await abPracticeApi.getSession(sessionId);
      setSession(nextSession);
      if (nextSession.status === 'ended') {
        setResults(await abPracticeApi.getResults(sessionId));
      } else {
        setResults(null);
      }
      setError(null);
    } catch (cause) {
      console.error(cause);
      setError('A/B 테스트 결과를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (isAuthenticated && isProfessor) void load();
  }, [isAuthenticated, isProfessor, load]);

  if (isLoading || loading)
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin" />
      </div>
    );
  if (!isAuthenticated) return null;
  if (!isProfessor) return <AccessDeniedView reason="student-only" />;
  if (!session)
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <Card>
          <CardContent className="py-8 text-center text-sm text-destructive">
            {error ?? '실습을 찾을 수 없습니다.'}
          </CardContent>
        </Card>
      </main>
    );

  return (
    <main id="ab-practice-results" className="min-h-screen bg-background bg-mesh">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6">
        <PageHeader
          title="A/B 테스트 결과"
          description={
            results ? `${session.title} (참여자: ${results.total_students}명)` : session.title
          }
          actions={
            <div className="ab-results-no-print flex gap-2">
              <Button
                asChild
                type="button"
                size="icon"
                variant="outline"
                aria-label="목록으로"
                title="목록으로"
              >
                <Link href="/professor/ab-practice">
                  <ArrowLeft className="h-4 w-4" />
                </Link>
              </Button>
              {results ? (
                <Button type="button" variant="outline" onClick={() => window.print()}>
                  <Download className="mr-2 h-4 w-4" />
                  PDF로 내보내기
                </Button>
              ) : null}
            </div>
          }
        />
        {error ? (
          <Card className="border-destructive/40">
            <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
          </Card>
        ) : null}
        {session.status !== 'ended' ? (
          <Card className="glass-card rounded-xl">
            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
              <BarChart3 className="h-9 w-9 text-muted-foreground" />
              <p className="font-medium">투표를 종료하면 결과를 확인할 수 있습니다.</p>
            </CardContent>
          </Card>
        ) : results ? (
          <>
            {results.pairs.length === 0 ? (
              <Card className="glass-card rounded-xl">
                <CardContent className="py-10 text-center text-sm text-muted-foreground">
                  표시할 A/B 테스트 항목 결과가 없습니다.
                </CardContent>
              </Card>
            ) : (
              <div className="ab-results-table-wrap overflow-x-auto rounded-xl border bg-card/80">
                <table className="ab-results-table w-full min-w-[820px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50 text-left text-muted-foreground">
                      <th className="px-3 py-3 font-medium">이미지</th>
                      <th className="px-3 py-3 font-medium">항목 제목</th>
                      <th className="px-3 py-3 font-medium">등록자</th>
                      <th className="px-3 py-3 text-right font-medium">A 선택</th>
                      <th className="px-3 py-3 text-right font-medium">B 선택</th>
                      <th className="px-3 py-3 text-right font-medium">시간 초과</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.pairs.map((pair, index) => (
                      <tr key={pair.pair_id} className="border-b last:border-0">
                        <td className="px-3 py-2">
                          <div className="flex gap-2">
                            {[
                              { label: 'A', url: pair.image_a_url },
                              { label: 'B', url: pair.image_b_url },
                            ].map((image) => (
                              <button
                                key={image.label}
                                type="button"
                                onClick={() =>
                                  setPreview({
                                    url: absoluteAssetUrl(image.url),
                                    label: `A/B 테스트 항목 ${index + 1} 이미지 ${image.label}`,
                                  })
                                }
                                aria-label={`${image.label} 이미지 크게 보기`}
                                className="relative h-28 w-[5.6rem] shrink-0 overflow-hidden rounded border bg-muted"
                              >
                                <Image
                                  unoptimized
                                  src={absoluteAssetUrl(image.url)}
                                  alt={`항목 ${index + 1} 이미지 ${image.label}`}
                                  fill
                                  sizes="90px"
                                  className="object-cover"
                                />
                              </button>
                            ))}
                          </div>
                        </td>
                        <td className="px-3 py-2 font-medium">{pair.title}</td>
                        <td className="px-3 py-2">{pair.submitter_name}</td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {pair.a_count}표{' '}
                          <span className="text-muted-foreground">
                            ({pair.a_percent === null ? '—' : `${pair.a_percent}%`})
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {pair.b_count}표{' '}
                          <span className="text-muted-foreground">
                            ({pair.b_percent === null ? '—' : `${pair.b_percent}%`})
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {pair.skipped_count}명{' '}
                          <span className="text-muted-foreground">
                            (
                            {results.total_students
                              ? `${Math.round((pair.skipped_count * 1000) / results.total_students) / 10}%`
                              : '—'}
                            )
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : null}
      </div>
      {preview ? (
        <button
          type="button"
          className="ab-results-preview fixed inset-0 z-50 flex cursor-zoom-out items-center justify-center bg-black/90 p-4"
          onClick={() => setPreview(null)}
          aria-label="이미지 미리보기 닫기"
        >
          <span className="sr-only">{preview.label}</span>
          <span className="relative block h-[95vh] w-[95vw]">
            <Image
              unoptimized
              src={preview.url}
              alt={preview.label}
              fill
              sizes="95vw"
              className="object-contain"
            />
          </span>
        </button>
      ) : null}
    </main>
  );
}
