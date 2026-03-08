import type { Feedback } from './SnippetAnalysisReport';

interface ParseFeedbackOptions {
  silent?: boolean;
}

function decodePartialString(value: string): string {
  return value.replace(/\\n/g, '\n').replace(/\\"/g, '"').trim();
}

export function parseFeedback(
  raw: Feedback | string | null | undefined,
  options: ParseFeedbackOptions = {},
): Feedback | null {
  if (!raw) return null;
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw) as Feedback;
    } catch (e) {
      if (!options.silent) {
        console.error('Failed to parse feedback JSON', e);
      }
      return null;
    }
  }
  return raw;
}

export function parsePartialFeedback(raw: string | null | undefined): Partial<Feedback> | null {
  if (!raw) return null;

  const partial: Partial<Feedback> = {};

  const totalScoreMatch = raw.match(/"total_score"\s*:\s*(-?\d+(?:\.\d+)?)/);
  if (totalScoreMatch) {
    partial.total_score = Number(totalScoreMatch[1]);
  }

  const keyLearningMatch = raw.match(/"key_learning"\s*:\s*"([\s\S]*?)(?:"|$)/);
  if (keyLearningMatch) {
    partial.key_learning = decodePartialString(keyLearningMatch[1]);
  }

  const nextActionMatch = raw.match(/"next_action"\s*:\s*"([\s\S]*?)(?:"|$)/);
  if (nextActionMatch) {
    partial.next_action = decodePartialString(nextActionMatch[1]);
  }

  return Object.keys(partial).length > 0 ? partial : null;
}
