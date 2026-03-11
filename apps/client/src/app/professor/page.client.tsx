'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { redirect } from 'next/navigation';

import { Navigation } from '@/components/Navigation';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';
import { createMentoringSse, mentoringApi } from '@/lib/api';
import { hasPrivilegedRole } from '@/lib/types';
import type { MentoringChatMessageResponse, MentoringChatSessionResponse } from '@/lib/types';

type ChatState = {
  sessions: MentoringChatSessionResponse[];
  selectedSessionId: number | null;
  messages: MentoringChatMessageResponse[];
  input: string;
  isSending: boolean;
  error: string | null;
};

export default function ProfessorPageClient() {
  const { user, isAuthenticated, isLoading } = useAuth();

  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  const [chatState, setChatState] = useState<ChatState>({
    sessions: [],
    selectedSessionId: null,
    messages: [],
    input: '',
    isSending: false,
    error: null,
  });

  const selectedSession = useMemo(
    () => chatState.sessions.find((session) => session.id === chatState.selectedSessionId) ?? null,
    [chatState.sessions, chatState.selectedSessionId],
  );

  const loadBootstrappedData = useCallback(async () => {
    try {
      setChatState((prev) => ({ ...prev, error: null }));
      const sessionData = await mentoringApi.listSessions();

      if (sessionData.items.length > 0) {
        const firstSession = sessionData.items[0];
        const messageData = await mentoringApi.getMessages(firstSession.id);
        setChatState((prev) => ({
          ...prev,
          sessions: sessionData.items,
          selectedSessionId: firstSession.id,
          messages: messageData.items,
        }));
      } else {
        setChatState((prev) => ({
          ...prev,
          sessions: [],
          selectedSessionId: null,
          messages: [],
        }));
      }
    } catch (e) {
      console.error(e);
      setChatState((prev) => ({ ...prev, error: '멘토링 데이터를 불러오지 못했습니다.' }));
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    const timerId = window.setTimeout(() => {
      void loadBootstrappedData();
    }, 0);
    return () => {
      window.clearTimeout(timerId);
    };
  }, [isAuthenticated, loadBootstrappedData]);

  const handleCreateSession = useCallback(async () => {
    try {
      setChatState((prev) => ({ ...prev, error: null }));
      const created = await mentoringApi.createSession({ title: '새 멘토링 세션' });
      setChatState((prev) => ({
        ...prev,
        sessions: [created, ...prev.sessions],
        selectedSessionId: created.id,
        messages: [],
      }));
    } catch (e) {
      console.error(e);
      setChatState((prev) => ({ ...prev, error: '세션 생성에 실패했습니다.' }));
    }
  }, []);

  const handleSelectSession = useCallback(async (sessionId: number) => {
    try {
      setChatState((prev) => ({ ...prev, error: null, selectedSessionId: sessionId }));
      const result = await mentoringApi.getMessages(sessionId);
      setChatState((prev) => ({ ...prev, messages: result.items }));
    } catch (e) {
      console.error(e);
      setChatState((prev) => ({ ...prev, error: '메시지를 불러오지 못했습니다.' }));
    }
  }, []);

  const handleSend = useCallback(async () => {
    const { selectedSessionId, input, isSending } = chatState;
    if (!selectedSessionId || !input.trim() || isSending) return;

    const text = input.trim();
    setChatState((prev) => ({ ...prev, input: '', isSending: true, error: null }));

    const optimisticUserMessage: MentoringChatMessageResponse = {
      id: Date.now() * -1,
      session_id: selectedSessionId,
      role: 'user',
      content_markdown: text,
      created_at: new Date().toISOString(),
      latency_ms: null,
      tokens_input: null,
      tokens_output: null,
    };

    const optimisticAssistantMessage: MentoringChatMessageResponse = {
      id: Date.now() * -1 - 1,
      session_id: selectedSessionId,
      role: 'assistant',
      content_markdown: '',
      created_at: new Date().toISOString(),
      latency_ms: null,
      tokens_input: null,
      tokens_output: null,
    };

    setChatState((prev) => ({
      ...prev,
      messages: [...prev.messages, optimisticUserMessage, optimisticAssistantMessage],
    }));

    try {
      const source = createMentoringSse(selectedSessionId, text, {
        onDelta: (delta) => {
          setChatState((prev) => ({
            ...prev,
            messages: prev.messages.map((message) =>
              message.id === optimisticAssistantMessage.id
                ? { ...message, content_markdown: message.content_markdown + delta }
                : message,
            ),
          }));
        },
        onDone: async () => {
          source.close();
          const refreshed = await mentoringApi.getMessages(selectedSessionId);
          setChatState((prev) => ({
            ...prev,
            messages: refreshed.items,
            isSending: false,
          }));
        },
        onError: (detail) => {
          source.close();
          setChatState((prev) => ({ ...prev, error: detail, isSending: false }));
        },
      });
    } catch (e) {
      console.error(e);
      setChatState((prev) => ({ ...prev, error: '메시지 전송에 실패했습니다.', isSending: false }));
    }
  }, [chatState]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">교수 멘토링 화면을 준비 중입니다...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    redirect('/login');
  }

  if (!hasAccess || !isProfessor) {
    return <AccessDeniedView reason="student-only" />;
  }

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-7xl px-6 py-8 grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
        <Card className="glass-card rounded-xl h-[calc(100vh-120px)]">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">세션</CardTitle>
            <Button size="sm" onClick={handleCreateSession} variant="secondary">
              새 세션
            </Button>
          </CardHeader>
          <CardContent className="space-y-2 overflow-y-auto">
            {chatState.sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                  chatState.selectedSessionId === session.id
                    ? 'border-primary/50 bg-primary/10 text-foreground'
                    : 'border-border/70 bg-card/60 hover:bg-muted/50'
                }`}
                onClick={() => {
                  void handleSelectSession(session.id);
                }}
              >
                <div className="font-medium">{session.title}</div>
                <div className="text-xs text-muted-foreground">{session.status}</div>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card className="glass-card rounded-xl h-[calc(100vh-120px)] flex flex-col">
          <CardHeader>
            <CardTitle className="text-base">{selectedSession?.title ?? '멘토링 채팅'}</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto space-y-2">
            {chatState.messages.map((message) => (
              <div
                key={message.id}
                className={`rounded-xl border px-3 py-2 text-sm whitespace-pre-wrap ${
                  message.role === 'user'
                    ? 'ml-12 border-primary/20 bg-primary/90 text-primary-foreground'
                    : 'mr-12 border-border/70 bg-card/80 text-foreground'
                }`}
              >
                {message.content_markdown || (chatState.isSending && message.role === 'assistant' ? '응답 생성 중...' : '')}
              </div>
            ))}
          </CardContent>
          <div className="border-t border-border/70 p-3 space-y-2 bg-muted/20">
            <textarea
              value={chatState.input}
              onChange={(e) => setChatState((prev) => ({ ...prev, input: e.target.value }))}
              placeholder="이번주 상황을 요약해줘"
              className="w-full min-h-[90px] rounded-md border border-border/70 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
            />
            <div className="flex justify-end">
              <Button
                onClick={() => {
                  void handleSend();
                }}
                disabled={!chatState.selectedSessionId || chatState.isSending || !chatState.input.trim()}
                variant="secondary"
              >
                {chatState.isSending ? '전송 중...' : '전송'}
              </Button>
            </div>
            {chatState.error ? <p className="text-xs text-destructive">{chatState.error}</p> : null}
          </div>
        </Card>
      </main>
    </div>
  );
}
