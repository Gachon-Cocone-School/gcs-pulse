import type { Feedback } from './SnippetAnalysisReport';

export interface OrganizeResult {
  organizedContent?: string | null;
}

export interface SnippetFormProps {
  initialContent?: string;
  onSave?: (content: string) => Promise<void>;
  readOnly?: boolean;
  onOrganize?: (content: string) => Promise<OrganizeResult | null | undefined>;
  onGenerateFeedback?: (content: string, organizedContent?: string) => Promise<Feedback | string | null>;
  isOrganizing?: boolean;
  isGeneratingFeedback?: boolean;
  feedback?: Feedback | string | null;
}

export type FormUiState = {
  showPreview: boolean;
  isSubmitting: boolean;
  isApplying: boolean;
  submitError: string | null;
  previewFeedbackRaw: Feedback | string | null;
  isOrganizeModalOpen: boolean;
  organizedDraftContent: string;
};
export type FormUiAction =
  | { type: 'SET_SHOW_PREVIEW'; payload: boolean }
  | { type: 'SET_IS_SUBMITTING'; payload: boolean }
  | { type: 'SET_IS_APPLYING'; payload: boolean }
  | { type: 'SET_SUBMIT_ERROR'; payload: string | null }
  | { type: 'SET_PREVIEW_FEEDBACK'; payload: Feedback | string | null }
  | {
      type: 'OPEN_ORGANIZE_DRAFT';
      payload: {
        content: string;
      };
    }
  | { type: 'CLOSE_ORGANIZE_DRAFT' }
  | { type: 'RESET_FOR_INITIAL_CONTENT' };
