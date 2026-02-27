import type { Feedback } from './SnippetAnalysisReport';

export function parseFeedback(raw: Feedback | string | null | undefined): Feedback | null {
  if (!raw) return null;
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw) as Feedback;
    } catch (e) {
      console.error('Failed to parse feedback JSON', e);
      return null;
    }
  }
  return raw;
}
