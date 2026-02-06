'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card } from '@/components/Card';
import { Badge } from '@/components/Badge';
import { FileText, Plus, Edit2, Trash2, Check, X, AlertCircle, Calendar, Search, ToggleLeft, ToggleRight, Loader2 } from 'lucide-react';

interface Term {
  id: number;
  type: string;
  version: string;
  content: string;
  is_required: boolean;
  is_active: boolean;
  created_at: string;
}

export default function TermsPage() {
  const [terms, setTerms] = useState<Term[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [editingTerm, setEditingTerm] = useState<Term | null>(null);
  const [formData, setFormData] = useState({
    type: 'service_terms',
    version: '1.0.0',
    content: '',
    is_required: true,
    is_active: true
  });

  const fetchTerms = async () => {
    try {
      const data = await api.get<Term[]>('/admin/terms');
      setTerms(data);
    } catch (error) {
      console.error('Failed to fetch terms:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTerms();
  }, []);

  const handleSubmit = async () => {
    try {
      if (editingTerm) {
        await api.put(`/admin/terms/${editingTerm.id}`, {
          content: formData.content,
          is_required: formData.is_required,
          is_active: formData.is_active
        });
      } else {
        await api.post('/admin/terms', formData);
      }
      setIsAdding(false);
      setEditingTerm(null);
      resetForm();
      fetchTerms();
    } catch (error: any) {
      alert(error.response?.data?.detail || '작업에 실패했습니다.');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('정말 이 약관을 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/admin/terms/${id}`);
      fetchTerms();
    } catch (error) {
      alert('약관 삭제에 실패했습니다.');
    }
  };

  const resetForm = () => {
    setFormData({
      type: 'service_terms',
      version: '1.0.0',
      content: '',
      is_required: true,
      is_active: true
    });
  };

  const filteredTerms = terms.filter(t => 
    t.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.version.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
      <p className="text-slate-500 font-medium">약관 데이터를 불러오는 중...</p>
    </div>
  );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 tracking-tight mb-0">약관 관리</h2>
        <button 
          onClick={() => { resetForm(); setIsAdding(true); setEditingTerm(null); }}
          className="px-4 py-2 bg-primary-600 text-white text-sm font-bold rounded-lg shadow-md shadow-primary-50 hover:bg-primary-700 transition-all flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> 새 약관 등록
        </button>
      </div>

      <div className="bg-white border border-slate-100 shadow-sm rounded-xl overflow-hidden focus-within:border-primary-400 transition-all">
        <div className="flex items-center px-4 gap-3 h-10">
          <Search className="w-4 h-4 text-slate-300 shrink-0" />
          <input 
            type="text"
            placeholder="약관 타입 또는 버전으로 검색..."
            className="w-full bg-transparent outline-none font-medium text-[14px] text-slate-600 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {filteredTerms.length > 0 ? (
          filteredTerms.map((term) => (
            <div key={term.id} className="w-full">
              <Card 
                padding="none" 
                className={`w-full border border-slate-100 transition-all group overflow-hidden ${editingTerm?.id === term.id ? 'rounded-b-none border-b-0 shadow-none ring-1 ring-primary-100 relative z-10' : 'hover:border-primary-100'}`}
              >
                <div className="flex items-center justify-between px-4 py-2.5 bg-white">
                  <div className="flex items-center gap-3">
                    <div>
                      <h6 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                        <span className="uppercase">{term.type.replace('_', ' ')}</span>
                        <div className="flex gap-1">
                          <Badge variant="neutral" size="sm" className="px-1.5 py-0 font-bold text-[8px]">
                            v{term.version}
                          </Badge>
                          {term.is_required && (
                            <Badge variant="accent" size="sm" className="px-1.5 py-0 font-bold text-[8px]">
                              필수
                            </Badge>
                          )}
                          {term.is_active ? (
                            <Badge variant="primary" size="sm" className="px-1.5 py-0 font-bold text-[8px] bg-emerald-500 text-white">
                              활성
                            </Badge>
                          ) : (
                            <Badge variant="neutral" size="sm" className="px-1.5 py-0 font-bold text-[8px]">
                              비활성
                            </Badge>
                          )}
                        </div>
                      </h6>
                      <div className="flex items-center gap-3 mt-0">
                        <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium whitespace-nowrap">
                          <FileText className="w-3 h-3 text-slate-400" /> {term.content.substring(0, 50)}...
                        </div>
                        <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium whitespace-nowrap">
                          <Calendar className="w-3 h-3 text-slate-400" /> {new Date(term.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
                    <button 
                      onClick={() => {
                        if (editingTerm?.id === term.id) {
                          setEditingTerm(null);
                        } else {
                          setEditingTerm(term);
                          setFormData({
                            type: term.type,
                            version: term.version,
                            content: term.content,
                            is_required: term.is_required,
                            is_active: term.is_active
                          });
                        }
                      }}
                      className={`p-1.5 rounded-md transition-all ${editingTerm?.id === term.id ? 'bg-primary-500 text-white shadow-sm' : 'text-slate-400 hover:text-primary-600 hover:bg-primary-50'}`}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button 
                      onClick={() => handleDelete(term.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-all"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </Card>

              {/* Inline Edit Area */}
              {editingTerm?.id === term.id && (
                <div className="w-full animate-in slide-in-from-top-1 duration-200">
                  <div className="bg-slate-50/40 border-x border-primary-100 border-b border-primary-100 rounded-b-xl border-t-0 p-5 space-y-6 ring-1 ring-primary-100 ring-t-0 relative z-0">
                    <div className="space-y-3">
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">약관 내용</label>
                      <textarea 
                        className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:border-primary-400 outline-none transition-all font-medium text-[13px] text-slate-700 placeholder:text-slate-300 min-h-[120px] resize-none"
                        value={formData.content}
                        onChange={(e) => setFormData({...formData, content: e.target.value})}
                        placeholder="약관의 상세 내용을 입력하세요..."
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-xl cursor-pointer" onClick={() => setFormData({...formData, is_required: !formData.is_required})}>
                        <div className="flex items-center gap-2">
                          <AlertCircle className={`w-4 h-4 ${formData.is_required ? 'text-rose-500' : 'text-slate-400'}`} />
                          <span className="text-[11px] font-bold text-slate-900">필수 동의</span>
                        </div>
                        {formData.is_required ? <ToggleRight className="w-6 h-6 text-primary-600" /> : <ToggleLeft className="w-6 h-6 text-slate-300" />}
                      </div>

                      <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-xl cursor-pointer" onClick={() => setFormData({...formData, is_active: !formData.is_active})}>
                        <div className="flex items-center gap-2">
                          <Check className={`w-4 h-4 ${formData.is_active ? 'text-emerald-500' : 'text-slate-400'}`} />
                          <span className="text-[11px] font-bold text-slate-900">활성화</span>
                        </div>
                        {formData.is_active ? <ToggleRight className="w-6 h-6 text-emerald-500" /> : <ToggleLeft className="w-6 h-6 text-slate-300" />}
                      </div>
                    </div>

                    <div className="flex justify-end gap-2 pt-5 border-t border-slate-100/60">
                      <button 
                        onClick={() => setEditingTerm(null)}
                        className="px-4 py-1.5 text-xs font-bold text-slate-500 hover:text-slate-700 transition-colors"
                      >
                        취소
                      </button>
                      <button 
                        onClick={handleSubmit}
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
            <FileText className="w-10 h-10 text-slate-200 mx-auto mb-4" />
            <p className="text-sm text-slate-400 font-medium">검색된 약관이 없습니다.</p>
          </div>
        )}
      </div>

      {/* Add New Term Modal */}
      {isAdding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 animate-in fade-in duration-200">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setIsAdding(false)} />
          <Card className="w-full max-w-2xl relative z-10 shadow-2xl p-0 overflow-hidden rounded-2xl border-none">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h3 className="text-lg font-bold text-slate-900">새 약관 등록</h3>
              <button 
                onClick={() => setIsAdding(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-3">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">약관 타입</label>
                  <select 
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl focus:border-primary-400 outline-none transition-all font-semibold text-[13px] text-slate-700 h-10"
                    value={formData.type}
                    onChange={(e) => setFormData({...formData, type: e.target.value})}
                  >
                    <option value="service_terms">이용약관</option>
                    <option value="privacy_policy">개인정보 처리방침</option>
                    <option value="marketing_consent">마케팅 수신동의</option>
                  </select>
                </div>
                <div className="space-y-3">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">버전</label>
                  <div className="flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm h-10 items-center">
                    <input 
                      type="text"
                      className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                      value={formData.version}
                      onChange={(e) => setFormData({...formData, version: e.target.value})}
                      placeholder="1.0.0"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">약관 내용</label>
                <textarea 
                  className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:border-primary-400 outline-none transition-all font-medium text-[13px] text-slate-700 placeholder:text-slate-300 min-h-[200px]"
                  value={formData.content}
                  onChange={(e) => setFormData({...formData, content: e.target.value})}
                  placeholder="약관의 상세 내용을 입력하세요..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-xl cursor-pointer" onClick={() => setFormData({...formData, is_required: !formData.is_required})}>
                  <div className="flex items-center gap-2">
                    <AlertCircle className={`w-4 h-4 ${formData.is_required ? 'text-rose-500' : 'text-slate-400'}`} />
                    <span className="text-[11px] font-bold text-slate-900">필수 동의</span>
                  </div>
                  {formData.is_required ? <ToggleRight className="w-6 h-6 text-primary-600" /> : <ToggleLeft className="w-6 h-6 text-slate-300" />}
                </div>

                <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-xl cursor-pointer" onClick={() => setFormData({...formData, is_active: !formData.is_active})}>
                  <div className="flex items-center gap-2">
                    <Check className={`w-4 h-4 ${formData.is_active ? 'text-emerald-500' : 'text-slate-400'}`} />
                    <span className="text-[11px] font-bold text-slate-900">활성화</span>
                  </div>
                  {formData.is_active ? <ToggleRight className="w-6 h-6 text-emerald-500" /> : <ToggleLeft className="w-6 h-6 text-slate-300" />}
                </div>
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
                onClick={handleSubmit}
                className="px-6 py-1.5 bg-primary-600 text-white text-xs font-bold rounded-lg shadow-md shadow-primary-50 hover:bg-primary-700 transition-all flex items-center gap-2"
              >
                <Check className="w-3.5 h-3.5" /> 약관 게시
              </button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
