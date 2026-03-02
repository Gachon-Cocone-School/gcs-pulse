'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, RefreshCw, AlertTriangle, Sparkles, MessageSquare } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { TeamSnippetFeed } from '@/components/views/TeamSnippetFeed';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/context/auth-context';
import { professorApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type {
  ProfessorOverviewResponse,
  ProfessorRiskQueueItem,
  ProfessorRiskQueueResponse,
  StudentRiskSnapshot,
  RiskReason,
  RiskTonePolicy,
  RiskBand,
} from '@/lib/types';

const DEFAULT_OVERVIEW: ProfessorOverviewResponse = {
  high_or_critical_count: 0,
  high_count: 0,
  critical_count: 0,
  medium_count: 0,
  low_count: 0,
};

const COMMENT_TONES = ['격려', '제안', '질문', '훈계'] as const;
type CommentTone = (typeof COMMENT_TONES)[number];
type CommentToneMap = Record<CommentTone, string>;

function toCommentTone(value: string): CommentTone {
  if ((COMMENT_TONES as readonly string[]).includes(value)) {
    return value as CommentTone;
  }
  return '격려';
}

function formatRiskBandLabel(band: RiskBand) {
  if (band === 'Critical') return 'Critical';
  if (band === 'High') return 'High';
  if (band === 'Medium') return 'Medium';
  return 'Low';
}

function riskBadgeClass(band: RiskBand) {
  if (band === 'Critical') return 'bg-red-100 text-red-700 border-red-200';
  if (band === 'High') return 'bg-amber-100 text-amber-800 border-amber-200';
  if (band === 'Medium') return 'bg-blue-100 text-blue-700 border-blue-200';
  return 'bg-emerald-100 text-emerald-700 border-emerald-200';
}

function reasonPromptSummary(reason: RiskReason) {
  if (!reason.prompt_items?.length) return reason.risk_factor;
  return reason.prompt_items.slice(0, 2).join(', ');
}

function buildProfessorCommentTemplate(tonePolicy?: RiskTonePolicy | null, reasons?: RiskReason[]) {
  const primary = tonePolicy?.primary ?? '질문';
  const topReason = reasons?.[0];
  const reasonHint = topReason ? reasonPromptSummary(topReason) : '학습 흐름 점검';

  if (primary === '격려') {
    return `이번 주에도 기록을 이어가고 있어서 좋습니다.\n\n특히 ${reasonHint} 기준으로 보면 회복의 단서가 보입니다.\n다음 기록에서는 내일 바로 실행할 행동 1가지를 더 구체적으로 적어볼까요?`;
  }

  if (primary === '제안') {
    return `좋은 회고였습니다.\n\n${reasonHint} 관점에서 다음 주에는 우선순위를 1~2개로 좁혀 실행 계획을 분명히 해보면 좋겠습니다.\n이번 주에 가장 먼저 시도할 한 가지를 댓글로 남겨주세요.`;
  }

  if (primary === '훈계') {
    return `같은 미이행 패턴이 반복되고 있습니다.\n\n${reasonHint} 항목에서 개선이 필요합니다.\n다음 기록에는 실행 완료 기준과 체크 시점을 반드시 포함해 주세요.`;
  }

  return `이번 기록 잘 확인했습니다.\n\n${reasonHint} 항목을 기준으로 보면 추가 점검이 필요해 보입니다.\n현재 가장 막히는 지점이 무엇인지, 그리고 내일 시도할 행동 1가지를 구체적으로 적어주세요.`;
}

function getStudentSnippetPath(item: ProfessorRiskQueueItem): string | null {
  if (typeof item.latest_weekly_snippet_id === 'number') {
    return `/weekly-snippets?view=team&id=${item.latest_weekly_snippet_id}`;
  }
  if (typeof item.latest_daily_snippet_id === 'number') {
    return `/daily-snippets?view=team&id=${item.latest_daily_snippet_id}`;
  }
  return null;
}

function KpiCard({ title, value, tone }: { title: string; value: number; tone: 'critical' | 'high' | 'medium' | 'low' }) {
  const toneClass =
    tone === 'critical'
      ? 'text-red-600'
      : tone === 'high'
        ? 'text-amber-600'
        : tone === 'medium'
          ? 'text-blue-600'
          : 'text-emerald-600';

  return (
    <Card className="border-slate-200 bg-white/80">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-slate-600">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className={`text-3xl font-bold ${toneClass}`}>{value}</p>
      </CardContent>
    </Card>
  );
}

function RiskReasons({ reasons }: { reasons: RiskReason[] }) {
  if (!reasons.length) {
    return <p className="text-sm text-slate-500">표시할 위험 근거가 없습니다.</p>;
  }

  return (
    <div className="space-y-2">
      {reasons.slice(0, 3).map((reason, index) => (
        <div key={`${reason.risk_factor}-${index}`} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-slate-800">{reason.risk_factor}</p>
            <span className="text-xs font-semibold text-slate-500">impact {reason.impact.toFixed(1)}</span>
          </div>
          <p className="mt-1 text-xs text-slate-600">{reasonPromptSummary(reason)}</p>
          <p className="mt-1 text-xs text-slate-500">{reason.evidence}</p>
        </div>
      ))}
    </div>
  );
}

function StudentHistoryPanel({ history }: { history: StudentRiskSnapshot[] }) {
  if (!history.length) {
    return <p className="text-sm text-slate-500">이전 위험도 기록이 없습니다.</p>;
  }

  return (
    <div className="space-y-2">
      {history.map((snapshot) => (
        <div
          key={`${snapshot.user_id}-${snapshot.evaluated_at}`}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Badge className={riskBadgeClass(snapshot.risk_band)}>{formatRiskBandLabel(snapshot.risk_band)}</Badge>
              <span className="text-sm font-semibold text-slate-800">{snapshot.risk_score.toFixed(1)}점</span>
            </div>
            <span className="text-xs text-slate-500">
              {new Date(snapshot.evaluated_at).toLocaleString('ko-KR')}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-600">
            L1 {snapshot.l1.toFixed(1)} · L2 {snapshot.l2.toFixed(1)} · L3 {snapshot.l3.toFixed(1)}
          </p>
        </div>
      ))}
    </div>
  );
}

function CommentToneTabs({
  templateMap,
  selectedTone,
  onToneChange,
  draft,
  onDraftChange,
}: {
  templateMap: CommentToneMap;
  selectedTone: CommentTone;
  onToneChange: (value: string) => void;
  draft: string;
  onDraftChange: (value: string) => void;
}) {
  return (
    <Tabs value={selectedTone} onValueChange={onToneChange} className="w-full">
      <TabsList>
        {COMMENT_TONES.map((tone) => (
          <TabsTrigger key={tone} value={tone}>
            {tone}
          </TabsTrigger>
        ))}
      </TabsList>

      {COMMENT_TONES.map((tone) => (
        <TabsContent key={tone} value={tone} className="mt-3">
          <div className="space-y-2">
            <p className="text-xs text-slate-500">추천 초안</p>
            <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm whitespace-pre-wrap">
              {templateMap[tone]}
            </div>
            <p className="text-xs text-slate-500">최종 전송 내용(수정 가능)</p>
            <textarea
              className="min-h-[140px] w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-rose-300"
              value={draft}
              onChange={(event) => onDraftChange(event.target.value)}
            />
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
}

export default function ProfessorPageClient() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();

  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const [overview, setOverview] = React.useState<ProfessorOverviewResponse>(DEFAULT_OVERVIEW);
  const [queue, setQueue] = React.useState<ProfessorRiskQueueItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const [selectedUserId, setSelectedUserId] = React.useState<number | null>(null);
  const [selectedItem, setSelectedItem] = React.useState<ProfessorRiskQueueItem | null>(null);
  const [history, setHistory] = React.useState<StudentRiskSnapshot[]>([]);
  const [historyLoading, setHistoryLoading] = React.useState(false);
  const [evaluating, setEvaluating] = React.useState(false);
  const [selectedView, setSelectedView] = React.useState<'weekly' | 'daily' | null>(null);

  const [selectedTone, setSelectedTone] = React.useState<CommentTone>('격려');
  const [commentDraft, setCommentDraft] = React.useState('');

  const loadProfessorData = React.useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [overviewRes, queueRes] = await Promise.all([
        professorApi.overview(),
        professorApi.riskQueue({ limit: 30 }),
      ]);

      setOverview(overviewRes);
      setQueue((queueRes as ProfessorRiskQueueResponse).items ?? []);

      const first = (queueRes as ProfessorRiskQueueResponse).items?.[0] ?? null;
      if (first) {
        setSelectedUserId(first.user_id);
        setSelectedItem(first);
        setSelectedView(
          typeof first.latest_weekly_snippet_id === 'number'
            ? 'weekly'
            : typeof first.latest_daily_snippet_id === 'number'
              ? 'daily'
              : null,
        );
      } else {
        setSelectedUserId(null);
        setSelectedItem(null);
        setSelectedView(null);
        setHistory([]);
      }
    } catch (loadError) {
      console.error('Failed to load professor page data', loadError);
      setError('교수 데이터 로드에 실패했습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    if (hasAccess && isProfessor) {
      void loadProfessorData();
    }
  }, [isLoading, isAuthenticated, hasAccess, isProfessor, router, loadProfessorData]);

  React.useEffect(() => {
    if (!selectedUserId) return;

    const selected = queue.find((item) => item.user_id === selectedUserId) ?? null;
    setSelectedItem(selected);

    if (!selected) {
      setCommentDraft('');
      setSelectedView(null);
      return;
    }

    const primaryDraft = buildProfessorCommentTemplate(selected.tone_policy, selected.reasons);
    setSelectedTone(toCommentTone(selected.tone_policy?.primary ?? '격려'));
    setCommentDraft(primaryDraft);

    if (typeof selected.latest_weekly_snippet_id === 'number') {
      setSelectedView('weekly');
    } else if (typeof selected.latest_daily_snippet_id === 'number') {
      setSelectedView('daily');
    } else {
      setSelectedView(null);
    }
  }, [selectedUserId, queue]);

  React.useEffect(() => {
    if (!selectedUserId) {
      setHistory([]);
      return;
    }

    let mounted = true;
    const loadHistory = async () => {
      setHistoryLoading(true);
      try {
        const res = await professorApi.riskHistory(selectedUserId, { limit: 12 });
        if (!mounted) return;
        setHistory(res.items ?? []);
      } catch (historyError) {
        console.error('Failed to load student risk history', historyError);
        if (mounted) setHistory([]);
      } finally {
        if (mounted) setHistoryLoading(false);
      }
    };

    void loadHistory();

    return () => {
      mounted = false;
    };
  }, [selectedUserId]);

  const handleEvaluate = React.useCallback(async () => {
    if (!selectedUserId) return;

    setEvaluating(true);
    try {
      await professorApi.riskEvaluate(selectedUserId);
      const [queueRes, historyRes] = await Promise.all([
        professorApi.riskQueue({ limit: 30 }),
        professorApi.riskHistory(selectedUserId, { limit: 12 }),
      ]);
      setQueue(queueRes.items ?? []);
      setHistory(historyRes.items ?? []);
    } catch (evaluateError) {
      console.error('Failed to evaluate student risk', evaluateError);
    } finally {
      setEvaluating(false);
    }
  }, [selectedUserId]);

  const toneTemplateMap = React.useMemo<CommentToneMap>(() => {
    const baseReasons = selectedItem?.reasons ?? [];
    const basePolicy = selectedItem?.tone_policy;

    return {
      격려: buildProfessorCommentTemplate({ ...(basePolicy ?? {}), primary: '격려' } as RiskTonePolicy, baseReasons),
      제안: buildProfessorCommentTemplate({ ...(basePolicy ?? {}), primary: '제안' } as RiskTonePolicy, baseReasons),
      질문: buildProfessorCommentTemplate({ ...(basePolicy ?? {}), primary: '질문' } as RiskTonePolicy, baseReasons),
      훈계: buildProfessorCommentTemplate({ ...(basePolicy ?? {}), primary: '훈계' } as RiskTonePolicy, baseReasons),
    };
  }, [selectedItem]);

  const handleToneChange = React.useCallback(
    (tone: string) => {
      const normalizedTone = toCommentTone(tone);
      setSelectedTone(normalizedTone);
      setCommentDraft(toneTemplateMap[normalizedTone]);
    },
    [toneTemplateMap],
  );

  const handleMoveToStudentSnippet = React.useCallback(() => {
    if (!selectedItem) return;
    const path = getStudentSnippetPath(selectedItem);
    if (!path) return;
    router.push(path);
  }, [selectedItem, router]);

  if (isLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-rose-500 animate-spin" />
          <p className="text-slate-500 font-medium">교수 멘토링 화면을 준비 중입니다...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (!hasAccess || !isProfessor) {
    return <AccessDeniedView reason="student-only" />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 bg-mesh">
        <Navigation />
        <main className="max-w-7xl mx-auto px-6 py-8">
          <Card className="border-rose-200 bg-rose-50/70">
            <CardContent className="py-8">
              <div className="flex flex-col items-center gap-3 text-center">
                <AlertTriangle className="h-8 w-8 text-rose-600" />
                <p className="text-sm text-rose-700">{error}</p>
                <Button onClick={() => void loadProfessorData()} variant="outline" className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  다시 시도
                </Button>
              </div>
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 bg-mesh">
      <Navigation />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        <PageHeader
          title="교수 멘토링"
          description="Risk-driven 큐를 기반으로 개입 우선순위를 정하고 코멘트를 작성하세요."
          actions={
            <Button variant="outline" className="gap-2" onClick={() => void loadProfessorData()}>
              <RefreshCw className="h-4 w-4" />
              새로고침
            </Button>
          }
        />

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <KpiCard title="High+Critical" value={overview.high_or_critical_count} tone="critical" />
          <KpiCard title="Critical" value={overview.critical_count} tone="critical" />
          <KpiCard title="High" value={overview.high_count} tone="high" />
          <KpiCard title="Medium" value={overview.medium_count} tone="medium" />
          <KpiCard title="Low" value={overview.low_count} tone="low" />
        </section>

        <section className="grid grid-cols-1 gap-6 xl:grid-cols-[360px_1fr]">
          <Card className="border-slate-200 bg-white/80">
            <CardHeader>
              <CardTitle className="text-lg">Risk Queue</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {!queue.length ? (
                <p className="text-sm text-slate-500">현재 고위험 큐가 비어 있습니다.</p>
              ) : (
                queue.map((item) => {
                  const active = selectedUserId === item.user_id;
                  return (
                    <button
                      key={item.user_id}
                      type="button"
                      onClick={() => setSelectedUserId(item.user_id)}
                      className={`w-full rounded-lg border px-3 py-3 text-left transition-colors ${
                        active
                          ? 'border-rose-300 bg-rose-50'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-900">{item.user_name}</p>
                        <Badge className={riskBadgeClass(item.risk_band)}>{formatRiskBandLabel(item.risk_band)}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-slate-600">{item.user_email}</p>
                      <p className="mt-2 text-xs font-semibold text-slate-700">
                        score {item.risk_score.toFixed(1)} · conf {item.confidence.toFixed(2)}
                      </p>
                    </button>
                  );
                })
              )}

              <Button
                variant="outline"
                className="w-full"
                onClick={() => {
                  if (!queue.length) return;
                  const currentIndex = queue.findIndex((item) => item.user_id === selectedUserId);
                  const next = queue[(currentIndex + 1) % queue.length] ?? queue[0];
                  if (next) setSelectedUserId(next.user_id);
                }}
                disabled={!queue.length}
              >
                다음 고위험 학생
              </Button>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="border-slate-200 bg-white/80">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-lg">선택 학생 분석</CardTitle>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => void handleEvaluate()}
                    disabled={!selectedUserId || evaluating}
                    className="gap-2"
                  >
                    {evaluating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    risk-evaluate
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleMoveToStudentSnippet}
                    disabled={!selectedItem || !getStudentSnippetPath(selectedItem)}
                    className="gap-2"
                  >
                    <MessageSquare className="h-4 w-4" />
                    스니펫으로 이동
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {!selectedItem ? (
                  <p className="text-sm text-slate-500">학생을 선택하면 상세 분석이 표시됩니다.</p>
                ) : (
                  <>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className={riskBadgeClass(selectedItem.risk_band)}>
                        {formatRiskBandLabel(selectedItem.risk_band)}
                      </Badge>
                      <span className="text-sm font-semibold text-slate-800">
                        Risk {selectedItem.risk_score.toFixed(1)}
                      </span>
                      <span className="text-sm text-slate-500">
                        평가 시각 {new Date(selectedItem.evaluated_at).toLocaleString('ko-KR')}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                      <div>
                        <h3 className="mb-2 text-sm font-semibold text-slate-700">Top Reasons</h3>
                        <RiskReasons reasons={selectedItem.reasons} />
                      </div>

                      <div>
                        <h3 className="mb-2 text-sm font-semibold text-slate-700">Risk History</h3>
                        {historyLoading ? (
                          <div className="flex items-center gap-2 text-sm text-slate-500">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            히스토리 로딩 중...
                          </div>
                        ) : (
                          <StudentHistoryPanel history={history} />
                        )}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-white/80">
              <CardHeader>
                <CardTitle className="text-lg">추천 코멘트 탭 (자동 전송 없음)</CardTitle>
              </CardHeader>
              <CardContent>
                {!selectedItem ? (
                  <p className="text-sm text-slate-500">학생 선택 후 코멘트 템플릿을 확인할 수 있습니다.</p>
                ) : (
                  <>
                    <CommentToneTabs
                      templateMap={toneTemplateMap}
                      selectedTone={selectedTone}
                      onToneChange={handleToneChange}
                      draft={commentDraft}
                      onDraftChange={setCommentDraft}
                    />
                    <p className="mt-3 text-xs text-slate-500">
                      아래 팀 피드에서 해당 스니펫의 댓글 영역을 열고, 수정한 내용을 수동으로 전송하세요.
                    </p>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="text-lg font-semibold text-slate-900">선택 학생 스니펫 피드 (교수 코멘트)</h3>
          {selectedItem && getStudentSnippetPath(selectedItem) ? (
            <>
              <Tabs
                value={selectedView ?? 'weekly'}
                onValueChange={(value) => setSelectedView(value as 'weekly' | 'daily')}
              >
                <TabsList>
                  <TabsTrigger
                    value="weekly"
                    disabled={typeof selectedItem.latest_weekly_snippet_id !== 'number'}
                  >
                    주간 스니펫
                  </TabsTrigger>
                  <TabsTrigger
                    value="daily"
                    disabled={typeof selectedItem.latest_daily_snippet_id !== 'number'}
                  >
                    일간 스니펫
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="weekly" className="mt-3">
                  {typeof selectedItem.latest_weekly_snippet_id === 'number' ? (
                    <TeamSnippetFeed
                      kind="weekly"
                      id={selectedItem.latest_weekly_snippet_id}
                      commentType="professor"
                    />
                  ) : (
                    <Card className="border-slate-200 bg-white/80">
                      <CardContent className="py-6 text-sm text-slate-500">
                        최신 주간 스니펫이 없습니다.
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>
                <TabsContent value="daily" className="mt-3">
                  {typeof selectedItem.latest_daily_snippet_id === 'number' ? (
                    <TeamSnippetFeed
                      kind="daily"
                      id={selectedItem.latest_daily_snippet_id}
                      commentType="professor"
                    />
                  ) : (
                    <Card className="border-slate-200 bg-white/80">
                      <CardContent className="py-6 text-sm text-slate-500">
                        최신 일간 스니펫이 없습니다.
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>
              </Tabs>
            </>
          ) : (
            <Card className="border-slate-200 bg-white/80">
              <CardContent className="py-6 text-sm text-slate-500">
                Risk Queue에서 학생을 선택하면 해당 학생의 스니펫 피드가 표시됩니다.
              </CardContent>
            </Card>
          )}
        </section>
      </main>
    </div>
  );
}
