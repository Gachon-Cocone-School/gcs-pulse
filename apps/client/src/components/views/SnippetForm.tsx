"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  Sparkles,
  MessageCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/api";
import { toast } from "sonner";
import type { Feedback } from "./SnippetAnalysisReport";

const SnippetAnalysisReport = dynamic(
  () => import("./SnippetAnalysisReport").then((mod) => mod.SnippetAnalysisReport),
  {
    loading: () => <p className="text-sm text-slate-500">AI 분석을 불러오는 중입니다...</p>,
  },
);

interface OrganizeResult {
  organizedContent?: string | null;
  feedback?: Feedback | string | null;
}

interface SnippetFormProps {
  initialContent?: string;
  onSave?: (content: string) => Promise<void>;
  readOnly?: boolean;
  onOrganize?: (content: string) => Promise<OrganizeResult | null | undefined>;
  onGenerateFeedback?: (content: string, organizedContent?: string) => Promise<Feedback | string | null>;
  isOrganizing?: boolean;
  isGeneratingFeedback?: boolean;
  feedback?: Feedback | string | null;
}

const snippetSchema = z.object({
  content: z.string().min(1, "내용을 입력해주세요."),
});

type SnippetFormValues = z.infer<typeof snippetSchema>;

const MarkdownRenderer = dynamic(() => import("./MarkdownRenderer"), {
  loading: () => <p className="italic text-muted-foreground">미리보기를 불러오는 중입니다...</p>,
});

function parseFeedback(raw: Feedback | string | null | undefined): Feedback | null {
  if (!raw) return null;
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw) as Feedback;
    } catch (e) {
      console.error("Failed to parse feedback JSON", e);
      return null;
    }
  }
  return raw;
}

export default function SnippetForm({
  initialContent = "",
  onSave,
  readOnly = false,
  onOrganize,
  onGenerateFeedback,
  isOrganizing = false,
  isGeneratingFeedback = false,
  feedback: rawFeedback,
}: SnippetFormProps) {
  const [showPreview, setShowPreview] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [previewFeedbackRaw, setPreviewFeedbackRaw] = useState<Feedback | string | null>(null);
  const [isOrganizeModalOpen, setIsOrganizeModalOpen] = useState(false);
  const [organizedDraftContent, setOrganizedDraftContent] = useState("");
  const [organizedDraftFeedback, setOrganizedDraftFeedback] = useState<Feedback | string | null>(null);

  const persistedFeedback = React.useMemo(() => parseFeedback(rawFeedback), [rawFeedback]);
  const previewFeedback = React.useMemo(() => parseFeedback(previewFeedbackRaw), [previewFeedbackRaw]);
  const feedback = previewFeedback ?? persistedFeedback;

  const isPreviewMode = readOnly || showPreview;
  const isAnalyzed = Boolean(feedback);
  const activeTab = isPreviewMode ? "preview" : "editor";

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    getValues,
    formState: { errors },
  } = useForm<SnippetFormValues>({
    resolver: zodResolver(snippetSchema),
    defaultValues: {
      content: initialContent,
    },
  });

  useEffect(() => {
    reset({ content: initialContent });
    setPreviewFeedbackRaw(null);
    setIsOrganizeModalOpen(false);
    setOrganizedDraftContent("");
    setOrganizedDraftFeedback(null);
  }, [initialContent, reset]);

  const currentContent = watch("content");
  const hasContent = currentContent.trim().length > 0;
  const hasOrganizedDraft = organizedDraftContent.trim().length > 0;
  const hasOrganizedDraftFeedback = Boolean(organizedDraftFeedback);
  const isBusy = isSubmitting || isOrganizing || isGeneratingFeedback || isApplying;

  const discardOrganizedDraft = () => {
    setIsOrganizeModalOpen(false);
    setOrganizedDraftContent("");
    setOrganizedDraftFeedback(null);
  };

  const onSubmit = async (data: SnippetFormValues) => {
    if (readOnly) {
      toast("이 스니펫은 더 이상 편집할 수 없습니다.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      if (onSave) {
        await onSave(data.content);
      }
      setPreviewFeedbackRaw(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 405) {
        setSubmitError("작성 가능한 시간이 아닙니다. (06:00 ~ 23:59)");
      } else if (error instanceof ApiError && error.status === 403) {
        setSubmitError("이 스니펫은 더 이상 편집할 수 없습니다.");
        toast("이 스니펫은 더 이상 편집할 수 없습니다.");
      } else {
        console.error("Failed to save snippet:", error);
        setSubmitError("저장에 실패했습니다. 잠시 후 다시 시도해주세요.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOrganizeClick = async () => {
    if (!onOrganize) return;

    const sourceContent = getValues("content");
    setSubmitError(null);

    try {
      const result = await onOrganize(sourceContent);
      if (!result) {
        setSubmitError("AI 정리에 실패했습니다. 잠시 후 다시 시도해주세요.");
        return;
      }

      const organized =
        result && typeof result.organizedContent === "string"
          ? result.organizedContent
          : "";

      setOrganizedDraftContent(organized);
      setOrganizedDraftFeedback(result.feedback ?? null);
      setIsOrganizeModalOpen(true);

      if (organized.trim()) {
        toast("AI 정리 결과를 확인해 주세요.");
      } else {
        toast("AI 정리 결과가 비어 있습니다.");
      }
    } catch (error) {
      console.error("Organize failed", error);
      setSubmitError("AI 정리에 실패했습니다. 잠시 후 다시 시도해주세요.");
    }
  };

  const handleGenerateFeedbackClick = async () => {
    if (!onGenerateFeedback) return;

    const sourceContent = getValues("content");
    const organizedContent = hasOrganizedDraft ? organizedDraftContent : undefined;

    setSubmitError(null);
    try {
      const nextFeedback = await onGenerateFeedback(sourceContent, organizedContent);
      setPreviewFeedbackRaw(nextFeedback ?? null);

      if (nextFeedback) {
        toast("AI 피드백을 갱신했습니다.");
      } else {
        toast("AI 피드백 결과가 비어 있습니다.");
      }
    } catch (error) {
      console.error("Feedback generation failed", error);
      setSubmitError("AI 피드백 생성에 실패했습니다. 잠시 후 다시 시도해주세요.");
    }
  };

  const handleApplyOrganizeDraft = async () => {
    if (!onSave || !hasOrganizedDraft || readOnly) return;

    setIsApplying(true);
    setSubmitError(null);

    try {
      await onSave(organizedDraftContent);
      setValue("content", organizedDraftContent);
      setPreviewFeedbackRaw(null);
      discardOrganizedDraft();
      toast("정리 내용을 적용해 저장했습니다.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 405) {
        setSubmitError("작성 가능한 시간이 아닙니다. (06:00 ~ 23:59)");
      } else if (error instanceof ApiError && error.status === 403) {
        setSubmitError("이 스니펫은 더 이상 편집할 수 없습니다.");
        toast("이 스니펫은 더 이상 편집할 수 없습니다.");
      } else {
        console.error("Failed to apply organized draft:", error);
        setSubmitError("적용하기에 실패했습니다. 잠시 후 다시 시도해주세요.");
      }
    } finally {
      setIsApplying(false);
    }
  };

  const handleCancelOrganizeDraft = () => {
    if (isApplying) return;
    discardOrganizedDraft();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {!readOnly && (
        <div className="flex flex-col items-stretch justify-end gap-2 border-b border-border pb-4 sm:flex-row">
          <Button
            type="button"
            variant="outline"
            disabled={readOnly || isBusy || !onOrganize}
            onClick={handleOrganizeClick}
            className="w-full sm:w-auto"
          >
            {isOrganizing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 h-4 w-4" />
            )}
            정리하기
          </Button>

          <Button
            type="button"
            variant="outline"
            disabled={readOnly || isBusy || !hasContent || !onGenerateFeedback}
            onClick={handleGenerateFeedbackClick}
            className="w-full sm:w-auto"
          >
            {isGeneratingFeedback ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <MessageCircle className="mr-2 h-4 w-4" />
            )}
            피드백 받기
          </Button>

          <Button
            type="submit"
            variant="default"
            disabled={readOnly || isBusy || !hasContent}
            className="w-full sm:w-auto"
          >
            {isSubmitting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            저장하기
          </Button>
        </div>
      )}

      <div className="relative">
        <Tabs value={activeTab} className="gap-3">
          {!readOnly && (
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger
                  value="editor"
                  onClick={() => setShowPreview(false)}
                >
                  <EyeOff className="h-4 w-4" />
                  편집
                </TabsTrigger>
                <TabsTrigger
                  value="preview"
                  onClick={() => setShowPreview(true)}
                >
                  <Eye className="h-4 w-4" />
                  미리보기
                </TabsTrigger>
              </TabsList>
            </div>
          )}

          <div className="relative group">
            <TabsContent value="preview" className={cn(activeTab === "preview" ? "block" : "hidden")}>
              <Card className="min-h-[450px] rounded-lg border border-border p-4">
                <div className="prose prose-slate max-w-none overflow-y-auto">
                  {currentContent ? (
                    <MarkdownRenderer
                      content={currentContent}
                      useRemarkGfm
                      useRehypeRaw
                    />
                  ) : (
                    <p className="italic text-muted-foreground">내용이 없습니다.</p>
                  )}
                </div>
              </Card>
            </TabsContent>

            <TabsContent value="editor" className={cn(activeTab === "editor" ? "block" : "hidden")}>
              <div className="relative">
                <Textarea
                  id="snippet-content"
                  {...register("content")}
                  disabled={readOnly || isBusy}
                  className={cn(
                    "h-[450px] min-h-[450px] resize-y rounded-lg border-border px-4 py-3 font-mono text-sm",
                    errors.content && "border-destructive focus-visible:border-destructive",
                  )}
                  placeholder="마크다운 형식을 사용하여 내용을 입력하세요…"
                />
              </div>
            </TabsContent>

            {errors.content && (
              <p className="mt-2 text-sm text-destructive">{errors.content.message}</p>
            )}
          </div>
        </Tabs>
      </div>

      {isAnalyzed && feedback && (
        <SnippetAnalysisReport
          feedback={feedback}
        />
      )}

      {submitError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{submitError}</AlertDescription>
        </Alert>
      )}

      <Dialog
        open={isOrganizeModalOpen}
        onOpenChange={(open) => {
          if (open) {
            setIsOrganizeModalOpen(true);
            return;
          }
          handleCancelOrganizeDraft();
        }}
      >
        <DialogContent className="sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>AI 정리 결과</DialogTitle>
            <DialogDescription>
              정리 결과를 확인한 뒤 적용 여부를 선택하세요. 적용하기 전에는 본문이 바뀌지 않습니다.
            </DialogDescription>
          </DialogHeader>

          <div className="max-h-[60vh] overflow-y-auto rounded-lg border border-border p-4">
            {hasOrganizedDraft ? (
              <div className="prose prose-slate max-w-none">
                <MarkdownRenderer
                  content={organizedDraftContent}
                  useRemarkGfm
                  useRehypeRaw
                />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">AI 정리 결과가 비어 있습니다.</p>
            )}
          </div>

          {hasOrganizedDraftFeedback && (
            <p className="text-xs text-muted-foreground">
              정리 과정에서 분석 데이터가 함께 생성되었습니다. 필요하면 피드백 받기로 최신 리포트를 확인하세요.
            </p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={handleCancelOrganizeDraft}
              disabled={isApplying}
            >
              취소하기
            </Button>
            <Button
              type="button"
              onClick={handleApplyOrganizeDraft}
              disabled={readOnly || isBusy || !hasOrganizedDraft}
            >
              {isApplying ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              적용하기
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </form>
  );
}
