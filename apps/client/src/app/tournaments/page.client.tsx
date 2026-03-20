'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Loader2, Trophy } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/context/auth-context';
import { tournamentsApi } from '@/lib/api';
import type { TournamentStudentSessionItem } from '@/lib/types';

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return new Intl.DateTimeFormat('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export default function TournamentsPageClient() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  const [sessions, setSessions] = useState<TournamentStudentSessionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace('/login');
  }, [isLoading, isAuthenticated, router]);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await tournamentsApi.listMySessions();
      setSessions(response.items);
    } catch {
      setError('토너먼트 목록을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadSessions();
  }, [isAuthenticated, loadSessions]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-3xl px-6 py-8 space-y-6">
        <PageHeader
          title="토너먼트"
          description="내가 참가한 토너먼트 대진표를 확인할 수 있습니다."
        />

        {error ? (
          <Card className="border-destructive/40">
            <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
          </Card>
        ) : null}

        <Card className="glass-card rounded-xl animate-entrance">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-4 w-4 text-primary" />
              참가 중인 토너먼트
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-6 flex items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
            ) : sessions.length === 0 ? (
              <div className="rounded-lg border border-border/60 bg-card/70 px-4 py-8 text-center text-sm text-muted-foreground">
                참가 중인 토너먼트가 없습니다.
              </div>
            ) : (
              <div className="space-y-3">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className="flex items-center justify-between gap-4 rounded-lg border border-border/60 bg-card/70 px-4 py-3"
                  >
                    <div className="min-w-0 space-y-0.5">
                      <div className="text-sm font-medium truncate">{session.title}</div>
                      <div className="text-xs text-muted-foreground">{formatDate(session.updated_at)}</div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/tournaments/${session.id}/bracket`}>대진표</Link>
                      </Button>
                      <Button asChild size="sm" variant="secondary">
                        <Link href={`/tournaments/${session.id}/results?ref=list`}>결과 보기</Link>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
