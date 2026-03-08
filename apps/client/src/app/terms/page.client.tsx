'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { CheckCircle2, ChevronRight, AlertCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import type { UserConsent } from '@/lib/types/auth';

interface Term {
  id: number;
  type: string;
  version: string;
  content: string;
  is_required: boolean;
}


export default function TermsPageClient() {
  const [terms, setTerms] = useState<Term[] | null>(null);
  const [agreements, setAgreements] = useState<Record<number, boolean>>({});
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();
  const { user, checkAuth } = useAuth();

  useEffect(() => {
    const fetchTerms = async () => {
      if (!user) return;

      let data: Term[] = [];
      try {
        data = await api.get<Term[]>('/terms');
      } catch (error) {
        console.error('Failed to fetch terms:', error);
      }

      const userConsentIds = (user.consents as UserConsent[]).map((c) => c.term_id);
      setTerms(data);
      setAgreements(
        Object.fromEntries(
          data.map((term) => [term.id, userConsentIds.includes(term.id)])
        )
      );
    };

    fetchTerms();
  }, [user]);

  const handleToggleAgreement = (id: number) => {
    setAgreements(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const requiredTerms = (terms ?? []).filter((term) => term.is_required);

  const allRequiredAgreed = requiredTerms.every((term) => agreements[term.id]);


  const handleSubmit = async () => {
    if (!allRequiredAgreed) return;

    setSubmitting(true);
    try {
      // Post each consent
      await Promise.all(
        Object.entries(agreements).map(([termId, agreed]) =>
          api.post('/consents', { term_id: Number(termId), agreed })
        )
      );

      // 약관 동의 후 최신 유저 정보를 다시 가져와서 consents 상태를 동기화합니다.
      await checkAuth();

      router.push('/');
    } catch (error) {
      console.error('Failed to submit consents:', error);
      alert('동의 제출에 실패했습니다. 다시 시도해 주세요.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!terms) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-10 h-10 animate-spin rounded-full border-4 border-border border-t-primary" />
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-10">
            <Badge variant="default" className="mb-4">Onboarding</Badge>
            <h1 className="text-3xl font-bold text-foreground mb-3">이용 약관 동의</h1>
            <p className="text-muted-foreground">서비스 이용을 위해 아래 약관에 동의해 주세요.</p>
          </div>

          <div className="space-y-6">
            {terms.map((term) => (
              <Card key={term.id} className="p-0 overflow-hidden border-2 border-border transition-all hover:border-ring">
                <div className="p-6 border-b border-border/70 flex items-center justify-between bg-card">
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col">
                      <span className="font-bold text-foreground">
                        {term.type === 'service_terms' ? '서비스 이용약관' :
                         term.type === 'privacy_policy' ? '개인정보 처리방침' : term.type}
                        <span className="ml-2 text-sm text-muted-foreground font-normal">v{term.version}</span>
                      </span>
                      {term.is_required ? (
                        <span className="text-xs text-destructive font-medium">필수</span>
                      ) : (
                        <span className="text-xs text-muted-foreground font-medium">선택</span>
                      )}
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => handleToggleAgreement(term.id)}
                    aria-pressed={agreements[term.id]}
                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                      agreements[term.id]
                        ? 'bg-primary/15 text-primary'
                        : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                  >
                    <CheckCircle2 className={`w-5 h-5 ${agreements[term.id] ? 'text-primary' : 'text-muted-foreground'}`} />
                    {agreements[term.id] ? '동의 완료' : '동의하기'}
                  </Button>
                </div>
                <div className="p-6 bg-background max-h-60 overflow-y-auto text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                  {term.content}
                </div>
              </Card>
            ))}

            {!allRequiredAgreed && (
              <div className="flex items-center gap-2 rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                필수 약관에 모두 동의해 주셔야 서비스 이용이 가능합니다.
              </div>
            )}

            <div className="flex gap-4 pt-4">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => router.push('/')}
              >
                나중에 하기
              </Button>
              <Button
                variant="default"
                className="flex-1"
                disabled={!allRequiredAgreed || submitting}
                onClick={handleSubmit}
              >
                {submitting ? '처리 중...' : '동의하고 시작하기'}
                <ChevronRight className="ml-2 w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
