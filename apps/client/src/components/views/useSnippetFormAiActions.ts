import React from 'react';
import type { UseFormGetValues, UseFormSetValue } from 'react-hook-form';
import { toast } from 'sonner';
import { ApiError } from '@/lib/api';
import type {
  FormUiAction,
  OrganizeProgressHandlers,
  OrganizeResult,
  SnippetFormProps,
} from './snippet-form.types';

type SnippetFormValues = {
  content: string;
};

interface UseSnippetFormAiActionsParams {
  readOnly: boolean;
  onSave: SnippetFormProps['onSave'];
  onOrganize: SnippetFormProps['onOrganize'];
  onGenerateFeedback: SnippetFormProps['onGenerateFeedback'];
  hasOrganizedDraft: boolean;
  organizedDraftContent: string;
  isApplying: boolean;
  getValues: UseFormGetValues<SnippetFormValues>;
  setValue: UseFormSetValue<SnippetFormValues>;
  dispatch: React.Dispatch<FormUiAction>;
  discardOrganizedDraft: () => void;
}

export function useSnippetFormAiActions({
  readOnly,
  onSave,
  onOrganize,
  onGenerateFeedback,
  hasOrganizedDraft,
  organizedDraftContent,
  isApplying,
  getValues,
  setValue,
  dispatch,
  discardOrganizedDraft,
}: UseSnippetFormAiActionsParams) {
  const organizeAbortRef = React.useRef<AbortController | null>(null);
  const organizeRequestIdRef = React.useRef(0);
  const feedbackAbortRef = React.useRef<AbortController | null>(null);
  const feedbackRequestIdRef = React.useRef(0);

  React.useEffect(() => {
    return () => {
      organizeAbortRef.current?.abort();
      feedbackAbortRef.current?.abort();
    };
  }, []);

  const handleOrganizeClick = React.useCallback(async () => {
    if (!onOrganize) return;

    organizeAbortRef.current?.abort();
    const abortController = new AbortController();
    organizeAbortRef.current = abortController;
    organizeRequestIdRef.current += 1;
    const requestId = organizeRequestIdRef.current;

    const sourceContent = getValues('content');
    dispatch({ type: 'SET_SUBMIT_ERROR', payload: null });
    dispatch({
      type: 'OPEN_ORGANIZE_DRAFT',
      payload: {
        content: '',
      },
    });

    try {
      let streamedContent = '';
      const result = await onOrganize(sourceContent, {
        signal: abortController.signal,
        onChunk: (chunk) => {
          if (requestId !== organizeRequestIdRef.current || abortController.signal.aborted) {
            return;
          }

          streamedContent += chunk;
          dispatch({
            type: 'SET_ORGANIZE_DRAFT_CONTENT',
            payload: {
              content: streamedContent,
            },
          });
        },
      } satisfies OrganizeProgressHandlers);

      if (
        requestId !== organizeRequestIdRef.current ||
        abortController.signal.aborted ||
        (result as OrganizeResult | null | undefined)?.cancelled
      ) {
        return;
      }

      if (!result) {
        dispatch({ type: 'CLOSE_ORGANIZE_DRAFT' });
        dispatch({ type: 'SET_SUBMIT_ERROR', payload: 'AI 정리에 실패했습니다. 잠시 후 다시 시도해주세요.' });
        return;
      }

      const organized =
        result && typeof result.organizedContent === 'string' ? result.organizedContent : '';

      dispatch({
        type: 'SET_ORGANIZE_DRAFT_CONTENT',
        payload: {
          content: organized,
        },
      });

      if (organized.trim()) {
        toast('AI 정리 결과를 확인해 주세요.');
      } else {
        toast('AI 정리 결과가 비어 있습니다.');
      }
    } catch (error) {
      if (abortController.signal.aborted || requestId !== organizeRequestIdRef.current) {
        return;
      }

      console.error('Organize failed', error);
      dispatch({ type: 'CLOSE_ORGANIZE_DRAFT' });
      dispatch({ type: 'SET_SUBMIT_ERROR', payload: 'AI 정리에 실패했습니다. 잠시 후 다시 시도해주세요.' });
    } finally {
      if (organizeAbortRef.current === abortController) {
        organizeAbortRef.current = null;
      }
    }
  }, [dispatch, getValues, onOrganize]);

  const handleGenerateFeedbackClick = React.useCallback(async () => {
    if (!onGenerateFeedback) return;

    feedbackAbortRef.current?.abort();
    const abortController = new AbortController();
    feedbackAbortRef.current = abortController;
    feedbackRequestIdRef.current += 1;
    const requestId = feedbackRequestIdRef.current;

    const sourceContent = getValues('content');
    const nextOrganizedContent = hasOrganizedDraft ? organizedDraftContent : undefined;

    dispatch({ type: 'SET_SUBMIT_ERROR', payload: null });
    dispatch({ type: 'SET_PREVIEW_FEEDBACK', payload: null });

    try {
      const nextFeedback = await onGenerateFeedback(sourceContent, nextOrganizedContent, {
        signal: abortController.signal,
      });

      if (requestId !== feedbackRequestIdRef.current || abortController.signal.aborted) {
        return;
      }

      const resolvedFeedback = nextFeedback ?? null;
      dispatch({ type: 'SET_PREVIEW_FEEDBACK', payload: resolvedFeedback });

      if (resolvedFeedback) {
        toast('AI 피드백을 갱신했습니다.');
      } else {
        toast('AI 피드백 결과가 비어 있습니다.');
      }
    } catch (error) {
      if (abortController.signal.aborted || requestId !== feedbackRequestIdRef.current) {
        return;
      }

      console.error('Feedback generation failed', error);
      dispatch({ type: 'SET_SUBMIT_ERROR', payload: 'AI 피드백 생성에 실패했습니다. 잠시 후 다시 시도해주세요.' });
    } finally {
      if (feedbackAbortRef.current === abortController) {
        feedbackAbortRef.current = null;
      }
    }
  }, [
    dispatch,
    getValues,
    hasOrganizedDraft,
    onGenerateFeedback,
    organizedDraftContent,
  ]);

  const handleCancelFeedbackStreaming = React.useCallback(() => {
    feedbackAbortRef.current?.abort();
    feedbackRequestIdRef.current += 1;
    dispatch({ type: 'SET_PREVIEW_FEEDBACK', payload: null });
    toast('AI 피드백 생성을 취소했습니다.');
  }, [dispatch]);

  const handleApplyOrganizeDraft = React.useCallback(async () => {
    if (!onSave || !hasOrganizedDraft || readOnly) return;

    dispatch({ type: 'SET_IS_APPLYING', payload: true });
    dispatch({ type: 'SET_SUBMIT_ERROR', payload: null });

    try {
      await onSave(organizedDraftContent);
      setValue('content', organizedDraftContent);
      dispatch({ type: 'SET_PREVIEW_FEEDBACK', payload: null });
      discardOrganizedDraft();
      toast('정리 내용을 적용해 저장했습니다.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 405) {
        dispatch({ type: 'SET_SUBMIT_ERROR', payload: '작성 가능한 시간이 아닙니다. (06:00 ~ 23:59)' });
      } else if (error instanceof ApiError && error.status === 403) {
        dispatch({ type: 'SET_SUBMIT_ERROR', payload: '이 스니펫은 더 이상 편집할 수 없습니다.' });
        toast('이 스니펫은 더 이상 편집할 수 없습니다.');
      } else {
        console.error('Failed to apply organized draft:', error);
        dispatch({ type: 'SET_SUBMIT_ERROR', payload: '적용하기에 실패했습니다. 잠시 후 다시 시도해주세요.' });
      }
    } finally {
      dispatch({ type: 'SET_IS_APPLYING', payload: false });
    }
  }, [
    dispatch,
    discardOrganizedDraft,
    hasOrganizedDraft,
    onSave,
    organizedDraftContent,
    readOnly,
    setValue,
  ]);

  const handleCancelOrganizeDraft = React.useCallback(() => {
    if (isApplying) return;
    organizeAbortRef.current?.abort();
    organizeRequestIdRef.current += 1;
    discardOrganizedDraft();
  }, [discardOrganizedDraft, isApplying]);

  return {
    handleOrganizeClick,
    handleGenerateFeedbackClick,
    handleCancelFeedbackStreaming,
    handleApplyOrganizeDraft,
    handleCancelOrganizeDraft,
  };
}
