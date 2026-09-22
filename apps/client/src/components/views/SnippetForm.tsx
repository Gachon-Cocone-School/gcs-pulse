"use client";

import React, { useCallback, useEffect, useReducer, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { AlertCircle, Eye, EyeOff } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { ApiError } from '@/lib/api';
import { toast } from 'sonner';
import { SnippetActionBar } from './SnippetActionBar';
import { OrganizeResultDialog } from './OrganizeResultDialog';
import SnippetPreview from './SnippetPreview';
import { parseFeedback } from './snippet-form.helpers';
import { formUiReducer, initialFormUiState } from './snippet-form.state';
import type { SnippetFormProps } from './snippet-form.types';
import { useSnippetFormAiActions } from './useSnippetFormAiActions';

const SnippetAnalysisReport = dynamic(
  () => import("./SnippetAnalysisReport").then((mod) => mod.SnippetAnalysisReport),
  {
    loading: () => <p className="text-sm text-muted-foreground">AI 분석을 불러오는 중입니다...</p>,
  },
);

const snippetSchema = z.object({
  content: z.string().min(1, "내용을 입력해주세요."),
});

type SnippetFormValues = z.infer<typeof snippetSchema>;


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
  const analysisSectionRef = useRef<HTMLDivElement | null>(null);
  const [autoSaveState, setAutoSaveState] = useState<'idle' | 'pending' | 'saving' | 'saved' | 'error'>('idle');
  const latestContentRef = useRef(initialContent);
  const savedContentRef = useRef(initialContent);
  const saveInFlightRef = useRef(false);
  const onSaveRef = useRef(onSave);

  useEffect(() => {
    onSaveRef.current = onSave;
  }, [onSave]);

  const persistedFeedback = React.useMemo(() => parseFeedback(rawFeedback), [rawFeedback]);
  const previewFeedback = React.useMemo(
    () => parseFeedback(uiState.previewFeedbackRaw, { silent: true }),
    [uiState.previewFeedbackRaw],
  );
  const feedback = previewFeedback ?? persistedFeedback;

  const isPreviewMode = readOnly || uiState.showPreview;
  const hasFeedbackInProgress = isGeneratingFeedback;
  const analysisFeedback = hasFeedbackInProgress ? null : feedback;
  const isAnalyzed = Boolean(analysisFeedback) || hasFeedbackInProgress;
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
    latestContentRef.current = initialContent;
    savedContentRef.current = initialContent;
    setAutoSaveState('idle');
    dispatch({ type: "RESET_FOR_INITIAL_CONTENT" });
  }, [initialContent, reset]);

  const prevHasFeedbackInProgressRef = useRef(hasFeedbackInProgress);

  useEffect(() => {
    const wasFeedbackInProgress = prevHasFeedbackInProgressRef.current;

    if (!wasFeedbackInProgress && hasFeedbackInProgress) {
      analysisSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (wasFeedbackInProgress && !hasFeedbackInProgress && analysisFeedback) {
      analysisSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }

    prevHasFeedbackInProgressRef.current = hasFeedbackInProgress;
  }, [hasFeedbackInProgress, analysisFeedback]);

  const currentContent = watch("content");
  latestContentRef.current = currentContent;
  const hasContent = currentContent.trim().length > 0;
  const hasOrganizedDraft = uiState.organizedDraftContent.trim().length > 0;
  const isBusy =
    uiState.isSubmitting || isOrganizing || isGeneratingFeedback || uiState.isApplying;

  const saveAutomatically = useCallback(async () => {
    const content = latestContentRef.current;
    if (
      readOnly ||
      !onSaveRef.current ||
      !content.trim() ||
      content === savedContentRef.current ||
      saveInFlightRef.current
    ) {
      return;
    }

    saveInFlightRef.current = true;
    setAutoSaveState('saving');
    try {
      await onSaveRef.current(content);
      savedContentRef.current = content;
      setAutoSaveState('saved');
    } catch (error) {
      console.error('Failed to auto-save snippet:', error);
      setAutoSaveState('error');
    } finally {
      saveInFlightRef.current = false;
    }
  }, [readOnly]);

  useEffect(() => {
    if (
      readOnly ||
      !onSaveRef.current ||
      !currentContent.trim() ||
      currentContent === savedContentRef.current
    ) {
      return;
    }
    setAutoSaveState('pending');
    const timer = window.setTimeout(() => void saveAutomatically(), 10_000);
    return () => window.clearTimeout(timer);
  }, [currentContent, readOnly, saveAutomatically]);

  useEffect(() => {
    if (readOnly || !onSaveRef.current) return;
    const interval = window.setInterval(() => void saveAutomatically(), 60_000);
    return () => window.clearInterval(interval);
  }, [readOnly, saveAutomatically]);

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

  const {
    handleOrganizeClick,
    handleGenerateFeedbackClick,
    handleCancelFeedbackStreaming,
    handleApplyOrganizeDraft,
    handleCancelOrganizeDraft,
  } = useSnippetFormAiActions({
    readOnly,
    onSave,
    onOrganize,
    onGenerateFeedback,
    hasOrganizedDraft,
    organizedDraftContent: uiState.organizedDraftContent,
    isApplying: uiState.isApplying,
    getValues,
    setValue,
    dispatch,
    discardOrganizedDraft,
  });

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

      {!readOnly && autoSaveState !== 'idle' && (
        <p className={cn('text-xs text-muted-foreground', autoSaveState === 'error' && 'text-destructive')} role="status">
          {autoSaveState === 'pending' && '자동 저장 대기 중'}
          {autoSaveState === 'saving' && '자동 저장 중…'}
          {autoSaveState === 'saved' && '자동 저장됨'}
          {autoSaveState === 'error' && '자동 저장에 실패했습니다. 저장 버튼으로 다시 시도해주세요.'}
        </p>
      )}

      <div className="relative">
        <Tabs value={activeTab} className="gap-3">
          {!readOnly && (
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger
                  value="editor"
                  className="data-[state=active]:bg-[var(--sys-current-bg)] data-[state=active]:text-[var(--sys-current-fg)] data-[state=active]:border-[var(--sys-current-border)]"
                  onClick={() => dispatch({ type: "SET_SHOW_PREVIEW", payload: false })}
                >
                  <EyeOff className="h-4 w-4" />
                  편집
                </TabsTrigger>
                <TabsTrigger
                  value="preview"
                  className="data-[state=active]:bg-[var(--sys-current-bg)] data-[state=active]:text-[var(--sys-current-fg)] data-[state=active]:border-[var(--sys-current-border)]"
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
              {currentContent ? (
                <SnippetPreview content={currentContent} />
              ) : (
                <Card className="min-h-[450px] rounded-lg border-[var(--sys-current-border)] p-4">
                  <p className="italic text-muted-foreground">내용이 없습니다.</p>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="editor" className={cn(activeTab === "editor" ? "block" : "hidden")}>
              <div className="relative">
                <Textarea
                  id="snippet-content"
                  {...register("content")}
                  disabled={readOnly || isBusy}
                  className={cn(
                    "h-[450px] min-h-[450px] resize-y rounded-lg border-[var(--sys-current-border)] px-4 py-3 text-sm",
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

      {isAnalyzed && (
        <div ref={analysisSectionRef}>
          <SnippetAnalysisReport
            feedback={analysisFeedback}
            isStreaming={hasFeedbackInProgress}
            onCancelStreaming={handleCancelFeedbackStreaming}
          />
        </div>
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
        isOrganizing={isOrganizing}
        readOnly={readOnly}
        isBusy={isBusy}
        organizedDraftContent={uiState.organizedDraftContent}
        onCancel={handleCancelOrganizeDraft}
        onApply={handleApplyOrganizeDraft}
      />
    </form>
  );
}
