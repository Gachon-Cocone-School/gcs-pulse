'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { redirect } from 'next/navigation';
import { Activity, CheckCircle2, Loader2 } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/context/auth-context';
import { ApiError, createPeerReviewSessionStatusSse, peerReviewsApi } from '@/lib/api';
import type { PeerReviewFormResponse } from '@/lib/types';

interface PeerReviewFormPageClientProps {
  token: string;
}

type EntryState = {
  evaluateeUserId: number;
  evaluateeName: string;
  contributionPercent: number;
  fitYesNo: boolean;
};
function buildInitialContributionValues(count: number): number[] {
  if (count <= 0) {
    return [];
  }
  const base = Math.floor(100 / count);
  const remainder = 100 - base * count;
  return Array.from({ length: count }, (_, index) => base + (index < remainder ? 1 : 0));
}

function sum(values: number[]): number {
  return values.reduce((acc, value) => acc + value, 0);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function allocateIntegers(rawValues: number[], targetTotal: number): number[] {
  if (rawValues.length === 0) {
    return [];
  }

  const floors = rawValues.map((value) => Math.floor(value));
  let remainder = targetTotal - sum(floors);

  const ranked = rawValues
    .map((value, index) => ({ index, fractional: value - Math.floor(value) }))
    .sort((a, b) => b.fractional - a.fractional);

  for (let i = 0; i < ranked.length && remainder > 0; i += 1) {
    floors[ranked[i].index] += 1;
    remainder -= 1;
  }

  return floors;
}

function redistributeKeepingPrefix(values: number[], index: number, nextValue: number): number[] {
  const normalizedValues = values.map((value) => Math.max(0, Math.round(value)));
  const prefix = normalizedValues.slice(0, index);
  const prefixSum = sum(prefix);
  const tailCount = normalizedValues.length - index - 1;

  if (tailCount <= 0) {
    return [...prefix, Math.max(0, 100 - prefixSum)];
  }

  const maxCurrent = Math.max(0, 100 - prefixSum);
  const current = clamp(Math.round(nextValue), 0, maxCurrent);
  const remaining = 100 - prefixSum - current;
  const tailValues = normalizedValues.slice(index + 1);
  const tailSum = sum(tailValues);

  let redistributedTail: number[];
  if (remaining <= 0) {
    redistributedTail = Array.from({ length: tailCount }, () => 0);
  } else if (tailSum <= 0) {
    redistributedTail = allocateIntegers(Array.from({ length: tailCount }, () => remaining / tailCount), remaining);
  } else {
    const raw = tailValues.map((value) => (value / tailSum) * remaining);
    redistributedTail = allocateIntegers(raw, remaining);
  }

  return [...prefix, current, ...redistributedTail];
}

function buildInitialEntries(form: PeerReviewFormResponse): EntryState[] {
  const initialContributions = buildInitialContributionValues(form.team_members.length);
  return form.team_members.map((member, index) => ({
    evaluateeUserId: member.id,
    evaluateeName: member.name,
    contributionPercent: initialContributions[index] ?? 0,
    fitYesNo: true,
  }));
}

export default function PeerReviewFormPageClient({ token }: PeerReviewFormPageClientProps) {
  const { isAuthenticated, isLoading } = useAuth();

  const [form, setForm] = useState<PeerReviewFormResponse | null>(null);
  const [entries, setEntries] = useState<EntryState[]>([]);

  const [uiState, setUiState] = useState<{ loading: boolean; submitting: boolean; error: string | null }>({
    loading: true,
    submitting: false,
    error: null,
  });

  const contributionTotal = useMemo(() => entries.reduce((acc, entry) => acc + entry.contributionPercent, 0), [entries]);

  const loadForm = useCallback(async () => {
    setUiState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await peerReviewsApi.getForm(token);
      setForm(response);
      setEntries(buildInitialEntries(response));

    } catch (e) {
      if (e instanceof ApiError && e.status === 0) {
        setUiState((prev) => ({ ...prev, error: '서버에 연결하지 못했습니다. 네트워크 또는 브라우저 CORS/쿠키 설정을 확인해 주세요.' }));
      } else {
        console.error(e);
        setUiState((prev) => ({ ...prev, error: '피드백 폼을 불러오지 못했습니다. 링크와 권한을 확인해 주세요.' }));
      }
    } finally {
      setUiState((prev) => ({ ...prev, loading: false }));
    }
  }, [token]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      void loadForm();
    }
  }, [isAuthenticated, isLoading, loadForm]);

  useEffect(() => {
    if (!isAuthenticated || !form) {
      return;
    }

    const source = createPeerReviewSessionStatusSse((payload) => {
      if (payload.session_id !== form.session.session_id) {
        return;
      }

      setForm((prev) => {
        if (!prev || prev.session.session_id !== payload.session_id) {
          return prev;
        }
        return {
          ...prev,
          session: {
            ...prev.session,
            is_open: payload.is_open,
          },
        };
      });

      if (!payload.is_open) {
        setUiState((prev) => ({ ...prev, error: prev.error ?? '세션이 종료되어 제출할 수 없습니다.' }));
      }
    });

    return () => {
      source.close();
    };
  }, [form, isAuthenticated]);

  const handleContributionChange = useCallback((index: number, value: number) => {
    setEntries((prev) => {
      const values = prev.map((entry) => entry.contributionPercent);
      const maxCurrent = Math.max(0, 100 - values.slice(0, index).reduce((acc, item) => acc + item, 0));
      const clamped = clamp(Math.round(value), 0, maxCurrent);
      const redistributed = redistributeKeepingPrefix(values, index, clamped);
      return prev.map((entry, entryIndex) => ({
        ...entry,
        contributionPercent: redistributed[entryIndex] ?? 0,
      }));
    });
  }, []);

  const handleFitChange = useCallback((evaluateeUserId: number, fitYesNo: boolean) => {
    setEntries((prev) =>
      prev.map((entry) => (entry.evaluateeUserId === evaluateeUserId ? { ...entry, fitYesNo } : entry)),
    );
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!form) return;

    const normalizedEntries = entries.map((entry) => ({
      evaluatee_user_id: entry.evaluateeUserId,
      contribution_percent: entry.contributionPercent,
      fit_yes_no: entry.fitYesNo,
    }));

    if (normalizedEntries.some((entry) => !Number.isInteger(entry.contribution_percent) || entry.contribution_percent < 0)) {
      setUiState((prev) => ({ ...prev, error: '기여율은 0 이상의 정수만 입력할 수 있습니다.' }));
      return;
    }

    if (contributionTotal !== 100) {
      setUiState((prev) => ({ ...prev, error: `기여율 합계는 100이어야 합니다. 현재 ${contributionTotal}입니다.` }));
      return;
    }

    setUiState((prev) => ({ ...prev, submitting: true, error: null }));

    try {
      await peerReviewsApi.submitForm(token, {
        entries: normalizedEntries,
      });

      const refreshedForm = await peerReviewsApi.getForm(token);
      setForm(refreshedForm);
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) {
        setUiState((prev) => ({ ...prev, error: '제출 요청이 서버에 도달하지 못했습니다. 네트워크 또는 브라우저 CORS/쿠키 설정을 확인해 주세요.' }));
      } else if (e instanceof ApiError && e.status === 409) {
        setUiState((prev) => ({ ...prev, error: '세션이 종료되어 제출할 수 없습니다.' }));
        setForm((prev) =>
          prev
            ? {
                ...prev,
                session: {
                  ...prev.session,
                  is_open: false,
                },
              }
            : prev,
        );
      } else {
        console.error(e);
        setUiState((prev) => ({ ...prev, error: '제출에 실패했습니다. 입력값을 확인하고 다시 시도해 주세요.' }));
      }
    } finally {
      setUiState((prev) => ({ ...prev, submitting: false }));
    }
  }, [contributionTotal, entries, form, token]);

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

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-4xl px-6 py-8 space-y-6">
        <PageHeader title="동료 피드백 폼" description="팀원별 기여율(합계 100)과 fit 여부를 입력해 제출하세요." />

        {uiState.loading ? (
          <Card>
            <CardContent className="py-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </CardContent>
          </Card>
        ) : null}

        {uiState.error ? (
          <Alert variant="destructive">
            <AlertDescription>{uiState.error}</AlertDescription>
          </Alert>
        ) : null}


        {form ? (
          <>
            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 space-y-3">
                    <div className="truncate text-base font-semibold text-card-foreground">{form.session.title}</div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1.5">
                        <Activity className="h-3.5 w-3.5" />
                        {form.session.is_open ? '진행중' : '종료'}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        {form.has_submitted ? '제출완료' : '미제출'}
                      </span>
                    </div>
                  </div>
                  <Button onClick={handleSubmit} disabled={uiState.submitting || !form.session.is_open} className="shrink-0">
                    {uiState.submitting ? '제출 중...' : form.has_submitted ? '다시 제출' : '제출'}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
              <CardHeader>
                <CardTitle>팀원 기여율 및 적합도</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-sm font-medium">현재 합계: {contributionTotal} / 100</div>
                <div className="space-y-3">
                  {entries.map((entry, index) => {
                    const maxCurrent = Math.max(
                      0,
                      100 - entries.slice(0, index).reduce((acc, item) => acc + item.contributionPercent, 0),
                    );
                    const isSelf = form.me.id === entry.evaluateeUserId;
                    const isLockedRow = index === entries.length - 1;

                    return (
                      <div key={entry.evaluateeUserId} className="rounded-lg border border-border/70 bg-card/80 p-3 space-y-3">
                        <div className="font-medium text-card-foreground">{entry.evaluateeName}</div>
                        <div className="grid gap-2">
                          <div className="flex items-center justify-between text-sm">
                            <span>기여율</span>
                            <span data-testid={`contribution-value-${entry.evaluateeUserId}`}>{entry.contributionPercent}%</span>
                          </div>
                          <input
                            type="range"
                            min={0}
                            max={100}
                            value={entry.contributionPercent}
                            disabled={isLockedRow}
                            className="w-full accent-current disabled:opacity-50"
                            onChange={(event) => handleContributionChange(index, Number(event.target.value))}
                            data-testid={`contribution-slider-${entry.evaluateeUserId}`}
                          />
                          {!isLockedRow && maxCurrent < 100 ? (
                            <div className="text-xs text-muted-foreground">현재 입력 가능 최대값: {maxCurrent}%</div>
                          ) : null}
                        </div>
                        {!isSelf ? (
                          <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                            <input
                              type="checkbox"
                              checked={entry.fitYesNo}
                              className="h-4 w-4 accent-current"
                              onChange={(event) => handleFitChange(entry.evaluateeUserId, event.target.checked)}
                              data-testid={`fit-checkbox-${entry.evaluateeUserId}`}
                            />
                            fit
                          </label>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

          </>
        ) : null}
      </main>
    </div>
  );
}
