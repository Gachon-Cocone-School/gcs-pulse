import React from 'react';
import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
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
  readOnly: boolean;
  isBusy: boolean;
  organizedDraftContent: string;
  hasOrganizedDraftFeedback: boolean;
  onCancel: () => void;
  onApply: () => void;
}

export function OrganizeResultDialog({
  open,
  isApplying,
  readOnly,
  isBusy,
  organizedDraftContent,
  hasOrganizedDraftFeedback,
  onCancel,
  onApply,
}: OrganizeResultDialogProps) {
  const hasOrganizedDraft = organizedDraftContent.trim().length > 0;

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          onCancel();
        }
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
              <MarkdownRenderer content={organizedDraftContent} useRemarkGfm useRehypeRaw />
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
