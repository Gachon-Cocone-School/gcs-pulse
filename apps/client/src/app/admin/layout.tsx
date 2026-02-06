'use client';

import React from 'react';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navigation } from '@/components/Navigation';
import { Shield, Key, FileText, Settings, Users, ArrowLeft, Layers, User } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const menuItems = [
    { name: '사용자 관리', href: '/admin/users', icon: User },
    { name: '팀 관리', href: '/admin/teams', icon: Users },
    { name: '역할 할당', href: '/admin/role-rules', icon: Layers },    
    { name: '약관 관리', href: '/admin/terms', icon: FileText },    
    { name: '권한 관리', href: '/admin/permissions', icon: Key },    
  ];

  return (
    <ProtectedRoute adminOnly>
      <div className="min-h-screen bg-slate-50">
        <Navigation />
        
        <div className="max-w-7xl mx-auto px-6 py-8 flex gap-8">
          {/* Sidebar */}
          <aside className="w-64 flex-shrink-0">
            <div className="bg-white border-2 border-slate-200 rounded-2xl p-4 sticky top-24">
              <div className="px-4 py-3 border-b border-slate-100 mb-4 flex items-center gap-3">
                <Shield className="w-6 h-6 text-primary-600" />
                <span className="font-bold text-slate-900">관리자 메뉴</span>
              </div>
              
              <nav className="space-y-1">
                {menuItems.map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <Link 
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium ${
                        isActive 
                          ? 'bg-primary-600 text-white shadow-lg shadow-primary-200' 
                          : 'text-slate-600 hover:bg-slate-50 hover:text-primary-600'
                      }`}
                    >
                      <item.icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                      <span className={isActive ? 'text-white' : ''}>{item.name}</span>
                    </Link>
                  );
                })}
              </nav>

              <div className="mt-8 pt-4 border-t border-slate-100">
                <Link href="/" className="flex items-center gap-3 px-4 py-3 text-slate-500 hover:text-primary-600 transition-colors text-sm font-medium">
                  <ArrowLeft className="w-4 h-4" />
                  메인으로 돌아가기
                </Link>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1 min-w-0">
            {children}
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
