"use client";

import React, { useEffect, useReducer } from "react";
import dynamic from "next/dynamic";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { ApiError } from '@/lib/api';
import { toast } from 'sonner';
import { SnippetActionBar } from './SnippetActionBar';
import { OrganizeResultDialog } from './OrganizeResultDialog';
import { parseFeedback } from './snippet-form.helpers';
import { formUiReducer, initialFormUiState } from './snippet-form.state';
import type { SnippetFormProps } from './snippet-form.types';

const SnippetAnalysisReport = dynamic(
  () => import("./SnippetAnalysisReport").then((mod) => mod.SnippetAnalysisReport),
  {
    loading: () => <p className="text-sm text-slate-500">AI 분석을 불러오는 중입니다...</p>,
  },
);

const snippetSchema = z.object({
  content: z.string().min(1, "내용을 입력해주세요."),
});

type SnippetFormValues = z.infer<typeof snippetSchema>;

const MarkdownRenderer = dynamic(() => import('./MarkdownRenderer'), {
  loading: () => <p className="italic text-muted-foreground">미리보기를 불러오는 중입니다...</p>,
});

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
  const [uiState, dispatch] = useReducer(formUiReducer, initialFormUiState);

  const persistedFeedback = React.useMemo(() => parseFeedback(rawFeedback), [rawFeedback]);
  const previewFeedback = React.useMemo(
    () => parseFeedback(uiState.previewFeedbackRaw),
    [uiState.previewFeedbackRaw],
  );
  const feedback = previewFeedback ?? persistedFeedback;

  const isPreviewMode = readOnly || uiState.showPreview;
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
    dispatch({ type: "RESET_FOR_INITIAL_CONTENT" });
  }, [initialContent, reset]);

  const currentContent = watch("content");
  const hasContent = currentContent.trim().length > 0;
  const hasOrganizedDraft = uiState.organizedDraftContent.trim().length > 0;
  const hasOrganizedDraftFeedback = Boolean(uiState.organizedDraftFeedback);
  const isBusy =
    uiState.isSubmitting || isOrganizing || isGeneratingFeedback || uiState.isApplying;

  const discardOrganizedDraft = () => {
    dispatch({ type: "CLOSE_ORGANIZE_DRAFT" });
  };

  const onSubmit = async (data: SnippetFormValues) => {
    if (readOnly) {
      toast("이 스니펫은 더 이상 편집할 수 없습니다.");
      return;
    }

    if (data.content === initialContent) {
      dispatch({ type: "SET_SUBMIT_ERROR", payload: null });
      toast("변경된 내용이 없습니다.");
      return;
    }

    dispatch({ type: "SET_IS_SUBMITTING", payload: true });
    dispatch({ type: "SET_SUBMIT_ERROR", payload: null });

    try {
      if (onSave) {
        await onSave(data.content);
      }
      dispatch({ type: "SET_PREVIEW_FEEDBACK", payload: null });
    } catch (error) {
      if (error instanceof ApiError && error.status === 405) {
        dispatch({ type: "SET_SUBMIT_ERROR", payload: "작성 가능한 시간이 아닙니다. (06:00 ~ 23:59)" });
      } else if (error instanceof ApiError && error.status === 403) {
        dispatch({ type: "SET_SUBMIT_ERROR", payload: "이 스니펫은 더 이상 편집할 수 없습니다." });
        toast("이 스니펫은 더 이상 편집할 수 없습니다.");
      } else {
        console.error("Failed to save snippet:", error);
        dispatch({ type: "SET_SUBMIT_ERROR", payload: "저장에 실패했습니다. 잠시 후 다시 시도해주세요." });
      }
    } finally {
      dispatch({ type: "SET_IS_SUBMITTING", payload: false });
    }
  };

  const handleOrganizeClick = async () => {
    if (!onOrganize) return;

    const sourceContent = getValues("content");
    dispatch({ type: "SET_SUBMIT_ERROR", payload: null });

    try {
      const result = await onOrganize(sourceContent);
      if (!result) {
        dispatch({ type: "SET_SUBMIT_ERROR", payload: "AI 정리에 실패했습니다. 잠시 후 다시 시도해주세요." });
        return;
      }

      const organized =
        result && typeof result.organizedContent === "string"
          ? result.organizedContent
          : "";

      dispatch({
        type: "OPEN_ORGANIZE_DRAFT",
        payload: {
          content: organized,
          feedback: result.feedback ?? null,
        },
      });

      if (organized.trim()) {
        toast("AI 정리 결과를 확인해 주세요.");
      } else {
        toast("AI 정리 결과가 비어 있습니다.");
      }
    } catch (error) {
      console.error("Organize failed", error);
      dispatch({ type: "SET_SUBMIT_ERROR", payload: "AI 정리에 실패했습니다. 잠시 후 다시 시도해주세요." });
    }
  };

  const handleGenerateFeedbackClick = async () => {
    if (!onGenerateFeedback) return;

    const sourceContent = getValues("content");
    const organizedContent = hasOrganizedDraft ? uiState.organizedDraftContent : undefined;

    if (sourceContent === initialContent) {
      dispatch({ type: "SET_SUBMIT_ERROR", payload: null });
      toast("변경된 내용이 없습니다.");
      return;
    }

    dispatch({ type: "SET_SUBMIT_ERROR", payload: null });

    try {
      const nextFeedback = await onGenerateFeedback(sourceContent, organizedContent);
      dispatch({ type: "SET_PREVIEW_FEEDBACK", payload: nextFeedback ?? null });

      if (nextFeedback) {
        toast("AI 피드백을 갱신했습니다.");
      } else {
        toast("AI 피드백 결과가 비어 있습니다.");
      }
    } catch (error) {
      console.error("Feedback generation failed", error);
      dispatch({ type: "SET_SUBMIT_ERROR", payload: "AI 피드백 생성에 실패했습니다. 잠시 후 다시 시도해주세요." });
    }
  };

  const handleApplyOrganizeDraft = async () => {
    if (!onSave || !hasOrganizedDraft || readOnly) return;

    const organizedDraftContent = uiState.organizedDraftContent;

    dispatch({ type: "SET_IS_APPLYING", payload: true });
    dispatch({ type: "SET_SUBMIT_ERROR", payload: null });

    try {
      await onSave(organizedDraftContent);
      setValue("content", organizedDraftContent);
      dispatch({ type: "SET_PREVIEW_FEEDBACK", payload: null });
      discardOrganizedDraft();
      toast("정리 내용을 적용해 저장했습니다.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 405) {
        dispatch({ type: "SET_SUBMIT_ERROR", payload: "작성 가능한 시간이 아닙니다. (06:00 ~ 23:59)" });
      } else if (error instanceof ApiError && error.status === 403) {
        dispatch({ type: "SET_SUBMIT_ERROR", payload: "이 스니펫은 더 이상 편집할 수 없습니다." });
        toast("이 스니펫은 더 이상 편집할 수 없습니다.");
      } else {
        console.error("Failed to apply organized draft:", error);
        dispatch({ type: "SET_SUBMIT_ERROR", payload: "적용하기에 실패했습니다. 잠시 후 다시 시도해주세요." });
      }
    } finally {
      dispatch({ type: "SET_IS_APPLYING", payload: false });
    }
  };

  const handleCancelOrganizeDraft = () => {
    if (uiState.isApplying) return;
    discardOrganizedDraft();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <SnippetActionBar
        readOnly={readOnly}
        isBusy={isBusy}
        hasContent={hasContent}
        isOrganizing={isOrganizing}
        isGeneratingFeedback={isGeneratingFeedback}
        isSubmitting={uiState.isSubmitting}
        canOrganize={Boolean(onOrganize)}
        canGenerateFeedback={Boolean(onGenerateFeedback)}
        onOrganizeClick={handleOrganizeClick}
        onGenerateFeedbackClick={handleGenerateFeedbackClick}
      />

      <div className="relative">
        <Tabs value={activeTab} className="gap-3">
          {!readOnly && (
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger
                  value="editor"
                  onClick={() => dispatch({ type: "SET_SHOW_PREVIEW", payload: false })}
                >
                  <EyeOff className="h-4 w-4" />
                  편집
                </TabsTrigger>
                <TabsTrigger
                  value="preview"
                  onClick={() => dispatch({ type: "SET_SHOW_PREVIEW", payload: true })}
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

      {uiState.submitError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{uiState.submitError}</AlertDescription>
        </Alert>
      )}

      <OrganizeResultDialog
        open={uiState.isOrganizeModalOpen}
        isApplying={uiState.isApplying}
        readOnly={readOnly}
        isBusy={isBusy}
        organizedDraftContent={uiState.organizedDraftContent}
        hasOrganizedDraftFeedback={hasOrganizedDraftFeedback}
        onCancel={handleCancelOrganizeDraft}
        onApply={handleApplyOrganizeDraft}
      />
    </form>
  );
}
