import {
  Sparkles,
  Brain,
  TrendingUp,
  Target,
  CheckCircle2,
  MessageCircle,
  Quote,
  Flag,
  Lightbulb,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export interface Feedback {
  total_score: number;
  scores: Record<string, { score: number; max_score: number }>;
  key_learning: string;
  learning_sources: string[];
  next_action: string;
  mentor_comment: string;
  next_reflection_mission?: string;
  anchoring_message?: string;
}

interface SnippetAnalysisReportProps {
  feedback: Feedback | null;
}

const SCORE_LABELS: Record<string, string> = {
  record_completeness: "기록 충실도",
  learning_signal_detection: "배움 포착",
  cause_effect_connection: "인과 연결",
  action_translation: "행동 전환",
  learning_attitude_consistency: "태도 일관성",
};

export function SnippetAnalysisReport({
  feedback,
}: SnippetAnalysisReportProps) {
  if (!feedback) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-border bg-muted/30 py-10 text-muted-foreground">
        <p>아직 AI 분석 결과가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="animate-in slide-in-from-top-4 fade-in space-y-6 pb-6 duration-500">
      <div className="relative overflow-hidden rounded-lg border border-border bg-card p-6 shadow-sm">
        {feedback.anchoring_message && (
          <div className="mb-6 rounded-r-md border-l-4 border-primary/40 bg-primary/10 p-4">
            <p className="font-medium italic text-primary">"{feedback.anchoring_message}"</p>
          </div>
        )}

        <div className="flex flex-col items-center gap-6 sm:flex-row">
          <div className="flex-none flex flex-col items-center">
            <div className="relative mb-1 flex h-20 w-20 items-center justify-center rounded-full border-4 border-primary/20 bg-primary/10">
              <span className="text-2xl font-bold text-primary">
                {feedback.total_score}
              </span>
            </div>
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Score
            </span>
          </div>

          <div className="flex-1 text-center sm:text-left">
            <h3 className="mb-2 flex items-center justify-center gap-2 text-xl font-bold text-foreground sm:justify-start">
              <Sparkles className="h-5 w-5 text-primary" />
              AI 회고 분석
            </h3>
            <p className="text-sm leading-relaxed text-muted-foreground">
              오늘의 회고 내용을 바탕으로 학습 성장도를 분석했습니다.
              <br className="hidden sm:block" />
              지속적인 기록으로 더 나은 성장을 만들어가세요.
            </p>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-5 w-5 text-primary" />
            핵심 배움
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-lg font-medium leading-relaxed text-foreground">
            {feedback.key_learning}
          </p>
          {feedback.learning_sources &&
            feedback.learning_sources.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {feedback.learning_sources.map((source) => (
                  <Badge
                    key={source}
                    variant="secondary"
                    className="bg-muted px-3 py-1 text-muted-foreground hover:bg-muted/80"
                  >
                    #{source}
                  </Badge>
                ))}
              </div>
            )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-5 w-5 text-primary" />
            상세 분석
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {feedback.scores &&
            Object.entries(feedback.scores).map(([key, value]) => {
              const scoreData =
                typeof value === "number"
                  ? { score: value, max_score: 10 }
                  : value;
              const percentage =
                (scoreData.score / scoreData.max_score) * 100;

              return (
                <div key={key} className="space-y-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-foreground">
                      {SCORE_LABELS[key] || key}
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {scoreData.score} / {scoreData.max_score}
                    </span>
                  </div>
                  <Progress value={percentage} className="h-2" />
                </div>
              );
            })}
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="h-full border-border bg-muted/30">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base font-medium text-foreground">
              <Target className="h-5 w-5 text-primary" />
              다음 실행 액션
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-5 w-5 flex-none text-primary" />
              <p className="font-medium leading-relaxed text-foreground">
                {feedback.next_action}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="h-full border-border bg-muted/30">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base font-medium text-foreground">
              <MessageCircle className="h-5 w-5 text-primary" />
              멘토 코멘트
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-3">
              <Quote className="mt-0.5 h-5 w-5 flex-none text-primary" />
              <p className="leading-relaxed text-foreground">
                {feedback.mentor_comment}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {feedback.next_reflection_mission && (
        <Card className="border-border bg-muted/30">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base font-medium text-foreground">
              <Flag className="h-5 w-5 text-primary" />
              다음 회고 미션
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-3">
              <Lightbulb className="mt-0.5 h-5 w-5 flex-none text-primary" />
              <p className="font-medium leading-relaxed text-foreground">
                {feedback.next_reflection_mission}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
