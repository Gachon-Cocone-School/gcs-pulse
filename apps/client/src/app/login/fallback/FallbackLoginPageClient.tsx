'use client';

import { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';

import { api, ApiError } from '@/lib/api';
import { resetCsrfToken } from '@/lib/csrf';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export default function FallbackLoginPageClient() {
  const searchParams = useSearchParams();

  const [email, setEmail] = useState('');
  const [studentId, setStudentId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post('/auth/fallback', { email: email.trim(), student_id: studentId.trim() });
      resetCsrfToken();
      const next = searchParams.get('next');
      window.location.href = next && next.startsWith('/') && !next.startsWith('//') ? next : '/';
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('이메일 또는 학번이 올바르지 않습니다.');
      } else {
        setError('오류가 발생했습니다. 잠시 후 다시 시도해 주세요.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-mesh flex min-h-screen w-full flex-col items-center justify-center p-6">
      <Card className="w-full max-w-[440px] border-border/80 bg-card/95 shadow-sm backdrop-blur-sm">
        <CardHeader className="items-center gap-4 text-center">
          <Image
            src="/logo.svg"
            alt="Logo"
            width={240}
            height={48}
            className="theme-logo h-12 w-auto"
            priority
          />
          <div className="space-y-1">
            <CardTitle className="text-2xl font-bold text-foreground">간편 입장</CardTitle>
            <CardDescription className="text-sm text-muted-foreground">
              이메일과 학번을 입력하세요
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="email">이메일</Label>
              <Input
                id="email"
                type="email"
                placeholder="학교 이메일"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="student-id">학번</Label>
              <Input
                id="student-id"
                type="text"
                placeholder="학번 입력"
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                required
                autoComplete="off"
                inputMode="numeric"
              />
            </div>
            <Button
              type="submit"
              className="h-12 w-full text-base font-semibold"
              disabled={loading}
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : '입장하기'}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="border-t border-border pt-5">
          <Link
            href={`/login${searchParams.get('next') ? `?next=${encodeURIComponent(searchParams.get('next')!)}` : ''}`}
            className="w-full text-center text-sm text-muted-foreground hover:text-foreground"
          >
            ← Google 계정으로 로그인
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}
