import dynamic from 'next/dynamic';
import React from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LoadingDotsText } from '@/components/ui/LoadingDotsText';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const MarkdownRenderer = dynamic(() => import('./MarkdownRenderer'), {
  loading: () => <p className="italic text-muted-foreground">미리보기를 불러오는 중입니다...</p>,
});

interface OrganizeResultDialogProps {
  open: boolean;
  isApplying: boolean;
  isOrganizing: boolean;
  readOnly: boolean;
  isBusy: boolean;
  organizedDraftContent: string;
  onCancel: () => void;
  onApply: () => void;
}

export function OrganizeResultDialog({
  open,
  isApplying,
  isOrganizing,
  readOnly,
  isBusy,
  organizedDraftContent,
  onCancel,
  onApply,
}: OrganizeResultDialogProps) {
  const hasOrganizedDraft = organizedDraftContent.trim().length > 0;
  const contentContainerRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (!hasOrganizedDraft) return;

    const container = contentContainerRef.current;
    if (!container) return;

    container.scrollTop = container.scrollHeight;
  }, [organizedDraftContent, hasOrganizedDraft]);

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          onCancel();
        }
      }}
    >
      <DialogContent
        className="sm:max-w-3xl border-[var(--sys-current-border)] shadow-lg"
        style={{ backgroundColor: 'var(--color-card)', opacity: 1 }}
      >
        <DialogHeader>
          <DialogTitle>AI 정리 결과</DialogTitle>
          <DialogDescription>
            정리 결과를 확인한 뒤 적용 여부를 선택하세요. 적용하기 전에는 본문이 바뀌지 않습니다.
          </DialogDescription>
        </DialogHeader>

        <div
          ref={contentContainerRef}
          className="max-h-[60vh] overflow-y-auto rounded-lg border border-[var(--sys-current-border)] p-4"
          style={{ backgroundColor: 'var(--color-card)', opacity: 1 }}
        >
          {hasOrganizedDraft ? (
            <div className="prose max-w-none [--tw-prose-body:var(--color-foreground)] [--tw-prose-headings:var(--color-foreground)] [--tw-prose-links:var(--color-foreground)] [--tw-prose-bold:var(--color-foreground)] [--tw-prose-bullets:var(--color-foreground)] [--tw-prose-counters:var(--color-foreground)]">
              <MarkdownRenderer content={organizedDraftContent} useRemarkGfm useRehypeRaw />
            </div>
          ) : isOrganizing ? (
            <LoadingDotsText
              text="AI 정리 결과를 만들고 있어요"
              className="text-sm text-muted-foreground"
            />
          ) : (
            <p className="text-sm text-muted-foreground">AI 정리 결과가 비어 있습니다.</p>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onCancel} disabled={isApplying}>
            취소하기
          </Button>
          <Button
            type="button"
            onClick={onApply}
            disabled={readOnly || isBusy || !hasOrganizedDraft}
          >
            {isApplying ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            적용하기
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
