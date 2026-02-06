'use client';

import React from 'react';
import { Navigation } from '../Navigation';
import { Button } from '../Button';
import { Card } from '../Card';
import { Input } from '../Input';
import { Badge } from '../Badge';
import { ProgressBar } from '../ProgressBar';
import { CourseCard } from '../CourseCard';
import { StatCard } from '../StatCard';
import { Tabs } from '../Tabs';
import { BookOpen, Users, Award, TrendingUp, Play, ChevronRight } from 'lucide-react';

export function MainDashboardView() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Navigation />
      
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Hero Section */}
        <section className="mb-12">
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div>
              <Badge variant="primary" className="mb-4">디자인 시스템 쇼케이스</Badge>
              <h1 className="mb-4 text-4xl font-bold text-slate-900 leading-tight">전문가급 LMS 디자인 시스템</h1>
              <p className="mb-6 text-lg text-slate-600">
                차분한 슬레이트 그레이와 틸 그린, 앰버 악센트가 조화를 이루는 세련된 디자인 시스템입니다. 
                일반적인 AI 생성 디자인을 넘어 전문성과 독창성을 갖춘 컴포넌트를 제공합니다.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button variant="primary" size="lg">
                  <Play className="w-5 h-5 mr-2" />
                  시작하기
                </Button>
                <Button variant="outline" size="lg">
                  컴포넌트 둘러보기
                  <ChevronRight className="w-5 h-5 ml-2" />
                </Button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <StatCard
                title="전체 수강생"
                value="12,450"
                change="+18% 이번 달"
                icon={Users}
                trend="up"
              />
              <StatCard
                title="완료된 강의"
                value="892"
                change="+12% 이번 달"
                icon={BookOpen}
                trend="up"
              />
              <StatCard
                title="평균 평점"
                value="4.8"
                change="0.2점 상승"
                icon={Award}
                trend="up"
              />
              <StatCard
                title="수료율"
                value="87%"
                change="+5% 이번 달"
                icon={TrendingUp}
                trend="up"
              />
            </div>
          </div>
        </section>

        {/* Design System Components */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">디자인 시스템 컴포넌트</h2>
          
          <Tabs
            tabs={[
              {
                id: 'buttons',
                label: '버튼',
                content: (
                  <Card>
                    <h4 className="font-semibold text-slate-900 mb-4">버튼 스타일</h4>
                    <div className="flex flex-wrap gap-3 mb-6">
                      <Button variant="primary">Primary</Button>
                      <Button variant="secondary">Secondary</Button>
                      <Button variant="accent">Accent</Button>
                      <Button variant="outline">Outline</Button>
                      <Button variant="ghost">Ghost</Button>
                    </div>
                    <h4 className="font-semibold text-slate-900 mb-4">버튼 크기</h4>
                    <div className="flex flex-wrap items-center gap-3">
                      <Button size="sm">Small</Button>
                      <Button size="md">Medium</Button>
                      <Button size="lg">Large</Button>
                    </div>
                  </Card>
                )
              },
              {
                id: 'inputs',
                label: '입력 필드',
                content: (
                  <Card>
                    <div className="grid md:grid-cols-2 gap-6">
                      <Input 
                        label="이메일" 
                        type="email"
                        placeholder="example@email.com"
                        helperText="이메일 주소를 입력해주세요"
                      />
                      <Input 
                        label="비밀번호" 
                        type="password"
                        placeholder="••••••••"
                      />
                      <Input 
                        label="이름" 
                        placeholder="홍길동"
                      />
                      <Input 
                        label="에러 예시" 
                        placeholder="잘못된 입력"
                        error="올바른 형식이 아닙니다"
                      />
                    </div>
                  </Card>
                )
              },
              {
                id: 'badges',
                label: '배지',
                content: (
                  <Card>
                    <h4 className="font-semibold text-slate-900 mb-4">배지 스타일</h4>
                    <div className="flex flex-wrap gap-3 mb-6">
                      <Badge variant="primary">Primary</Badge>
                      <Badge variant="accent">Accent</Badge>
                      <Badge variant="success">Success</Badge>
                      <Badge variant="warning">Warning</Badge>
                      <Badge variant="neutral">Neutral</Badge>
                    </div>
                    <h4 className="font-semibold text-slate-900 mb-4">배지 크기</h4>
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge size="sm">Small</Badge>
                      <Badge size="md">Medium</Badge>
                      <Badge size="lg">Large</Badge>
                    </div>
                  </Card>
                )
              },
              {
                id: 'progress',
                label: '진행률',
                content: (
                  <Card>
                    <div className="space-y-6">
                      <ProgressBar 
                        progress={75} 
                        label="리액트 마스터클래스"
                        variant="primary"
                      />
                      <ProgressBar 
                        progress={45} 
                        label="UX/UI 디자인 심화"
                        variant="accent"
                      />
                      <ProgressBar 
                        progress={92} 
                        label="타입스크립트 완성"
                        variant="gradient"
                      />
                      <ProgressBar 
                        progress={30} 
                        label="데이터 분석 입문"
                        variant="primary"
                      />
                    </div>
                  </Card>
                )
              },
              {
                id: 'cards',
                label: '카드',
                content: (
                  <div className="grid md:grid-cols-2 gap-4">
                    <Card variant="default">
                      <h5 className="font-semibold mb-2">Default Card</h5>
                      <p className="text-sm text-slate-500">기본 그림자 효과가 있는 카드입니다.</p>
                    </Card>
                    <Card variant="elevated">
                      <h5 className="font-semibold mb-2">Elevated Card</h5>
                      <p className="text-sm text-slate-500">강조된 그림자 효과가 있는 카드입니다.</p>
                    </Card>
                    <Card variant="bordered">
                      <h5 className="font-semibold mb-2">Bordered Card</h5>
                      <p className="text-sm text-slate-500">테두리 스타일의 카드입니다.</p>
                    </Card>
                    <Card variant="flat">
                      <h5 className="font-semibold mb-2">Flat Card</h5>
                      <p className="text-sm text-slate-500">플랫한 배경색만 있는 카드입니다.</p>
                    </Card>
                  </div>
                )
              }
            ]}
          />
        </section>

        {/* Course Cards Section */}
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-slate-900">인기 강의</h2>
            <Button variant="ghost">
              전체 보기
              <ChevronRight className="w-5 h-5 ml-1" />
            </Button>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <CourseCard
              title="프로덕트 디자인 마스터클래스: Figma부터 프로토타이핑까지"
              instructor="김민지"
              thumbnail="https://images.unsplash.com/photo-1558655146-d09347e92766?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxkaWdpdGFsJTIwZGVzaWdufGVufDF8fHx8MTc2NDg0ODUzOHww&ixlib=rb-4.1.0&q=80&w=1080"
              category="디자인"
              duration="8시간"
              students={3420}
              rating={4.9}
              progress={65}
            />
            <CourseCard
              title="모던 웹 개발: React & TypeScript 완전 정복"
              instructor="이준호"
              thumbnail="https://images.unsplash.com/photo-1515879218367-8466d910aaa4?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxwcm9ncmFtbWluZyUyMGNvZGV8ZW58MXx8fHwxNzY0ODY3MzI3fDA&ixlib=rb-4.1.0&q=80&w=1080"
              category="개발"
              duration="12시간"
              students={5280}
              rating={4.8}
              progress={42}
            />
            <CourseCard
              title="효율적인 업무를 위한 디지털 워크플로우"
              instructor="박서연"
              thumbnail="https://images.unsplash.com/photo-1524758631624-e2822e304c36?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjB3b3Jrc3BhY2V8ZW58MXx8fHwxNzY0ODk2MTA0fDA&ixlib=rb-4.1.0&q=80&w=1080"
              category="생산성"
              duration="5시간"
              students={2150}
              rating={4.7}
              progress={88}
            />
          </div>
        </section>
      </main>
    </div>
  );
}
