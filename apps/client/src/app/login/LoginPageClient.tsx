'use client';

import Image from 'next/image';
import { API_URL } from '@/lib/api';
import { useAuth } from '@/context/auth-context';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export default function LoginPageClient() {
  const { authError } = useAuth();

  const handleGoogleLogin = () => {
    if (authError) {
      return;
    }
    window.location.href = `${API_URL}/auth/google/login`;
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
            <CardTitle className="text-2xl font-bold text-foreground">환영합니다</CardTitle>
            <CardDescription className="text-sm text-muted-foreground">
              가천 코코네 스쿨에 로그인하세요
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent className="space-y-3">
          {authError ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {authError}
            </div>
          ) : null}

          <Button
            type="button"
            variant="outline"
            onClick={handleGoogleLogin}
            disabled={Boolean(authError)}
            className="h-12 w-full justify-center gap-3 text-base font-semibold"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden>
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Google 계정으로 로그인
          </Button>
        </CardContent>

        <CardFooter className="border-t border-border pt-6">
          <p className="text-center text-sm leading-relaxed text-muted-foreground">
            학생과 교직원은 학교 Google 계정으로 로그인 해야 합니다.
          </p>
        </CardFooter>
      </Card>

      <div className="mt-6">
        <a
          href="https://github.com/Gachon-Cocone-School/gcs-pulse"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-full border border-border bg-card/80 px-4 py-2 text-sm font-semibold text-foreground shadow-sm transition hover:bg-card"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden>
            <path
              fill="currentColor"
              d="M12 .5a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.04c-3.34.73-4.04-1.41-4.04-1.41-.55-1.38-1.34-1.74-1.34-1.74-1.1-.74.08-.73.08-.73 1.21.09 1.85 1.23 1.85 1.23 1.08 1.84 2.83 1.31 3.52 1 .11-.77.42-1.31.77-1.61-2.67-.3-5.47-1.33-5.47-5.92 0-1.31.47-2.39 1.24-3.23-.12-.3-.54-1.52.12-3.17 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.29-1.55 3.29-1.23 3.29-1.23.66 1.65.24 2.87.12 3.17.77.84 1.24 1.92 1.24 3.23 0 4.6-2.81 5.61-5.49 5.9.43.37.82 1.1.82 2.21v3.28c0 .32.22.7.83.58A12 12 0 0 0 12 .5Z"
            />
          </svg>
          GitHub 저장소
        </a>
      </div>

      <footer className="mt-4 text-center text-xs font-medium text-muted-foreground">
        © 2026 Gachon Cocone School. All rights reserved.
      </footer>
    </div>
  );
}
