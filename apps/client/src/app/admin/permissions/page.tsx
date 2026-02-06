'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card } from '@/components/Card';
import { Badge } from '@/components/Badge';
import { Key, Plus, Trash2, Edit2, Globe, Lock, Shield, Check, X, Search, Loader2 } from 'lucide-react';

interface RoutePermission {
  id: number;
  path: string;
  method: string;
  is_public: boolean;
  roles: string[];
}

export default function PermissionsPage() {
  const [permissions, setPermissions] = useState<RoutePermission[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingPerm, setEditingPerm] = useState<RoutePermission | null>(null);
  const [rolesInput, setRolesInput] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [newPermission, setNewPermission] = useState<Partial<RoutePermission>>({
    path: '',
    method: 'GET',
    is_public: false,
    roles: []
  });

  const fetchPermissions = async () => {
    try {
      const data = await api.get<RoutePermission[]>('/admin/permissions');
      setPermissions(data);
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPermissions();
  }, []);

  const handleCreate = async () => {
    try {
      if (!newPermission.path || !newPermission.method) return;
      await api.post('/admin/permissions', newPermission);
      setNewPermission({ path: '', method: 'GET', is_public: false, roles: [] });
      setIsAdding(false);
      fetchPermissions();
    } catch (error) {
      alert('생성에 실패했습니다.');
    }
  };

  const handleUpdate = async () => {
    if (!editingPerm) return;
    try {
      const roles = rolesInput.split(',').map(s => s.trim()).filter(Boolean);
      await api.put(`/admin/permissions/${editingPerm.id}`, { 
        roles: roles, 
        is_public: editingPerm.is_public 
      });
      setEditingPerm(null);
      setRolesInput('');
      fetchPermissions();
    } catch (error) {
      alert('수정에 실패했습니다.');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/admin/permissions/${id}`);
      fetchPermissions();
    } catch (error) {
      alert('삭제에 실패했습니다.');
    }
  };

  const getMethodColor = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case 'POST': return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'PUT': return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'DELETE': return 'bg-rose-100 text-rose-700 border-rose-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const filteredPermissions = permissions.filter(p => 
    p.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.method.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
      <p className="text-slate-500 font-medium">권한 목록을 불러오는 중...</p>
    </div>
  );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 tracking-tight mb-0">권한 관리</h2>
        <button 
          onClick={() => setIsAdding(true)}
          className="px-4 py-2 bg-primary-600 text-white text-sm font-bold rounded-lg shadow-md shadow-primary-50 hover:bg-primary-700 transition-all flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> 신규 권한 추가
        </button>
      </div>

      <div className="bg-white border border-slate-100 shadow-sm rounded-xl overflow-hidden focus-within:border-primary-400 transition-all">
        <div className="flex items-center px-4 gap-3 h-10">
          <Search className="w-4 h-4 text-slate-300 shrink-0" />
          <input 
            type="text"
            placeholder="경로 또는 메소드로 검색..."
            className="w-full bg-transparent outline-none font-medium text-[14px] text-slate-600 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {filteredPermissions.length > 0 ? (
          filteredPermissions.map((perm) => (
            <div key={perm.id} className="w-full">
              <Card 
                padding="none" 
                className={`w-full border border-slate-100 transition-all group overflow-hidden ${editingPerm?.id === perm.id ? 'rounded-b-none border-b-0 shadow-none ring-1 ring-primary-100 relative z-10' : 'hover:border-primary-100'}`}
              >
                <div className="flex items-center justify-between px-4 py-2.5 bg-white">
                  <div className="flex items-center gap-3">
                    <div>
                      <h6 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                        <span className={`text-[8px] font-black px-1.5 py-0.5 rounded border uppercase ${getMethodColor(perm.method)}`}>
                          {perm.method}
                        </span>
                        <code className="font-mono text-[13px]">{perm.path}</code>
                      </h6>
                      <div className="flex items-center gap-3 mt-0">
                        {perm.is_public ? (
                          <div className="flex items-center gap-1 text-[11px] text-amber-600 font-medium whitespace-nowrap">
                            <Globe className="w-3 h-3" /> 전체 공개
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium whitespace-nowrap">
                            <Shield className="w-3 h-3 text-slate-400" /> 
                            {perm.roles.length > 0 ? perm.roles.join(', ') : '역할 없음'}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
                    <button 
                      onClick={() => {
                        if (editingPerm?.id === perm.id) {
                          setEditingPerm(null);
                          setRolesInput('');
                        } else {
                          setEditingPerm(perm);
                          setRolesInput(perm.roles.join(', '));
                        }
                      }}
                      className={`p-1.5 rounded-md transition-all ${editingPerm?.id === perm.id ? 'bg-primary-500 text-white shadow-sm' : 'text-slate-400 hover:text-primary-600 hover:bg-primary-50'}`}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button 
                      onClick={() => handleDelete(perm.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-all"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </Card>

              {/* Inline Edit Area */}
              {editingPerm?.id === perm.id && (
                <div className="w-full animate-in slide-in-from-top-1 duration-200">
                  <div className="bg-slate-50/40 border-x border-primary-100 border-b border-primary-100 rounded-b-xl border-t-0 p-5 space-y-6 ring-1 ring-primary-100 ring-t-0 relative z-0">
                    <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-xl">
                      <div className="flex items-center gap-3">
                        <Globe className={`w-4 h-4 ${editingPerm.is_public ? 'text-amber-500' : 'text-slate-400'}`} />
                        <div>
                          <p className="text-[11px] font-bold text-slate-900">공개 경로 (Public)</p>
                          <p className="text-[10px] text-slate-500">누구나 인증 없이 접근 가능</p>
                        </div>
                      </div>
                      <input 
                        type="checkbox" 
                        className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                        checked={editingPerm.is_public}
                        onChange={(e) => setEditingPerm({...editingPerm, is_public: e.target.checked})}
                      />
                    </div>

                    {!editingPerm.is_public && (
                      <div className="space-y-3">
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">허용 역할 (콤마 구분)</label>
                        <div className="flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm h-10 items-center">
                          <Shield className="w-4 h-4 text-primary-500 shrink-0" />
                          <input 
                            type="text"
                            className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                            value={rolesInput}
                            onChange={(e) => setRolesInput(e.target.value)}
                            placeholder="admin, user 등"
                          />
                        </div>
                      </div>
                    )}

                    <div className="flex justify-end gap-2 pt-5 border-t border-slate-100/60">
                      <button 
                        onClick={() => setEditingPerm(null)}
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
            <Search className="w-10 h-10 text-slate-200 mx-auto mb-4" />
            <p className="text-sm text-slate-400 font-medium">검색된 권한이 없습니다.</p>
          </div>
        )}
      </div>

      {/* Add New Permission Modal */}
      {isAdding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 animate-in fade-in duration-200">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setIsAdding(false)} />
          <Card className="w-full max-w-lg relative z-10 shadow-2xl p-0 overflow-hidden rounded-2xl border-none">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h3 className="text-lg font-bold text-slate-900">새 권한 추가</h3>
              <button 
                onClick={() => setIsAdding(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-1 space-y-3">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">Method</label>
                  <select 
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl focus:border-primary-400 outline-none transition-all font-semibold text-[13px] text-slate-700 h-10"
                    value={newPermission.method}
                    onChange={(e) => setNewPermission({...newPermission, method: e.target.value})}
                  >
                    <option>GET</option>
                    <option>POST</option>
                    <option>PUT</option>
                    <option>DELETE</option>
                  </select>
                </div>
                <div className="col-span-2 space-y-3">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">API 경로</label>
                  <div className="flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm h-10 items-center">
                    <Key className="w-4 h-4 text-primary-500 shrink-0" />
                    <input 
                      type="text"
                      className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                      value={newPermission.path}
                      onChange={(e) => setNewPermission({...newPermission, path: e.target.value})}
                      placeholder="/api/v1/..."
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-xl">
                <div className="flex items-center gap-3">
                  <Globe className={`w-4 h-4 ${newPermission.is_public ? 'text-amber-500' : 'text-slate-400'}`} />
                  <div>
                    <p className="text-[11px] font-bold text-slate-900">공개 경로 (Public)</p>
                    <p className="text-[10px] text-slate-500">누구나 인증 없이 접근 가능</p>
                  </div>
                </div>
                <input 
                  type="checkbox" 
                  className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                  checked={newPermission.is_public}
                  onChange={(e) => setNewPermission({...newPermission, is_public: e.target.checked})}
                />
              </div>

              {!newPermission.is_public && (
                <div className="space-y-3">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">허용 역할 (콤마 구분)</label>
                  <div className="flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm h-10 items-center">
                    <Shield className="w-4 h-4 text-primary-500 shrink-0" />
                    <input 
                      type="text"
                      className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                      value={newPermission.roles?.join(', ')}
                      onChange={(e) => {
                        const roles = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
                        setNewPermission({...newPermission, roles});
                      }}
                      placeholder="admin, user 등"
                    />
                  </div>
                </div>
              )}
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
                <Check className="w-3.5 h-3.5" /> 권한 생성
              </button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
