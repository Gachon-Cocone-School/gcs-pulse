"use client";

import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import {
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/api";
import { toast } from "sonner";
import { SnippetAnalysisReport, Feedback } from "./SnippetAnalysisReport";

interface SnippetFormProps {
  kind: "daily" | "weekly";
  initialContent?: string;
  onSave?: (content: string) => Promise<void>;
  readOnly?: boolean;
  onOrganize?: () => Promise<string | null | undefined>;
  isOrganizing?: boolean;
  structuredContent?: string | null;
  feedback?: Feedback | string | null;
}

const snippetSchema = z.object({
  content: z.string().min(1, "내용을 입력해주세요."),
});

type SnippetFormValues = z.infer<typeof snippetSchema>;

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
  // State
  const [showPreview, setShowPreview] = useState(false);
  const originalContentRef = React.useRef<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Parse feedback
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

  // Initialize isAnalyzed based on feedback presence (optional, but good for revisiting)
  const isPreviewMode = readOnly || showPreview;
  const isAnalyzed = Boolean(feedback) || Boolean(structuredContent);
  const activeTab = isPreviewMode ? "preview" : "editor";

  // Form setup
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

  // Handle external content updates
  useEffect(() => {
    // Only reset if the form is pristine or if we want to force update
    // But for now, let's respect the initialContent prop if it changes
    // and we haven't touched it?
    // Actually, controlled behavior is safer for "initialContent".
    // We'll use reset to update it, but we need to be careful not to overwrite user work if they are typing.
    // However, usually initialContent only changes on load or save.
    reset({ content: initialContent });
  }, [initialContent, reset]);

  const currentContent = watch("content");

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

    const contentToSave = getValues("content");
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      if (onSave) {
        await onSave(contentToSave);
      }

      originalContentRef.current = contentToSave;

      const organizedContent = await onOrganize();
      const nextContent = organizedContent ?? structuredContent;

      if (nextContent) {
        setValue("content", nextContent);
        toast("✨ AI가 내용을 다듬었습니다.", {
          action: {
            label: "원래대로 되돌리기",
            onClick: () => {
              if (originalContentRef.current) {
                setValue("content", originalContentRef.current);
              }
            },
          },
        });
      }
    } catch (error) {
      console.error("Organize failed", error);
      setSubmitError("AI 분석에 실패했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
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
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                    >
                      {currentContent}
                    </ReactMarkdown>
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
                  disabled={readOnly || isOrganizing}
                  className={cn(
                    "h-[450px] min-h-[450px] resize-y rounded-lg border-border px-4 py-3 font-mono text-sm",
                    errors.content && "border-destructive focus-visible:border-destructive",
                  )}
                  placeholder="마크다운 형식을 사용하여 내용을 입력하세요…"
                />

                {!readOnly && onOrganize && (
                  <div className="absolute bottom-4 right-4 z-10">
                    <Button
                      type="button"
                      size="icon"
                      className={cn(
                        "h-12 w-12 rounded-full shadow-sm transition-all",
                        isOrganizing
                          ? "bg-muted text-muted-foreground"
                          : "bg-gradient-to-r from-indigo-500 to-rose-500 text-white hover:scale-105",
                      )}
                      onClick={handleOrganizeClick}
                      disabled={isOrganizing || isSubmitting}
                      title="AI로 다듬기"
                    >
                      {isOrganizing ? (
                        <Loader2 className="h-6 w-6 animate-spin" />
                      ) : (
                        <Sparkles className="h-6 w-6" />
                      )}
                    </Button>
                  </div>
                )}
              </div>
            </TabsContent>

            {errors.content && (
              <p className="mt-2 text-sm text-destructive">{errors.content.message}</p>
            )}
          </div>
        </Tabs>
      </div>

      {/* AI Analysis Report Section */}
      {isAnalyzed && feedback && (
        <SnippetAnalysisReport
          feedback={feedback}
        />
      )}

      {/* Error Message */}
      {submitError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{submitError}</AlertDescription>
        </Alert>
      )}

      {/* Actions */}
      {!readOnly && (
        <div className="flex items-center justify-end border-t border-border pt-4">
          <Button
            type="submit"
            variant="default"
            disabled={isSubmitting || isOrganizing}
            className="w-full sm:w-auto"
          >
            {isSubmitting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            저장하기
          </Button>
        </div>
      )}
    </form>
  );
}
