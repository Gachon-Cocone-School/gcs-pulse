'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { CheckCircle2, ChevronRight, AlertCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/auth-context';


interface Term {
  id: number;
  type: string;
  version: string;
  content: string;
  is_required: boolean;
}

export default function TermsPage() {
  const [terms, setTerms] = useState<Term[]>([]);
  const [agreements, setAgreements] = useState<Record<number, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();
  const { user, checkAuth } = useAuth();



  useEffect(() => {
    const fetchTerms = async () => {
      try {
        const data = await api.get<Term[]>('/terms');
        setTerms(data);
        
        // 사용자의 기존 동의 이력을 바탕으로 초기 상태를 설정합니다.
        const initialAgreements: Record<number, boolean> = {};
        const userConsentIds = user?.consents.map(c => c.term_id) || [];
        
        data.forEach(term => {
          initialAgreements[term.id] = userConsentIds.includes(term.id);
        });
        setAgreements(initialAgreements);

        // 추가된 로직: 이미 모든 필수 약관에 동의했다면 메인으로 즉시 이동
        const requiredTermIds = data.filter(t => t.is_required).map(t => t.id);
        const allRequiredAgreedLocally = requiredTermIds.every(id => userConsentIds.includes(id));
        
        if (allRequiredAgreedLocally && data.length > 0) {
          router.push('/');
          return;
        }
      } catch (error) {
        console.error('Failed to fetch terms:', error);
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchTerms();
    }
  }, [user]);


  const handleToggleAgreement = (id: number) => {
    setAgreements(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const allRequiredAgreed = terms
    .filter(term => term.is_required)
    .every(term => agreements[term.id]);

  const handleSubmit = async () => {
    if (!allRequiredAgreed) return;

    setSubmitting(true);
    try {
      // Post each consent
      await Promise.all(
        Object.entries(agreements).map(([termId, agreed]) => 
          api.post('/consents', { term_id: parseInt(termId), agreed })
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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-50 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-10">
            <Badge variant="primary" className="mb-4">Onboarding</Badge>
            <h1 className="text-3xl font-bold text-slate-900 mb-3">이용 약관 동의</h1>
            <p className="text-slate-500">서비스 이용을 위해 아래 약관에 동의해 주세요.</p>
          </div>

          <div className="space-y-6">
            {terms.map((term) => (
              <Card key={term.id} className="p-0 overflow-hidden border-2 border-slate-200 transition-all hover:border-slate-300">
                <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-white">
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col">
                      <span className="font-bold text-slate-900">
                        {term.type === 'service_terms' ? '서비스 이용약관' : 
                         term.type === 'privacy_policy' ? '개인정보 처리방침' : term.type}
                        <span className="ml-2 text-sm text-slate-400 font-normal">v{term.version}</span>
                      </span>
                      {term.is_required ? (
                        <span className="text-xs text-rose-500 font-medium">필수</span>
                      ) : (
                        <span className="text-xs text-slate-400 font-medium">선택</span>
                      )}
                    </div>
                  </div>
                  <button 
                    onClick={() => handleToggleAgreement(term.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                      agreements[term.id] 
                        ? 'bg-primary-100 text-primary-700' 
                        : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                    }`}
                  >
                    <CheckCircle2 className={`w-5 h-5 ${agreements[term.id] ? 'text-primary-600' : 'text-slate-400'}`} />
                    {agreements[term.id] ? '동의 완료' : '동의하기'}
                  </button>
                </div>
                <div className="p-6 bg-slate-50 max-h-60 overflow-y-auto text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                  {term.content}
                </div>
              </Card>
            ))}

            {!allRequiredAgreed && (
              <div className="flex items-center gap-2 p-4 bg-rose-50 text-rose-600 rounded-xl border border-rose-100 text-sm">
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
                variant="primary" 
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
