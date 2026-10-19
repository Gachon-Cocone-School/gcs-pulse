'use client';

import Image from 'next/image';
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type SyntheticEvent,
} from 'react';
import { Check, CheckCircle2, Loader2, X } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { API_URL, abPracticeApi, ApiError } from '@/lib/api';
import type { ABPracticeCurrentExposureResponse } from '@/lib/types';

function asset(path?: string | null) {
  if (!path) return '';
  return path.startsWith('http') ? path : `${API_URL.replace(/\/+$/, '')}${path}`;
}

function createParticipantToken(): string {
  if (window.crypto.randomUUID) return window.crypto.randomUUID();
  const bytes = new Uint8Array(32);
  window.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

export default function ABPracticeTestPageClient({ token }: { token: string }) {
  const [current, setCurrent] = useState<ABPracticeCurrentExposureResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [needsName, setNeedsName] = useState(false);
  const [participantName, setParticipantName] = useState('');
  const [loadedImages, setLoadedImages] = useState<string[]>([]);
  const [imageAspectRatios, setImageAspectRatios] = useState<Record<string, number>>({});
  const [detailChoice, setDetailChoice] = useState<'a' | 'b' | null>(null);
  const [remainingMs, setRemainingMs] = useState(0);
  const [busy, setBusy] = useState(false);
  const [selectedChoice, setSelectedChoice] = useState<'a' | 'b' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const actionId = useRef<number | null>(null);
  const loadRequestId = useRef(0);
  const readyId = useRef<number | null>(null);
  const startingId = useRef<number | null>(null);
  const participantTokenRef = useRef<string | null>(null);
  const currentExposureIdRef = useRef<number | null>(null);
  const preloadedImagesRef = useRef(new Map<string, HTMLImageElement>());
  const imagesReady = Boolean(
    current?.image_a_url &&
      current.image_b_url &&
      loadedImages.includes(current.image_a_url) &&
      loadedImages.includes(current.image_b_url),
  );

  const loadCurrent = useCallback(
    async (identityToken: string | null = participantTokenRef.current) => {
      const requestId = ++loadRequestId.current;
      try {
        const response = await abPracticeApi.getCurrentExposure(token, identityToken);
        if (requestId !== loadRequestId.current) return;
        currentExposureIdRef.current = response.exposure_id ?? null;
        setCurrent(response);
        setNeedsName(response.status === 'needs_name');
        setSelectedChoice(null);
        setLoadedImages([]);
        setError(null);
        if (response.exposure_id) {
          readyId.current = null;
          startingId.current = null;
          actionId.current = null;
        }
      } catch (cause) {
        console.error(cause);
        if (requestId !== loadRequestId.current) return;
        setError(
          cause instanceof ApiError && cause.status === 404
            ? '실습을 찾을 수 없습니다. QR 코드를 확인해 주세요.'
            : '테스트를 열지 못했습니다. 네트워크 연결을 확인해 주세요.',
        );
      } finally {
        if (requestId === loadRequestId.current) setLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    const storageKey = `ab-practice-participant:v1:${token}`;
    let savedToken: string | null = null;
    try {
      savedToken = window.localStorage.getItem(storageKey);
    } catch {
      /* Continue with this tab if storage is unavailable. */
    }
    participantTokenRef.current = savedToken;
    void loadCurrent(savedToken);
    return () => {
      loadRequestId.current += 1;
    };
  }, [loadCurrent, token]);

  useEffect(() => {
    if (current?.status !== 'waiting') return;
    const timer = window.setInterval(() => void loadCurrent(participantTokenRef.current), 2500);
    return () => window.clearInterval(timer);
  }, [current?.status, loadCurrent]);

  const registerParticipant = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const name = participantName.trim();
      if (!name) return;
      const identityToken = participantTokenRef.current ?? createParticipantToken();
      setBusy(true);
      setError(null);
      try {
        await abPracticeApi.registerAnonymousParticipant(token, name, identityToken);
        participantTokenRef.current = identityToken;
        try {
          window.localStorage.setItem(`ab-practice-participant:v1:${token}`, identityToken);
        } catch {
          /* Keep the token in memory for this visit. */
        }
        setNeedsName(false);
        await loadCurrent(identityToken);
      } catch (cause) {
        console.error(cause);
        setError(
          cause instanceof ApiError && cause.status === 409
            ? '테스트가 종료되었습니다.'
            : '이름을 등록하지 못했습니다. 다시 시도해 주세요.',
        );
      } finally {
        setBusy(false);
      }
    },
    [loadCurrent, participantName, token],
  );

  const startTimer = useCallback(
    async (exposureId: number) => {
      if (startingId.current === exposureId || readyId.current === exposureId || !imagesReady)
        return;
      startingId.current = exposureId;
      setError(null);
      try {
        const identityToken = participantTokenRef.current;
        if (!identityToken) return;
        const response = await abPracticeApi.startExposure(token, exposureId, identityToken);
        if (currentExposureIdRef.current !== exposureId) return;
        readyId.current = exposureId;
        const deadline = new Date(response.started_at).getTime() + response.exposure_seconds * 1000;
        setRemainingMs(Math.max(0, deadline - Date.now()));
        setCurrent((previous) =>
          previous?.exposure_id === exposureId
            ? { ...previous, started_at: response.started_at }
            : previous,
        );
      } catch (cause) {
        console.error(cause);
        if (currentExposureIdRef.current !== exposureId) return;
        if (cause instanceof ApiError && cause.status === 409) {
          await loadCurrent();
        } else {
          setError('항목 노출을 시작하지 못했습니다. 네트워크가 연결되면 다시 시도해 주세요.');
        }
      } finally {
        if (startingId.current === exposureId) startingId.current = null;
      }
    },
    [imagesReady, loadCurrent, token],
  );

  useEffect(() => {
    if (!current?.exposure_id || !imagesReady) return;
    void startTimer(current.exposure_id);
  }, [current?.exposure_id, imagesReady, startTimer]);

  useEffect(() => {
    if (!imagesReady) return;
    for (const url of [current?.next_image_a_url, current?.next_image_b_url]) {
      if (!url || preloadedImagesRef.current.has(url)) continue;
      const image = new window.Image();
      image.decoding = 'async';
      image.fetchPriority = 'low';
      image.src = asset(url);
      preloadedImagesRef.current.set(url, image);
    }
  }, [current?.next_image_a_url, current?.next_image_b_url, imagesReady]);

  const submit = useCallback(
    async (choice: 'a' | 'b' | 'skip') => {
      const exposureId = current?.exposure_id;
      const identityToken = participantTokenRef.current;
      if (!exposureId || !identityToken || actionId.current === exposureId) return;
      if (choice !== 'skip') setSelectedChoice(choice);
      actionId.current = exposureId;
      setBusy(true);
      try {
        await abPracticeApi.submitVote(token, exposureId, choice, identityToken);
        await loadCurrent(identityToken);
      } catch (cause) {
        console.error(cause);
        if (cause instanceof ApiError && cause.status === 409) {
          await loadCurrent(identityToken);
        } else {
          setError('응답을 저장하지 못했습니다. 연결을 확인하고 선택을 다시 눌러 주세요.');
          actionId.current = null;
        }
      } finally {
        setBusy(false);
      }
    },
    [current?.exposure_id, loadCurrent, token],
  );

  useEffect(() => {
    if (
      !current?.exposure_id ||
      current.exposure_seconds === 0 ||
      !current.started_at ||
      readyId.current !== current.exposure_id
    )
      return;
    const deadline = new Date(current.started_at).getTime() + current.exposure_seconds * 1000;
    const tick = () => {
      const next = Math.max(0, deadline - Date.now());
      setRemainingMs(next);
      if (next <= 0) void submit('skip');
    };
    tick();
    const timer = window.setInterval(tick, 50);
    return () => window.clearInterval(timer);
  }, [current?.exposure_id, current?.exposure_seconds, current?.started_at, submit]);

  const markImageReady = useCallback(
    (exposureId: number, imageUrl: string) => {
      if (current?.exposure_id !== exposureId) return;
      setLoadedImages((previous) =>
        previous.includes(imageUrl) ? previous : [...previous, imageUrl],
      );
    },
    [current?.exposure_id],
  );

  if (loading)
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin" />
      </main>
    );

  const completed = current?.status === 'completed';
  const ended = current?.status === 'ended';
  const exposureId = current?.exposure_id ?? null;
  const isCvrMode = current?.exposure_seconds === 0;
  const timerPercent =
    current && current.exposure_seconds > 0
      ? Math.max(0, Math.min(100, (remainingMs / (current.exposure_seconds * 1000)) * 100))
      : 0;
  const leftUrl = current?.image_a_is_left ? current.image_a_url : current?.image_b_url;
  const rightUrl = current?.image_a_is_left ? current.image_b_url : current?.image_a_url;
  const leftChoice = current?.image_a_is_left ? 'a' : 'b';
  const rightChoice = current?.image_a_is_left ? 'b' : 'a';

  return (
    <main
      className={`${isCvrMode ? 'min-h-[100svh] overflow-y-auto' : 'h-[100svh] min-h-[100svh] overflow-hidden sm:h-auto sm:min-h-screen sm:overflow-visible'} bg-[#f3f2ee] px-1 py-1 text-[#1e2928] sm:px-6 sm:py-8`}
    >
      <div
        className={`mx-auto flex max-w-5xl flex-col ${isCvrMode ? 'min-h-[calc(100svh-0.5rem)] gap-3 pb-4' : 'h-full min-h-0 sm:h-auto sm:min-h-[calc(100vh-4rem)]'}`}
      >
        {error ? (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        {needsName || current?.status === 'needs_name' ? (
          <Card className="m-auto w-full max-w-sm bg-white shadow-md">
            <CardContent className="space-y-4 p-6">
              <div>
                <h1 className="text-xl font-semibold">이름을 입력해 주세요</h1>
                <p className="mt-1 text-sm text-muted-foreground">투표 참여 현황에 표시됩니다.</p>
              </div>
              <form onSubmit={(event) => void registerParticipant(event)} className="space-y-3">
                <Input
                  autoFocus
                  maxLength={100}
                  autoComplete="name"
                  placeholder="이름"
                  value={participantName}
                  onChange={(event) => setParticipantName(event.target.value)}
                  required
                />
                <Button type="submit" className="w-full" disabled={busy || !participantName.trim()}>
                  {busy ? '등록 중…' : '시작하기'}
                </Button>
              </form>
            </CardContent>
          </Card>
        ) : ended ? (
          <Card className="m-auto max-w-lg border-emerald-900/10 bg-white text-center shadow-md">
            <CardContent className="space-y-3 py-12">
              <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-700" />
              <h2 className="text-2xl font-semibold">투표가 종료됐어요</h2>
            </CardContent>
          </Card>
        ) : completed ? (
          <Card className="m-auto max-w-lg border-emerald-900/10 bg-white text-center shadow-md">
            <CardContent className="space-y-3 py-12">
              <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-700" />
              <h2 className="text-2xl font-semibold">모든 A/B 테스트 항목을 확인했어요</h2>
            </CardContent>
          </Card>
        ) : current?.status === 'waiting' ? (
          <Card className="m-auto max-w-lg bg-white text-center shadow-sm">
            <CardContent className="space-y-3 py-10">
              <Loader2 className="mx-auto h-7 w-7 animate-spin text-emerald-800" />
              <h2 className="text-xl font-semibold">
                관리자가 테스트를 시작할 때까지 기다려 주세요
              </h2>
              <p className="text-sm text-muted-foreground">
                시작되면 이 화면에 항목이 자동으로 표시됩니다.
              </p>
            </CardContent>
          </Card>
        ) : current?.status === 'voting_open' && current.exposure_id && exposureId ? (
          <section
            className={`flex min-h-0 flex-1 flex-col gap-2 ${isCvrMode ? 'sm:gap-4' : 'sm:justify-center sm:gap-4'}`}
          >
            <div className="flex shrink-0 items-end justify-between gap-3">
              <h2 className="text-base font-semibold sm:text-2xl">{current.question}</h2>
              {!isCvrMode ? (
                <span className="shrink-0 text-xl font-bold tabular-nums text-emerald-900 sm:text-3xl">
                  {Math.max(0, remainingMs / 1000).toFixed(1)}
                  <small className="ml-1 text-sm font-medium">초</small>
                </span>
              ) : null}
            </div>
            {!isCvrMode ? (
              <Progress value={timerPercent} className="h-1.5 shrink-0 bg-emerald-900/10" />
            ) : null}
            <div
              className={`grid gap-2 ${isCvrMode ? 'grid-cols-1 sm:grid-cols-2 sm:gap-5' : 'min-h-0 flex-1 grid-cols-1 grid-rows-2 sm:grid-cols-2 sm:grid-rows-1 sm:gap-5'}`}
            >
              {(isCvrMode
                ? current.image_a_is_left
                  ? [
                      { choice: 'a', url: current.image_a_url },
                      { choice: 'b', url: current.image_b_url },
                    ]
                  : [
                      { choice: 'b', url: current.image_b_url },
                      { choice: 'a', url: current.image_a_url },
                    ]
                : [
                    { choice: leftChoice, url: leftUrl },
                    { choice: rightChoice, url: rightUrl },
                  ]
              ).map((side) => {
                const choice = side.choice as 'a' | 'b';
                const selected = selectedChoice === choice;
                const anotherSelected = selectedChoice !== null && !selected;
                const onImageLoad = (event: SyntheticEvent<HTMLImageElement>) => {
                  markImageReady(exposureId, side.url ?? '');
                  const image = event.currentTarget;
                  if (image.naturalWidth && image.naturalHeight)
                    setImageAspectRatios((previous) => ({
                      ...previous,
                      [choice]: image.naturalWidth / image.naturalHeight,
                    }));
                };
                return (
                  <div
                    key={`${exposureId}-${choice}`}
                    className={`flex min-h-0 min-w-0 flex-col gap-2 rounded-xl border-2 p-1.5 transition-all duration-150 sm:gap-3 sm:p-4 ${selected ? 'border-emerald-700 bg-emerald-50 shadow-[0_0_0_4px_rgba(4,120,87,0.22),0_12px_28px_rgba(4,120,87,0.22)]' : anotherSelected ? 'border-[#1e2928]/5 bg-white opacity-40' : 'border-[#1e2928]/10 bg-white shadow-sm'}`}
                  >
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={busy || readyId.current !== exposureId}
                      onClick={() => (isCvrMode ? setDetailChoice(choice) : void submit(choice))}
                      aria-label={
                        isCvrMode ? '이미지 상세 보기' : `${choice.toUpperCase()} 항목 선택`
                      }
                      aria-pressed={!isCvrMode && selected}
                      className={`group relative flex min-h-0 min-w-0 flex-col gap-1 p-0 text-left ${isCvrMode ? 'h-auto' : 'h-full'}`}
                    >
                      <div
                        className={`relative w-full overflow-hidden rounded-lg bg-[#e8e7e1] ${isCvrMode ? 'aspect-[4/3]' : 'min-h-0 flex-1 sm:aspect-[4/5] sm:flex-none'}`}
                      >
                        <Image
                          unoptimized
                          src={asset(side.url)}
                          alt={isCvrMode ? '이미지' : `항목 ${choice.toUpperCase()}`}
                          fill
                          priority
                          className="object-contain"
                          onLoad={onImageLoad}
                        />
                        {selected ? (
                          <span className="absolute right-2 top-2 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-700 text-white shadow-lg ring-2 ring-white">
                            <Check className="h-6 w-6" strokeWidth={3} />
                          </span>
                        ) : null}
                      </div>
                      {isCvrMode ? (
                        <span className="w-full py-1 text-center text-sm font-medium">
                          상세 보기
                        </span>
                      ) : null}
                    </Button>
                    {isCvrMode ? (
                      <Button
                        type="button"
                        aria-label="이 이미지 선택"
                        disabled={busy || readyId.current !== exposureId}
                        onClick={() => void submit(choice)}
                        className="w-full"
                      >
                        선택
                      </Button>
                    ) : null}
                  </div>
                );
              })}
            </div>
            {!imagesReady ? (
              <p className="shrink-0 text-center text-xs text-muted-foreground">
                항목을 불러오는 중입니다.{isCvrMode ? '' : ' 이미지가 준비되면 시간이 시작됩니다.'}
              </p>
            ) : null}
          </section>
        ) : (
          <Card className="m-auto max-w-lg">
            <CardContent className="space-y-3 py-10 text-center">
              <Loader2 className="mx-auto h-7 w-7 animate-spin text-emerald-800" />
              <p className="font-medium">투표를 불러오는 중입니다.</p>
              <p className="text-sm text-muted-foreground">
                관리자가 테스트를 시작하면 첫 항목이 표시됩니다.
              </p>
              <Button variant="outline" onClick={() => void loadCurrent()}>
                새로고침
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
      {detailChoice && isCvrMode && exposureId ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="이미지 상세 보기"
          className="fixed inset-0 z-50 overflow-y-auto bg-[#f3f2ee]"
        >
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-black/10 bg-[#f3f2ee]/95 px-4 py-3 backdrop-blur">
            <div className="font-semibold">상세 보기</div>
            <Button
              type="button"
              variant="outline"
              size="icon"
              aria-label="상세 보기 닫기"
              onClick={() => setDetailChoice(null)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="mx-auto w-full max-w-3xl px-2 py-3 sm:px-6">
            <div
              className="relative w-full"
              style={{ aspectRatio: imageAspectRatios[detailChoice] ?? '4 / 5' }}
            >
              <Image
                unoptimized
                src={asset(detailChoice === 'a' ? current?.image_a_url : current?.image_b_url)}
                alt="상세 이미지"
                fill
                priority
                className="object-contain object-top"
              />
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
