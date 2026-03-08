import React from 'react';
import { api } from '@/lib/api';
import type {
  FeedbackProgressHandlers,
  OrganizeProgressHandlers,
  OrganizeResult,
} from '@/components/views/snippet-form.types';

interface UseSnippetStreamingActionsParams {
  kind: 'daily' | 'weekly';
  basePath: string;
  requestHeaders?: Record<string, string>;
  setSnippet: React.Dispatch<React.SetStateAction<any>>;
  setOrganizing: React.Dispatch<React.SetStateAction<boolean>>;
  setGeneratingFeedback: React.Dispatch<React.SetStateAction<boolean>>;
}

function processSseEvent(
  rawEvent: string,
  handlers: {
    onChunk?: (chunk: string) => void;
    onDone?: (payload: any) => void;
    onError?: (message: string) => void;
  },
) {
  let eventName = 'message';
  const dataLines: string[] = [];

  for (const line of rawEvent.split('\n')) {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
    }
  }

  const dataText = dataLines.join('\n');
  if (!dataText) return;

  let parsed: any = null;
  try {
    parsed = JSON.parse(dataText);
  } catch {
    return;
  }

  if (eventName === 'chunk') {
    if (typeof parsed?.content === 'string') {
      handlers.onChunk?.(parsed.content);
    }
    return;
  }

  if (eventName === 'done') {
    handlers.onDone?.(parsed);
    return;
  }

  if (eventName === 'error') {
    const detail = typeof parsed?.detail === 'string' ? parsed.detail : 'AI processing failed';
    handlers.onError?.(detail);
  }
}

async function consumeSseStream(
  response: Response,
  handlers: {
    onChunk?: (chunk: string) => void;
    onDone?: (payload: any) => void;
  },
) {
  if (!response.body) {
    throw new Error('SSE stream body is empty');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split('\n\n');
    buffer = events.pop() ?? '';

    for (const event of events) {
      processSseEvent(event, {
        ...handlers,
        onError: (message) => {
          throw new Error(message);
        },
      });
    }
  }

  const tailEvent = buffer.trim();
  if (tailEvent) {
    processSseEvent(tailEvent, {
      ...handlers,
      onError: (message) => {
        throw new Error(message);
      },
    });
  }
}

export function useSnippetStreamingActions({
  kind,
  basePath,
  requestHeaders,
  setSnippet,
  setOrganizing,
  setGeneratingFeedback,
}: UseSnippetStreamingActionsParams) {
  const handleOrganize = React.useCallback(
    async (content: string, handlers?: OrganizeProgressHandlers): Promise<OrganizeResult | null> => {
      setOrganizing(true);

      try {
        const endpoint = `${basePath}/organize${basePath.includes('?') ? '&' : '?'}stream=1`;
        const headers = new Headers(requestHeaders);
        headers.set('Content-Type', 'application/json');
        headers.set('Accept', 'text/event-stream');

        const response = await api.request(endpoint, {
          method: 'POST',
          headers,
          body: JSON.stringify({ content }),
          signal: handlers?.signal,
        });

        if (!response.ok) {
          throw new Error(`Organize request failed: ${response.status}`);
        }

        const contentType = response.headers.get('content-type') ?? '';
        if (contentType.includes('application/json')) {
          const res = await response.json();
          return {
            organizedContent: typeof res?.organized_content === 'string' ? res.organized_content : null,
          };
        }

        let doneOrganizedContent: string | null = null;
        let chunkText = '';

        await consumeSseStream(response, {
          onChunk: (chunk) => {
            chunkText += chunk;
            handlers?.onChunk?.(chunk);
          },
          onDone: (payload) => {
            doneOrganizedContent =
              typeof payload?.organized_content === 'string' ? payload.organized_content : null;
          },
        });

        const finalText = doneOrganizedContent ?? chunkText;

        return {
          organizedContent: finalText || null,
        };
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return { cancelled: true };
        }

        console.error(`Failed to organize ${kind} snippet`, err);
        return null;
      } finally {
        setOrganizing(false);
      }
    },
    [basePath, kind, requestHeaders, setOrganizing],
  );

  const handleGenerateFeedback = React.useCallback(
    async (_content: string, _organizedContent?: string, handlers?: FeedbackProgressHandlers) => {
      setGeneratingFeedback(true);

      try {
        const endpoint = `${basePath}/feedback${basePath.includes('?') ? '&' : '?'}stream=1`;
        const headers = new Headers(requestHeaders);
        headers.set('Accept', 'text/event-stream');

        const response = await api.request(endpoint, {
          method: 'GET',
          headers,
          signal: handlers?.signal,
        });

        if (!response.ok) {
          throw new Error(`Feedback request failed: ${response.status}`);
        }

        const contentType = response.headers.get('content-type') ?? '';
        if (contentType.includes('application/json')) {
          const res = await response.json();
          const nextFeedback = typeof res?.feedback === 'string' ? res.feedback : null;
          setSnippet((prev: any) => (prev ? { ...prev, feedback: nextFeedback } : prev));
          return nextFeedback;
        }

        let doneFeedback: string | null = null;
        let chunkText = '';

        await consumeSseStream(response, {
          onChunk: (chunk) => {
            chunkText += chunk;
            handlers?.onChunk?.(chunk);
          },
          onDone: (payload) => {
            doneFeedback = typeof payload?.feedback === 'string' ? payload.feedback : null;
          },
        });

        const finalFeedback = doneFeedback ?? chunkText;
        const nextFeedback = finalFeedback || null;
        setSnippet((prev: any) => (prev ? { ...prev, feedback: nextFeedback } : prev));
        return nextFeedback;
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return null;
        }

        console.error(`Failed to generate ${kind} feedback`, err);
        return null;
      } finally {
        setGeneratingFeedback(false);
      }
    },
    [basePath, kind, requestHeaders, setGeneratingFeedback, setSnippet],
  );

  return {
    handleOrganize,
    handleGenerateFeedback,
  };
}
