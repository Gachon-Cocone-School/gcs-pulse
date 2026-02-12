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
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/api";
import { toast } from "sonner";
import { SnippetAnalysisReport, Feedback } from "./SnippetAnalysisReport";

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
  const [showPreview, setShowPreview] = useState(readOnly);
  const [isAnalyzed, setIsAnalyzed] = useState(false);
  const [originalContent, setOriginalContent] = useState<string | null>(null);
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
  useEffect(() => {
    if (feedback) {
      setIsAnalyzed(true);
    }
  }, [feedback]);

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

    // 1. Save current content first
    const contentToSave = getValues("content");
    setIsSubmitting(true);
    try {
      if (onSave) {
        await onSave(contentToSave);
      }
    } catch (error) {
      console.error("Failed to save before organizing:", error);
      setIsSubmitting(false);
      setSubmitError("저장에 실패하여 AI 분석을 진행할 수 없습니다.");
      return;
    }

    // 2. Backup original content
    setOriginalContent(contentToSave);

    // 3. Trigger organize
    // onOrganize is expected to update the parent state, which will update structuredContent prop
    try {
      await onOrganize();
      // Note: After this await, we expect structuredContent to be updated via props in a re-render.
      // However, we can't access the *new* prop here immediately.
      // We will rely on a useEffect to detect the completion and apply the change.
      // Or, if we trust the API flow, we can just wait for the prop update.
    } catch (e) {
      console.error("Organize failed", e);
      setIsSubmitting(false);
    }
  };

  // Watch for changes in structuredContent to apply auto-replacement
  // We use a ref or flag to know if we are waiting for an update?
  // Actually, isOrganizing prop tells us when it starts and ends.

  // Let's track previous isOrganizing state
  const prevIsOrganizingRef = React.useRef(isOrganizing);

  useEffect(() => {
    // If we just finished organizing (true -> false)
    if (prevIsOrganizingRef.current && !isOrganizing) {
      // And we have structured content and we are not submitting (finished)
      if (structuredContent) {
        // Apply the AI content
        setValue("content", structuredContent);
        setIsAnalyzed(true);
        setIsSubmitting(false); // Make sure to unset this if it was set in handleOrganizeClick

        // Show Toast
        toast("✨ AI가 내용을 다듬었습니다.", {
          action: {
            label: "원래대로 되돌리기",
            onClick: () => {
               setOriginalContent((prev) => {
                 if (prev) {
                   setValue("content", prev);
                   // Optionally revert structuredContent display?
                 }
                 return prev;
               });
            },
          },
        });
      }
    }
    prevIsOrganizingRef.current = isOrganizing;
  }, [isOrganizing, structuredContent, setValue]);


  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="relative">
        {/* Toolbar / Header */}
        <div className="flex items-center justify-between mb-2">
           <div className="text-sm text-slate-500 font-medium">
             {readOnly ? "View Mode" : "Write Mode"}
           </div>
           <div className="flex items-center gap-2">
             <Button
               type="button"
               variant="ghost"
               size="sm"
               onClick={() => setShowPreview(!showPreview)}
               className="text-slate-500 hover:text-slate-800"
               title={showPreview ? "편집하기" : "미리보기"}
             >
               {showPreview ? (
                 <>
                   <EyeOff className="w-4 h-4 mr-1.5" />
                   편집
                 </>
               ) : (
                 <>
                   <Eye className="w-4 h-4 mr-1.5" />
                   미리보기
                 </>
               )}
             </Button>
           </div>
        </div>

        {/* Editor Area */}
        <div className="relative group">
          {showPreview ? (
             <div
               className="w-full min-h-[450px] bg-white border border-slate-200 rounded-md p-4 overflow-y-auto prose prose-slate max-w-none"
             >
               {currentContent ? (
                 <ReactMarkdown
                   remarkPlugins={[remarkGfm]}
                   rehypePlugins={[rehypeRaw]}
                 >
                   {currentContent}
                 </ReactMarkdown>
               ) : (
                 <p className="text-slate-400 italic">내용이 없습니다.</p>
               )}
             </div>
          ) : (
            <>
              <textarea
                id="snippet-content"
                {...register("content")}
                disabled={readOnly || isOrganizing}
                style={{ minHeight: "450px" }}
                className={`w-full h-[450px] px-4 py-3 bg-white border rounded-md transition-colors duration-150 outline-none text-slate-800 placeholder:text-slate-400 font-mono text-sm resize-y
                  ${
                    errors.content
                      ? "border-rose-600 focus:border-rose-600 focus:ring-4 focus:ring-rose-100"
                      : "border-slate-200 focus:border-rose-500 focus-visible:ring-rose-100 focus-visible:ring-2"
                  }
                `}
                placeholder="마크다운 형식을 사용하여 내용을 입력하세요…"
              />

              {/* Floating AI Button */}
              {!readOnly && onOrganize && (
                <div className="absolute bottom-4 right-4 z-10">
                   <Button
                     type="button"
                     size="icon"
                     className={cn(
                       "h-12 w-12 rounded-full shadow-lg transition-all duration-300",
                       isOrganizing ? "bg-slate-100" : "bg-gradient-to-r from-indigo-500 to-rose-500 hover:scale-105 hover:shadow-rose-200/50"
                     )}
                     onClick={handleOrganizeClick}
                     disabled={isOrganizing || isSubmitting}
                     title="AI로 다듬기"
                   >
                     {isOrganizing ? (
                       <Loader2 className="h-6 w-6 text-slate-400 animate-spin" />
                     ) : (
                       <Sparkles className="h-6 w-6 text-white" />
                     )}
                   </Button>
                </div>
              )}
            </>
          )}

          {errors.content && (
            <p className="mt-1 text-sm text-rose-600">
              {errors.content.message}
            </p>
          )}
        </div>
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
        <div className="flex items-center justify-end pt-4 border-t border-slate-200">
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
