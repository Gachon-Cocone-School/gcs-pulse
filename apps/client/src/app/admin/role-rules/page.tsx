'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { Search, Trash2, Edit2, Shield, Check, Mail, Globe, Layers, ArrowUpDown, ChevronRight, Plus, Loader2 } from 'lucide-react';

interface RoleRule {
  id: number;
  rule_type: 'email_pattern' | 'email_list';
  rule_value: any;
  assigned_role: string;
  priority: number;
  is_active: boolean;
  created_at: string;
}

export default function RoleRulesPage() {
  const [rules, setRules] = useState<RoleRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingRule, setEditingRule] = useState<RoleRule | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [newRule, setNewRule] = useState<Partial<RoleRule>>({
    rule_type: 'email_pattern',
    rule_value: { pattern: '' },
    assigned_role: 'user',
    priority: 100,
    is_active: true
  });

  const fetchRules = async () => {
    try {
      const data = await api.get<RoleRule[]>('/admin/role-rules');
      setRules(data);
    } catch (error) {
      console.error('Failed to fetch rules:', error);
      setRules([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleCreate = async () => {
    try {
      const preparedRule = { ...newRule };
      if (preparedRule.rule_type === 'email_list' && Array.isArray(preparedRule.rule_value?.emails)) {
        preparedRule.rule_value.emails = preparedRule.rule_value.emails
          .map((e: string) => e.trim())
          .filter(Boolean);
      }
      await api.post('/admin/role-rules', preparedRule);
      setIsAdding(false);
      setNewRule({ rule_type: 'email_pattern', rule_value: { pattern: '' }, assigned_role: 'user', priority: 100, is_active: true });
      fetchRules();
    } catch (error) {
      alert('생성에 실패했습니다.');
    }
  };

  const handleUpdate = async () => {
    if (!editingRule) return;
    try {
      const { id, ...updates } = editingRule as any;
      const preparedValue = { ...updates.rule_value };
      if (updates.rule_type === 'email_list' && Array.isArray(preparedValue.emails)) {
        preparedValue.emails = preparedValue.emails
          .map((e: string) => e.trim())
          .filter(Boolean);
      }
      await api.put(`/admin/role-rules/${id}`, {
        rule_value: preparedValue,
        assigned_role: updates.assigned_role,
        priority: updates.priority,
        is_active: updates.is_active
      });
      setEditingRule(null);
      fetchRules();
    } catch (error) {
      alert('수정에 실패했습니다.');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/admin/role-rules/${id}`);
      fetchRules();
    } catch (error) {
      alert('삭제에 실패했습니다.');
    }
  };

  const filteredRules = rules.filter(r => 
    r.assigned_role.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (r.rule_type === 'email_pattern' && r.rule_value.pattern?.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (r.rule_type === 'email_list' && r.rule_value.emails?.some((e: string) => e.toLowerCase().includes(searchQuery.toLowerCase())))
  );

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
      <p className="text-slate-500 font-medium">배정 규칙을 불러오는 중...</p>
    </div>
  );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 tracking-tight mb-0">역할 할당</h2>
        <button 
          onClick={() => setIsAdding(true)}
          className="px-4 py-2 bg-primary-600 text-white text-sm font-bold rounded-lg shadow-md shadow-primary-50 hover:bg-primary-700 transition-all flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> 신규 규칙 추가
        </button>
      </div>

      <div className="bg-white border border-slate-100 shadow-sm rounded-xl overflow-hidden focus-within:border-primary-400 transition-all">
        <div className="flex items-center px-4 gap-3 h-10">
          <Search className="w-4 h-4 text-slate-300 shrink-0" />
          <input 
            type="text"
            placeholder="역할 또는 패턴으로 검색..."
            className="w-full bg-transparent outline-none font-medium text-[14px] text-slate-600 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {filteredRules.length > 0 ? (
          filteredRules.sort((a, b) => (a.priority || 0) - (b.priority || 0)).map((rule) => (
            <div key={rule.id} className="w-full">
              <Card 
                padding="none" 
                className={`w-full border border-slate-100 transition-all group overflow-hidden ${editingRule?.id === rule.id ? 'rounded-b-none border-b-0 shadow-none ring-1 ring-primary-100 relative z-10' : 'hover:border-primary-100'}`}
              >
                <div className="flex items-center justify-between px-4 py-2.5 bg-white">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${rule.is_active ? 'bg-primary-50' : 'bg-slate-50'}`}>
                      {rule.rule_type === 'email_pattern' ? (
                        <Globe className={`w-5 h-5 ${rule.is_active ? 'text-primary-600' : 'text-slate-400'}`} />
                      ) : (
                        <Layers className={`w-5 h-5 ${rule.is_active ? 'text-primary-600' : 'text-slate-400'}`} />
                      )}
                    </div>
                    <div>
                      <h6 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                        {rule.assigned_role}
                        <div className="flex gap-1">
                          <Badge variant={rule.rule_type === 'email_pattern' ? 'primary' : 'accent'} size="sm" className="px-1.5 py-0 font-bold text-[8px] uppercase">
                            {rule.rule_type === 'email_pattern' ? 'REGEX' : 'LIST'}
                          </Badge>
                          {!rule.is_active && (
                            <Badge variant="neutral" size="sm" className="px-1.5 py-0 font-bold text-[8px] uppercase">
                              DISABLED
                            </Badge>
                          )}
                        </div>
                      </h6>
                      <div className="flex items-center gap-3 mt-0">
                        <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium whitespace-nowrap">
                          <ArrowUpDown className="w-3 h-3 text-slate-400" /> 우선순위 {rule.priority}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
                    <button 
                      onClick={() => setEditingRule(editingRule?.id === rule.id ? null : rule)}
                      className={`p-1.5 rounded-md transition-all ${editingRule?.id === rule.id ? 'bg-primary-500 text-white shadow-sm' : 'text-slate-400 hover:text-primary-600 hover:bg-primary-50'}`}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button 
                      onClick={() => handleDelete(rule.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-all"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </Card>

              {/* Inline Edit Area */}
              {editingRule?.id === rule.id && (
                <div className="w-full animate-in slide-in-from-top-1 duration-200">
                  <div className="bg-slate-50/40 border-x border-primary-100 border-b border-primary-100 rounded-b-xl border-t-0 p-5 space-y-6 ring-1 ring-primary-100 ring-t-0 relative z-0">
                    <div className="space-y-3">
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">
                        {rule.rule_type === 'email_pattern' ? '이메일 정규식 패턴' : '이메일 목록 (콤마 구분)'}
                      </label>
                      <div className={`flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm ${rule.rule_type === 'email_pattern' ? 'h-10 items-center' : 'min-h-[40px] items-start py-1.5'}`}>
                        {rule.rule_type === 'email_pattern' ? <Globe className="w-4 h-4 text-primary-500 shrink-0" /> : <Layers className="w-4 h-4 text-primary-500 shrink-0 mt-1" />}
                        {rule.rule_type === 'email_pattern' ? (
                          <input 
                            type="text"
                            className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                            value={editingRule.rule_value.pattern}
                            onChange={(e) => setEditingRule({...editingRule, rule_value: { pattern: e.target.value }})}
                            placeholder=".*@gachon.ac.kr"
                          />
                        ) : (
                          <textarea 
                            className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0 min-h-[100px] resize-none py-1"
                            value={editingRule.rule_value.emails?.join(',')}
                            onChange={(e) => {
                              const emails = e.target.value.split(',');
                              setEditingRule({...editingRule, rule_value: { emails }});
                            }}
                            placeholder="user1@example.com,user2@example.com"
                          />
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-3">
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">할당할 역할</label>
                        <div className="flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm h-10 items-center">
                          <Shield className="w-4 h-4 text-primary-500 shrink-0" />
                          <input 
                            type="text"
                            className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                            value={editingRule.assigned_role}
                            onChange={(e) => setEditingRule({...editingRule, assigned_role: e.target.value})}
                            placeholder="admin, user 등"
                          />
                        </div>
                      </div>

                      <div className="space-y-3">
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">우선순위</label>
                        <div className="flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm h-10 items-center">
                          <ArrowUpDown className="w-4 h-4 text-primary-500 shrink-0" />
                          <input 
                            type="number"
                            className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                            value={editingRule.priority}
                            onChange={(e) => setEditingRule({...editingRule, priority: parseInt(e.target.value)})}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-xl">
                      <div className="flex items-center gap-3">
                        <Shield className={`w-4 h-4 ${editingRule.is_active ? 'text-primary-500' : 'text-slate-400'}`} />
                        <div>
                          <p className="text-[11px] font-bold text-slate-900">규칙 활성화</p>
                        </div>
                      </div>
                      <input 
                        type="checkbox" 
                        className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                        checked={editingRule.is_active}
                        onChange={(e) => setEditingRule({...editingRule, is_active: e.target.checked})}
                      />
                    </div>

                    <div className="flex justify-end gap-2 pt-5 border-t border-slate-100/60">
                      <button 
                        onClick={() => setEditingRule(null)}
                        className="px-4 py-1.5 text-xs font-bold text-slate-500 hover:text-slate-700 transition-colors"
                      >
                        취소
                      </button>
                      <button 
                        onClick={handleUpdate}
                        className="px-6 py-1.5 bg-primary-600 text-white text-xs font-bold rounded-lg shadow-md shadow-primary-50 hover:bg-primary-700 transition-all flex items-center gap-2"
                      >
                        <Check className="w-3.5 h-3.5" /> 저장하기
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="text-center py-20 bg-white border border-dashed border-slate-200 rounded-2xl">
            <Mail className="w-10 h-10 text-slate-200 mx-auto mb-4" />
            <p className="text-sm text-slate-400 font-medium">검색된 규칙이 없습니다.</p>
          </div>
        )}
      </div>

      {/* Add New Rule Modal */}
      {isAdding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 animate-in fade-in duration-200">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setIsAdding(false)} />
          <Card className="w-full max-w-xl relative z-10 shadow-2xl p-0 overflow-hidden rounded-2xl border-none">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h3 className="text-lg font-bold text-slate-900">새 규칙 추가</h3>
              <button 
                onClick={() => setIsAdding(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all"
              >
                <Check className="w-4 h-4" />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="space-y-3">
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">대상 식별 유형</label>
                <div className="flex gap-3">
                  {(['email_pattern', 'email_list'] as const).map((type) => (
                    <button 
                      key={type}
                      className={`flex-1 px-4 py-3 rounded-xl border-2 transition-all text-xs font-bold flex items-center justify-center gap-2 ${
                        newRule.rule_type === type 
                          ? 'border-primary-600 bg-primary-50 text-primary-600 shadow-sm' 
                          : 'border-slate-200 bg-slate-50 text-slate-400 hover:border-slate-300'
                      }`}
                      onClick={() => setNewRule({...newRule, rule_type: type, rule_value: type === 'email_pattern' ? { pattern: '' } : { emails: [] }})}
                    >
                      {type === 'email_pattern' ? <Globe className="w-4 h-4" /> : <Layers className="w-4 h-4" />}
                      {type === 'email_pattern' ? 'Regex Pattern' : 'Email List'}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">
                  {newRule.rule_type === 'email_pattern' ? '이메일 정규식 패턴' : '이메일 목록 (콤마 구분)'}
                </label>
                <div className={`flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm ${newRule.rule_type === 'email_pattern' ? 'h-10 items-center' : 'min-h-[40px] items-start py-1.5'}`}>
                  {newRule.rule_type === 'email_pattern' ? <Globe className="w-4 h-4 text-primary-500 shrink-0" /> : <Layers className="w-4 h-4 text-primary-500 shrink-0 mt-1" />}
                  {newRule.rule_type === 'email_pattern' ? (
                    <input 
                      type="text"
                      className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                      value={newRule.rule_value.pattern}
                      onChange={(e) => setNewRule({...newRule, rule_value: { pattern: e.target.value }})}
                      placeholder=".*@gachon.ac.kr"
                    />
                  ) : (
                    <textarea 
                      className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0 min-h-[100px] resize-none py-1"
                      value={newRule.rule_value.emails?.join(',')}
                      onChange={(e) => {
                        const emails = e.target.value.split(',');
                        setNewRule({...newRule, rule_value: { emails }});
                      }}
                      placeholder="user1@example.com,user2@example.com"
                    />
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-3">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">할당할 역할</label>
                  <div className="flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm h-10 items-center">
                    <Shield className="w-4 h-4 text-primary-500 shrink-0" />
                    <input 
                      type="text"
                      className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                      value={newRule.assigned_role}
                      onChange={(e) => setNewRule({...newRule, assigned_role: e.target.value})}
                      placeholder="admin, user 등"
                    />
                  </div>
                </div>

                <div className="space-y-3">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">우선순위</label>
                  <div className="flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm h-10 items-center">
                    <ArrowUpDown className="w-4 h-4 text-primary-500 shrink-0" />
                    <input 
                      type="number"
                      className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                      value={newRule.priority}
                      onChange={(e) => setNewRule({...newRule, priority: parseInt(e.target.value)})}
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-xl">
                <div className="flex items-center gap-3">
                  <Shield className={`w-4 h-4 ${newRule.is_active ? 'text-primary-500' : 'text-slate-400'}`} />
                  <div>
                    <p className="text-[11px] font-bold text-slate-900">규칙 활성화</p>
                    <p className="text-[10px] text-slate-500">이 규칙을 즉시 적용합니다</p>
                  </div>
                </div>
                <input 
                  type="checkbox" 
                  className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                  checked={newRule.is_active}
                  onChange={(e) => setNewRule({...newRule, is_active: e.target.checked})}
                />
              </div>
            </div>

            <div className="p-5 bg-slate-50 flex justify-end gap-2 border-t border-slate-100">
              <button 
                onClick={() => setIsAdding(false)}
                className="px-4 py-1.5 text-xs font-bold text-slate-500 hover:text-slate-700 transition-colors"
              >
                취소
              </button>
              <button 
                onClick={handleCreate}
                className="px-6 py-1.5 bg-primary-600 text-white text-xs font-bold rounded-lg shadow-md shadow-primary-50 hover:bg-primary-700 transition-all flex items-center gap-2"
              >
                <Check className="w-3.5 h-3.5" /> 규칙 생성
              </button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
