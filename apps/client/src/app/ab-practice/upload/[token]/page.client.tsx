'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, ImagePlus, Loader2, RefreshCw, Trash2 } from 'lucide-react';

import { PageHeader } from '@/components/PageHeader';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { API_URL, abPracticeApi, ApiError } from '@/lib/api';
import { useImageFileSelection } from '@/hooks/useImageFileSelection';
import type { ABPracticeUploadResponse } from '@/lib/types';

function asset(path: string) {
  return path.startsWith('http') ? path : `${API_URL.replace(/\/+$/, '')}${path}`;
}

export default function ABPracticeUploadPageClient({ token }: { token: string }) {
  const [data, setData] = useState<ABPracticeUploadResponse | null>(null);
  const imageA = useImageFileSelection();
  const imageB = useImageFileSelection();
  const selectImageA = imageA.selectFile;
  const selectImageB = imageB.selectFile;
  const [pairTitle, setPairTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputA = useRef<HTMLInputElement>(null);
  const inputB = useRef<HTMLInputElement>(null);
  const loadRequestId = useRef(0);
  const load = useCallback(async () => {
    const requestId = ++loadRequestId.current;
    try {
      const response = await abPracticeApi.getUpload(token);
      if (requestId !== loadRequestId.current) return;
      setData(response);
      setError(null);
    } catch (cause) {
      console.error(cause);
      if (requestId !== loadRequestId.current) return;
      setError(
        cause instanceof ApiError && cause.status === 403
          ? '이 A/B 테스트 항목을 관리할 권한이 없습니다.'
          : '등록 화면을 열지 못했습니다. QR 링크와 로그인 상태를 확인해 주세요.',
      );
    } finally {
      if (requestId === loadRequestId.current) setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
    return () => {
      loadRequestId.current += 1;
    };
  }, [load]);

  const run = useCallback(
    async (action: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);
      try {
        await action();
        selectImageA(null);
        selectImageB(null);
        setPairTitle('');
        if (inputA.current) inputA.current.value = '';
        if (inputB.current) inputB.current.value = '';
        await load();
      } catch (cause) {
        console.error(cause);
        setError(
          cause instanceof ApiError
            ? cause.message
            : 'A/B 테스트 항목을 저장하지 못했습니다. 다시 시도해 주세요.',
        );
      } finally {
        setBusy(false);
      }
    },
    [selectImageA, selectImageB, load],
  );

  const chooseReplace = useCallback(
    (pairId: number, slot: 'a' | 'b', file?: File) => {
      if (!file) return;
      void run(() => abPracticeApi.replaceImage(token, pairId, slot, file));
    },
    [run, token],
  );

  if (loading)
    return (
      <ProtectedRoute>
        <main className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-7 w-7 animate-spin" />
        </main>
      </ProtectedRoute>
    );
  if (!data)
    return (
      <ProtectedRoute>
        <main className="mx-auto max-w-2xl px-4 py-10">
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </main>
      </ProtectedRoute>
    );

  const canUpload = data.status === 'registration_open';
  return (
    <ProtectedRoute>
      <main className="min-h-screen bg-background px-4 py-8 sm:px-6">
        <div className="mx-auto max-w-5xl space-y-6">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            GCS Pulse
          </Link>
          <PageHeader title="A/B 테스트 항목 등록" description={data.title} />
          <Card className="border-primary/20 bg-primary/[0.035]">
            <CardContent className="py-5">
              <div className="flex justify-between text-sm">
                <span className="font-medium">등록된 A/B 테스트 항목</span>
                <span>{data.pairs.length}개</span>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                각 항목에 이미지 A와 이미지 B를 함께 올려 주세요. JPG·PNG·WebP 이미지 파일은 각각
                최대 8MB입니다.
              </p>
            </CardContent>
          </Card>
          {error ? (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
          {!canUpload ? (
            <Alert>
              <AlertDescription>
                A/B 테스트 항목 등록이 마감되었습니다. 등록한 이미지는 확인할 수 있습니다.
              </AlertDescription>
            </Alert>
          ) : null}

          {canUpload ? (
            <Card>
              <CardHeader>
                <CardTitle>새 A/B 테스트 항목 추가</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="ab-upload-title" className="text-sm font-medium">
                    항목 제목
                  </label>
                  <Input
                    id="ab-upload-title"
                    maxLength={200}
                    value={pairTitle}
                    onChange={(event) => setPairTitle(event.target.value)}
                    placeholder="예: 정리된 공간 메시지"
                    disabled={busy}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {(
                    [
                      { slot: 'A', selection: imageA, ref: inputA },
                      { slot: 'B', selection: imageB, ref: inputB },
                    ] as const
                  ).map(({ slot, selection, ref }) => (
                    <label
                      key={slot}
                      className="cursor-pointer space-y-2 rounded-lg border border-dashed p-3 text-center hover:border-primary"
                    >
                      <input
                        ref={ref}
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        className="sr-only"
                        disabled={busy}
                        onChange={(event) => selection.selectFile(event.target.files?.[0] ?? null)}
                      />
                      <div className="relative aspect-[4/5] overflow-hidden rounded-md bg-muted">
                        {selection.previewUrl ? (
                          <Image
                            unoptimized
                            src={selection.previewUrl}
                            alt={`선택한 이미지 ${slot} 미리보기`}
                            fill
                            className="object-contain"
                          />
                        ) : (
                          <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
                            <ImagePlus className="h-6 w-6" />
                            <span className="text-xs">미리보기</span>
                          </div>
                        )}
                      </div>
                      <span className="block text-sm font-medium">이미지 {slot} 선택</span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {selection.file?.name ?? '파일을 선택하세요'}
                      </span>
                    </label>
                  ))}
                </div>
                <div className="flex justify-end">
                  <Button
                    disabled={busy || !pairTitle.trim() || !imageA.file || !imageB.file}
                    onClick={() =>
                      void run(() =>
                        abPracticeApi.createPair(token, pairTitle, imageA.file!, imageB.file!),
                      )
                    }
                  >
                    {busy ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        업로드 중...
                      </>
                    ) : (
                      'A/B 테스트 항목 업로드'
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : null}

          <section className="space-y-3">
            <h2 className="text-lg font-semibold">등록된 A/B 테스트 항목</h2>
            {data.pairs.length === 0 ? (
              <Card className="border-dashed">
                <CardContent className="py-10 text-center text-sm text-muted-foreground">
                  아직 등록된 A/B 테스트 항목이 없습니다.
                </CardContent>
              </Card>
            ) : null}
            <div className="grid gap-4">
              {data.pairs.map((pair, index) => (
                <Card key={pair.id}>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                      <CardTitle className="text-base">
                        {pair.title}
                        {!pair.complete ? (
                          <span className="ml-2 text-xs font-normal text-amber-700">
                            이미지 등록 필요
                          </span>
                        ) : null}
                      </CardTitle>
                      <p className="mt-1 text-xs text-muted-foreground">
                        등록자: {pair.submitter_name}
                      </p>
                    </div>
                    {canUpload && pair.can_manage ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        disabled={busy}
                        onClick={() => {
                          if (window.confirm('이 A/B 테스트 항목을 삭제할까요?'))
                            void run(() => abPracticeApi.deletePair(token, pair.id));
                        }}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        항목 삭제
                      </Button>
                    ) : null}
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-3">
                    {(['a', 'b'] as const).map((slot) => {
                      const imageUrl = slot === 'a' ? pair.image_a_url : pair.image_b_url;
                      const slotLabel = `이미지 ${slot.toUpperCase()}`;
                      return (
                        <div key={slot} className="space-y-2">
                          <div className="relative aspect-[4/5] overflow-hidden rounded-lg border bg-muted">
                            {imageUrl ? (
                              <Image
                                unoptimized
                                src={asset(imageUrl)}
                                alt={`A/B 테스트 항목 ${index + 1} ${slotLabel}`}
                                fill
                                className="object-contain"
                              />
                            ) : (
                              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                                이미지가 없습니다
                              </div>
                            )}
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-semibold">{slotLabel}</span>
                            {canUpload && pair.can_manage ? (
                              <label
                                title={`${slotLabel} ${imageUrl ? '교체' : '업로드'}`}
                                className="cursor-pointer text-xs text-primary underline underline-offset-4"
                              >
                                {imageUrl ? (
                                  <>
                                    <RefreshCw className="h-4 w-4" />
                                    <span className="sr-only">{slotLabel} 교체</span>
                                  </>
                                ) : (
                                  '업로드'
                                )}
                                <input
                                  type="file"
                                  accept="image/png,image/jpeg,image/webp"
                                  className="sr-only"
                                  disabled={busy}
                                  onChange={(event) =>
                                    chooseReplace(pair.id, slot, event.target.files?.[0])
                                  }
                                />
                              </label>
                            ) : null}
                          </div>
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        </div>
      </main>
    </ProtectedRoute>
  );
}
