import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
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
import { Button } from "@/components/ui/button";

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
  structuredContent?: string | null;
  onApplyStructuredContent?: () => void;
  readOnly?: boolean;
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
  structuredContent,
  onApplyStructuredContent,
  readOnly = false,
}: SnippetAnalysisReportProps) {
  if (!feedback && !structuredContent) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-slate-500 gap-4 bg-slate-50 rounded-lg border border-slate-200">
        <p>아직 AI 분석 결과가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-6 animate-in slide-in-from-top-4 fade-in duration-500">
      {feedback && (
        <>
          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm relative overflow-hidden">
            {feedback.anchoring_message && (
              <div className="mb-6 p-4 bg-indigo-50 border-l-4 border-indigo-500 rounded-r-md">
                <p className="text-indigo-800 font-medium italic">
                  "{feedback.anchoring_message}"
                </p>
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-center gap-6">
              <div className="flex-none flex flex-col items-center">
                <div className="relative w-20 h-20 flex items-center justify-center bg-rose-50 rounded-full border-4 border-rose-100 mb-1">
                  <span className="text-2xl font-bold text-rose-700">
                    {feedback.total_score}
                  </span>
                </div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Total Score
                </span>
              </div>

              <div className="text-center sm:text-left flex-1">
                <h3 className="text-xl font-bold text-slate-800 flex items-center justify-center sm:justify-start gap-2 mb-2">
                  <Sparkles className="w-5 h-5 text-yellow-500" />
                  AI 회고 분석
                </h3>
                <p className="text-sm text-slate-600 leading-relaxed">
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
                <Brain className="w-5 h-5 text-indigo-600" />
                핵심 배움
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-lg font-medium text-slate-800 mb-4 leading-relaxed">
                {feedback.key_learning}
              </p>
              {feedback.learning_sources &&
                feedback.learning_sources.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {feedback.learning_sources.map((source, i) => (
                      <Badge
                        key={i}
                        variant="secondary"
                        className="text-slate-600 bg-slate-100 hover:bg-slate-200 px-3 py-1"
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
                <TrendingUp className="w-5 h-5 text-blue-600" />
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
                      <div className="flex justify-between items-center text-sm">
                        <span className="font-medium text-slate-700">
                          {SCORE_LABELS[key] || key}
                        </span>
                        <span className="text-slate-500 font-mono text-xs">
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
            <Card className="bg-green-50/40 border-green-200 h-full">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-medium text-green-800 flex items-center gap-2">
                  <Target className="w-5 h-5 text-green-600" />
                  다음 실행 액션
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5 flex-none" />
                  <p className="text-slate-800 font-medium leading-relaxed">
                    {feedback.next_action}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-blue-50/40 border-blue-200 h-full">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-medium text-blue-800 flex items-center gap-2">
                  <MessageCircle className="w-5 h-5 text-blue-600" />
                  멘토 코멘트
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-start gap-3">
                  <Quote className="w-5 h-5 text-blue-400 mt-0.5 flex-none" />
                  <p className="text-slate-700 leading-relaxed">
                    {feedback.mentor_comment}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {feedback.next_reflection_mission && (
            <Card className="bg-purple-50/40 border-purple-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-medium text-purple-800 flex items-center gap-2">
                  <Flag className="w-5 h-5 text-purple-600" />
                  다음 회고 미션
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-start gap-3">
                  <Lightbulb className="w-5 h-5 text-purple-500 mt-0.5 flex-none" />
                  <p className="text-slate-800 font-medium leading-relaxed">
                    {feedback.next_reflection_mission}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {structuredContent && (
        <div className="pt-6 mt-6 border-t border-slate-200 space-y-8">
          <div>
            <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-slate-500" />
              AI 정리
              {!readOnly && onApplyStructuredContent && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="ml-auto"
                  onClick={onApplyStructuredContent}
                >
                  적용하기
                </Button>
              )}
            </h3>
            <div className="prose prose-slate max-w-none text-sm text-slate-600 bg-slate-100/50 p-6 rounded-lg">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
              >
                {structuredContent}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
