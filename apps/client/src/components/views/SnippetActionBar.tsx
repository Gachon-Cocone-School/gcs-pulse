import React from 'react';
import { Loader2, MessageCircle, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SnippetActionBarProps {
  readOnly: boolean;
  isBusy: boolean;
  hasContent: boolean;
  isOrganizing: boolean;
  isGeneratingFeedback: boolean;
  isSubmitting: boolean;
  canOrganize: boolean;
  canGenerateFeedback: boolean;
  onOrganizeClick: () => void;
  onGenerateFeedbackClick: () => void;
}

export function SnippetActionBar({
  readOnly,
  isBusy,
  hasContent,
  isOrganizing,
  isGeneratingFeedback,
  isSubmitting,
  canOrganize,
  canGenerateFeedback,
  onOrganizeClick,
  onGenerateFeedbackClick,
}: SnippetActionBarProps) {
  if (readOnly) {
    return null;
  }

  return (
    <div className="flex flex-col items-stretch justify-end gap-2 border-b border-border pb-4 sm:flex-row">
      <Button
        type="button"
        variant="outline"
        disabled={readOnly || isBusy || !canOrganize}
        onClick={onOrganizeClick}
        className="w-full sm:w-auto"
      >
        {isOrganizing ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Sparkles className="mr-2 h-4 w-4" />
        )}
        AI 제안
      </Button>

      <Button
        type="button"
        variant="outline"
        disabled={readOnly || isBusy || !hasContent || !canGenerateFeedback}
        onClick={onGenerateFeedbackClick}
        className="w-full sm:w-auto"
      >
        {isGeneratingFeedback ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <MessageCircle className="mr-2 h-4 w-4" />
        )}
        AI 채점
      </Button>

      <Button
        type="submit"
        variant="default"
        disabled={readOnly || isBusy || !hasContent}
        className="w-full sm:w-auto"
      >
        {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
        저장하기
      </Button>
    </div>
  );
}
