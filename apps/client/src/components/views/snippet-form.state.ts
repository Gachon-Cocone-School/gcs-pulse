import type { FormUiAction, FormUiState } from './snippet-form.types';

export const initialFormUiState: FormUiState = {
  showPreview: false,
  isSubmitting: false,
  isApplying: false,
  submitError: null,
  previewFeedbackRaw: null,
  isOrganizeModalOpen: false,
  organizedDraftContent: '',
  organizedDraftFeedback: null,
};

export function formUiReducer(state: FormUiState, action: FormUiAction): FormUiState {
  switch (action.type) {
    case 'SET_SHOW_PREVIEW':
      return {
        ...state,
        showPreview: action.payload,
      };
    case 'SET_IS_SUBMITTING':
      return {
        ...state,
        isSubmitting: action.payload,
      };
    case 'SET_IS_APPLYING':
      return {
        ...state,
        isApplying: action.payload,
      };
    case 'SET_SUBMIT_ERROR':
      return {
        ...state,
        submitError: action.payload,
      };
    case 'SET_PREVIEW_FEEDBACK':
      return {
        ...state,
        previewFeedbackRaw: action.payload,
      };
    case 'OPEN_ORGANIZE_DRAFT':
      return {
        ...state,
        isOrganizeModalOpen: true,
        organizedDraftContent: action.payload.content,
        organizedDraftFeedback: action.payload.feedback,
      };
    case 'CLOSE_ORGANIZE_DRAFT':
      return {
        ...state,
        isOrganizeModalOpen: false,
        organizedDraftContent: '',
        organizedDraftFeedback: null,
      };
    case 'RESET_FOR_INITIAL_CONTENT':
      return {
        ...state,
        previewFeedbackRaw: null,
        isOrganizeModalOpen: false,
        organizedDraftContent: '',
        organizedDraftFeedback: null,
      };
    default:
      return state;
  }
}
