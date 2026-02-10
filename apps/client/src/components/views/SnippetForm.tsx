"use client";

import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import {
  AlertCircle,
  CheckCircle2,
  Sparkles,
  Brain,
  Quote,
  Target,
  BookOpen,
  TrendingUp,
  MessageCircle,
  Lightbulb,
  Flag,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/api";

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

interface SnippetFormProps {
  kind: "daily" | "weekly";
  initialContent?: string;
  onSave?: (content: string) => Promise<void>;
  readOnly?: boolean;
  onOrganize?: () => Promise<void>;
  isOrganizing?: boolean;
  structuredContent?: string | null;
  feedback?: Feedback | string | null;
}

const snippetSchema = z.object({
  content: z.string().min(1, "내용을 입력해주세요."),
});

type SnippetFormValues = z.infer<typeof snippetSchema>;
type TabType = "write" | "preview" | "ai";

const SCORE_LABELS: Record<string, string> = {
  record_completeness: "기록 충실도",
  learning_signal_detection: "배움 포착",
  cause_effect_connection: "인과 연결",
  action_translation: "행동 전환",
  learning_attitude_consistency: "태도 일관성",
};

export default function SnippetForm({
  kind,
  initialContent = "",
  onSave,
  readOnly = false,
  onOrganize,
  isOrganizing = false,
  structuredContent,
  feedback: rawFeedback,
}: SnippetFormProps) {
  const [activeTab, setActiveTab] = useState<TabType>(
    readOnly ? "preview" : "write"
  );

  const feedback = React.useMemo(() => {
    if (!rawFeedback) return null;
    if (typeof rawFeedback === "string") {
      try {
        return JSON.parse(rawFeedback) as Feedback;
      } catch (e) {
        console.error("Failed to parse feedback JSON", e);
        return null;
      }
    }
    return rawFeedback;
  }, [rawFeedback]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  React.useEffect(() => {
    if (readOnly) {
      setActiveTab("preview");
    }
  }, [readOnly]);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<SnippetFormValues>({
    resolver: zodResolver(snippetSchema),
    defaultValues: {
      content: initialContent,
    },
  });

  React.useEffect(() => {
    reset({ content: initialContent });
  }, [initialContent, reset]);

  const currentContent = watch("content");

  const onSubmit = async (data: SnippetFormValues) => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      if (onSave) {
        await onSave(data.content);
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 405) {
        setSubmitError("작성 가능한 시간이 아닙니다. (06:00 ~ 23:59)");
      } else {
        console.error("Failed to save snippet:", error);
        setSubmitError("저장에 실패했습니다. 잠시 후 다시 시도해주세요.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const tabClasses = (tab: TabType) =>
    `px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
      activeTab === tab
        ? "bg-white border border-slate-200 text-rose-600 shadow-sm"
        : "bg-slate-100 text-slate-600 hover:text-slate-800 hover:bg-slate-200"
    }`;

  const handleOrganizeClick = async () => {
    if (!onOrganize) return;

    // Always save before organizing to ensure the backend has the latest content
    if (onSave) {
      setIsSubmitting(true);
      try {
        await onSave(currentContent);
      } catch (error) {
        console.error("Failed to save before organizing:", error);
        // If save fails, we might want to stop here or warn the user.
        // For now, let's stop to avoid analyzing stale/unsaved data.
        setIsSubmitting(false);
        setSubmitError("저장에 실패하여 AI 분석을 진행할 수 없습니다.");
        return;
      } finally {
        setIsSubmitting(false);
      }
    }

    // Now trigger organize
    await onOrganize();
    setActiveTab("ai");
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="flex gap-1 border-b border-slate-200 mb-6 pb-2">
        {!readOnly && (
          <button
            type="button"
            className={tabClasses("write")}
            onClick={() => setActiveTab("write")}
          >
            작성
          </button>
        )}
        <button
          type="button"
          className={tabClasses("preview")}
          onClick={() => setActiveTab("preview")}
        >
          미리보기
        </button>
        {(structuredContent || onOrganize) && (
          <button
            type="button"
            className={tabClasses("ai")}
            onClick={() => setActiveTab("ai")}
          >
            AI 분석
          </button>
        )}
      </div>

      {activeTab === "write" && !readOnly && (
        <div className="flex flex-col gap-2">
          <textarea
            id="snippet-content"
            {...register("content")}
            style={{ minHeight: "450px" }}
            className={`w-full h-[450px] px-4 py-3 bg-white border rounded-md transition-colors duration-150 outline-none text-slate-800 placeholder:text-slate-400 font-mono text-sm resize-y
              ${
                errors.content
                  ? "border-rose-600 focus:border-rose-600 focus:ring-4 focus:ring-rose-100"
                  : "border-input focus:border-rose-500 focus-visible:ring-rose-100 focus-visible:ring-2"
              }
            `}
            placeholder="마크다운 형식을 사용하여 내용을 입력하세요…"
            aria-invalid={!!errors.content}
            aria-describedby={errors.content ? "content-error" : undefined}
          />
          {errors.content && (
            <p id="content-error" className="mt-1 text-sm text-rose-600">
              {errors.content.message}
            </p>
          )}
        </div>
      )}

      {activeTab === "preview" && (
        <div
          className="w-full h-[450px] bg-white border border-slate-200 rounded-md overflow-hidden isolate flex-none [clip-path:inset(0_round_theme(borderRadius.md))]"
          style={{ height: "450px" }}
        >
          <div className="w-full h-full p-4 overflow-y-auto rounded-[inherit] bg-inherit [scrollbar-gutter:stable]">
            {currentContent ? (
              <div className="prose prose-slate max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                >
                  {currentContent}
                </ReactMarkdown>
              </div>
            ) : (
              <p className="text-slate-400 italic">미리볼 내용이 없습니다.</p>
            )}
          </div>
        </div>
      )}

      {activeTab === "ai" && (
        <div
          className="w-full h-[450px] bg-slate-50 border border-slate-200 rounded-md overflow-hidden isolate flex-none [clip-path:inset(0_round_theme(borderRadius.md))]"
          style={{ height: "450px" }}
        >
          <div className="w-full h-full p-4 overflow-y-auto rounded-[inherit] bg-inherit [scrollbar-gutter:stable]">
            {feedback ? (
              <div className="space-y-6 pb-6">
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

                {structuredContent && (
                  <div className="pt-6 mt-6 border-t border-slate-200 space-y-8">
                    {structuredContent && (
                      <div>
                        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                          <Sparkles className="w-5 h-5 text-slate-500" />
                          AI 정리
                          {!readOnly && (
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="ml-auto"
                              onClick={() => {
                                reset({ content: structuredContent || "" });
                                setActiveTab("write");
                              }}
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
                    )}
                  </div>
                )}
              </div>
            ) : structuredContent ? (
              <div className="prose prose-slate max-w-none p-2">
                {structuredContent && (
                  <>
                    <h3 className="text-lg font-semibold text-slate-800 mb-2">
                      AI 요약
                    </h3>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                    >
                      {structuredContent}
                    </ReactMarkdown>
                  </>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4">
                <p>아직 AI 분석 결과가 없습니다.</p>
                {!readOnly && onOrganize && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleOrganizeClick}
                    disabled={isOrganizing || isSubmitting}
                  >
                    {isOrganizing || isSubmitting ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : null}
                    지금 AI로 분석하기
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {submitError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{submitError}</AlertDescription>
        </Alert>
      )}

      {!readOnly && (
        <div className="flex items-center justify-between pt-6 mt-6 border-t border-slate-200">
          <div></div>
          <div className="flex gap-2">
            {onOrganize && (
              <Button
                type="button"
                variant="outline"
                onClick={handleOrganizeClick}
                disabled={isSubmitting || isOrganizing}
              >
                {(isOrganizing || isSubmitting) && activeTab === 'ai' && (
                   <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                AI 분석
              </Button>
            )}
            <Button
              type="submit"
              variant="default"
              disabled={isSubmitting || isOrganizing}
            >
              {isSubmitting && activeTab === 'write' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              저장하기
            </Button>
          </div>
        </div>
      )}
    </form>
  );
}
