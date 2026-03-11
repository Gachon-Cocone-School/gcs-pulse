'use client';

import Link from 'next/link';
import { redirect } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Check, Loader2, X } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';
import { peerReviewsApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type { PeerReviewSessionResponse, PeerReviewSessionResultsResponse } from '@/lib/types';

interface ProfessorPeerReviewsResultsPageClientProps {
  sessionId: number;
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return '-';
  }
  return `${value.toFixed(1)}%`;
}

function formatContribution(value: number | null): string {
  if (value === null) {
    return '-';
  }
  return value.toFixed(1);
}

function formatNumber(value: number): string {
  return value.toFixed(1);
}

function toCsvCell(value: string | number): string {
  const text = String(value);
  if (text.includes(',') || text.includes('"') || text.includes('\n')) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function downloadCsv(filename: string, rows: Array<Array<string | number>>): void {
  const csvContent = rows.map((row) => row.map(toCsvCell).join(',')).join('\n');
  const blob = new Blob([`\uFEFF${csvContent}`], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default function ProfessorPeerReviewsResultsPageClient({
  sessionId,
}: ProfessorPeerReviewsResultsPageClientProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const [session, setSession] = useState<PeerReviewSessionResponse | null>(null);
  const [results, setResults] = useState<PeerReviewSessionResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sessionResponse, resultsResponse] = await Promise.all([
        peerReviewsApi.getSession(sessionId),
        peerReviewsApi.getResults(sessionId),
      ]);
      setSession(sessionResponse);
      setResults(resultsResponse);
    } catch (e) {
      console.error(e);
      setError('결과 데이터를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      void loadPage();
    }
  }, [isAuthenticated, isLoading, loadPage]);

  const contributionRows = useMemo(() => {
    const entries = Object.entries(results?.contribution_avg_by_evaluatee ?? {});
    return entries.sort((a, b) => {
      const aValue = a[1];
      const bValue = b[1];
      if (aValue === null && bValue === null) return 0;
      if (aValue === null) return 1;
      if (bValue === null) return -1;
      return bValue - aValue;
    });
  }, [results]);

  const fitRatioRows = useMemo(() => {
    const entries = Object.entries(results?.fit_yes_ratio_by_evaluatee ?? {});
    return entries.sort((a, b) => {
      const aValue = a[1];
      const bValue = b[1];
      if (aValue === null && bValue === null) return 0;
      if (aValue === null) return 1;
      if (bValue === null) return -1;
      return bValue - aValue;
    });
  }, [results]);

  const fitRatioByEvaluatorRows = useMemo(() => {
    const entries = Object.entries(results?.fit_yes_ratio_by_evaluator ?? {});
    return entries.sort((a, b) => {
      const aValue = a[1];
      const bValue = b[1];
      if (aValue === null && bValue === null) return 0;
      if (aValue === null) return 1;
      if (bValue === null) return -1;
      return bValue - aValue;
    });
  }, [results]);

  const mySelfContributionAverage = useMemo(() => {
    if (!results) return null;
    const selfRows = results.rows.filter((row) => row.evaluator_user_id === row.evaluatee_user_id);
    if (!selfRows.length) return null;
    return selfRows.reduce((sum, row) => sum + row.contribution_percent, 0) / selfRows.length;
  }, [results]);

  const othersContributionAverage = useMemo(() => {
    if (!results) return null;
    const otherRows = results.rows.filter((row) => row.evaluator_user_id !== row.evaluatee_user_id);
    if (!otherRows.length) return null;
    return otherRows.reduce((sum, row) => sum + row.contribution_percent, 0) / otherRows.length;
  }, [results]);

  const overallFitAverageExcludingSelf = useMemo(() => {
    if (!results) return null;
    const otherRows = results.rows.filter((row) => row.evaluator_user_id !== row.evaluatee_user_id);
    if (!otherRows.length) return null;
    const yesCount = otherRows.filter((row) => row.fit_yes_no).length;
    return (yesCount / otherRows.length) * 100;
  }, [results]);

  const summaryByPersonRows = useMemo((): Array<[string, number | null, number | null, number | null]> => {
    if (!results) return [];
    const nameSet = new Set<string>([
      ...Object.keys(results.contribution_avg_by_evaluatee),
      ...Object.keys(results.fit_yes_ratio_by_evaluatee),
      ...Object.keys(results.fit_yes_ratio_by_evaluator),
    ]);
    return Array.from(nameSet)
      .sort((a, b) => a.localeCompare(b, 'ko'))
      .map((name): [string, number | null, number | null, number | null] => [
        name,
        results.contribution_avg_by_evaluatee[name] ?? null,
        results.fit_yes_ratio_by_evaluatee[name] ?? null,
        results.fit_yes_ratio_by_evaluator[name] ?? null,
      ]);
  }, [results]);

  const handleDownloadSummaryCsv = useCallback(() => {
    if (!results) return;
    const rows: Array<Array<string | number>> = [
      ['이름', '기여도평균', '적합도평균(피평가자)', '적합도평균(평가자)'],
      ...summaryByPersonRows.map(([name, contribution, fitEvaluatee, fitEvaluator]) => [
        name,
        contribution === null ? '-' : formatNumber(contribution),
        fitEvaluatee === null ? '-' : formatNumber(fitEvaluatee),
        fitEvaluator === null ? '-' : formatNumber(fitEvaluator),
      ]),
    ];
    downloadCsv(`peer-review-summary-${sessionId}.csv`, rows);
  }, [results, sessionId, summaryByPersonRows]);

  const handleDownloadDetailsCsv = useCallback(() => {
    if (!results) return;
    const rows: Array<Array<string | number>> = [
      ['평가자', '피평가자', '기여도', '적합도', '수정 시각'],
      ...results.rows.map((row) => [
        row.evaluator_name,
        row.evaluatee_name,
        row.contribution_percent,
        row.evaluator_user_id === row.evaluatee_user_id ? '-' : row.fit_yes_no ? 'Yes' : 'No',
        new Date(row.updated_at).toLocaleString('ko-KR'),
      ]),
    ];
    downloadCsv(`peer-review-details-${sessionId}.csv`, rows);
  }, [results, sessionId]);

  const handleDownloadAllCsv = useCallback(() => {
    handleDownloadSummaryCsv();
    handleDownloadDetailsCsv();
  }, [handleDownloadDetailsCsv, handleDownloadSummaryCsv]);

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
          title="동료 피드백 결과"
          description="세션별 제출 결과를 확인합니다."
          actions={
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline">
                <Link href="/professor/peer-reviews">메인으로 돌아가기</Link>
              </Button>
              <Button variant="secondary" onClick={handleDownloadAllCsv}>
                CSV 다운로드
              </Button>
            </div>
          }
        />

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {loading || !session || !results ? (
          <Card>
            <CardContent className="py-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </CardContent>
          </Card>
        ) : (
          <>
            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
              <CardHeader>
                <CardTitle>{session.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                  <div className="rounded-lg border border-border/70 bg-card/80 p-3">
                    나의 자기평가 기여율 평균: <span className="font-semibold">{formatContribution(mySelfContributionAverage)}</span>
                  </div>
                  <div className="rounded-lg border border-border/70 bg-card/80 p-3">
                    타인평가 기여율 평균: <span className="font-semibold">{formatContribution(othersContributionAverage)}</span>
                  </div>
                  <div className="rounded-lg border border-border/70 bg-card/80 p-3">
                    전체 적합도 평균(자기평가 제외): <span className="font-semibold">{formatPercent(overallFitAverageExcludingSelf)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
                <CardHeader>
                  <CardTitle>기여도 평균(피평가자별)</CardTitle>
                </CardHeader>
                <CardContent>
                  {contributionRows.length === 0 ? (
                    <div className="text-sm text-muted-foreground">아직 집계 데이터가 없습니다.</div>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {contributionRows.map(([name, value]) => (
                        <li key={name} className="flex items-center justify-between rounded-lg border border-border/70 bg-card/80 px-3 py-2">
                          <span>{name}</span>
                          <span className="font-semibold">{formatContribution(value)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>

              <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
                <CardHeader>
                  <CardTitle>적합도 Yes 비율(피평가자별)</CardTitle>
                </CardHeader>
                <CardContent>
                  {fitRatioRows.length === 0 ? (
                    <div className="text-sm text-muted-foreground">아직 집계 데이터가 없습니다.</div>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {fitRatioRows.map(([name, value]) => (
                        <li key={name} className="flex items-center justify-between rounded-lg border border-border/70 bg-card/80 px-3 py-2">
                          <span>{name}</span>
                          <span className="font-semibold">{formatPercent(value)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>

              <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
                <CardHeader>
                  <CardTitle>적합도 Yes 비율(평가자별)</CardTitle>
                </CardHeader>
                <CardContent>
                  {fitRatioByEvaluatorRows.length === 0 ? (
                    <div className="text-sm text-muted-foreground">아직 집계 데이터가 없습니다.</div>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {fitRatioByEvaluatorRows.map(([name, value]) => (
                        <li key={name} className="flex items-center justify-between rounded-lg border border-border/70 bg-card/80 px-3 py-2">
                          <span>{name}</span>
                          <span className="font-semibold">{formatPercent(value)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </div>

            <Card className="glass-card rounded-xl animate-entrance border-0 shadow-md">
              <CardHeader>
                <CardTitle>제출 상세</CardTitle>
              </CardHeader>
              <CardContent>
                {results.rows.length === 0 ? (
                  <div className="text-sm text-muted-foreground">제출 데이터가 없습니다.</div>
                ) : (
                  <div className="overflow-auto rounded-lg border border-border/70 bg-card/80">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border/70 text-left">
                          <th className="p-2">평가자</th>
                          <th className="p-2">피평가자</th>
                          <th className="p-2">기여도</th>
                          <th className="p-2">적합도</th>
                          <th className="p-2">수정 시각</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.rows.map((row) => (
                          <tr
                            key={`${row.evaluator_user_id}-${row.evaluatee_user_id}-${row.updated_at}`}
                            className="border-b border-border/50 last:border-b-0"
                          >
                            <td className="p-2">{row.evaluator_name}</td>
                            <td className="p-2">{row.evaluatee_name}</td>
                            <td className="p-2">{row.contribution_percent}</td>
                            <td className="p-2">
                              {row.evaluator_user_id === row.evaluatee_user_id ? (
                                <span className="inline-flex items-center text-muted-foreground font-semibold" title="본인 평가 제외">
                                  -
                                </span>
                              ) : row.fit_yes_no ? (
                                <span className="inline-flex items-center" style={{ color: 'var(--sys-current-fg)' }} title="Yes">
                                  <Check className="h-4 w-4" />
                                </span>
                              ) : (
                                <span className="inline-flex items-center text-muted-foreground" title="No">
                                  <X className="h-4 w-4" />
                                </span>
                              )}
                            </td>
                            <td className="p-2">{new Date(row.updated_at).toLocaleString('ko-KR')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
