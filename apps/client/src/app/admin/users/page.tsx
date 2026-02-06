'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { Input } from '@/components/Input';
import { Users, Search, Edit2, Trash2, Mail, Calendar, Shield, X, Check, User as UserIcon, UserMinus, Loader2 } from 'lucide-react';

interface User {
  id: number;
  google_sub: string;
  email: string;
  name: string | null;
  picture: string | null;
  roles: string[];
  created_at: string;
  consents: any[];
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [rolesInput, setRolesInput] = useState('');

  const fetchUsers = async () => {
    try {
      const data = await api.get<User[]>('/admin/users');
      setUsers(data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleUpdate = async () => {
    if (!editingUser) return;
    try {
      // rolesInput 문자열을 배열로 변환
      const roles = rolesInput.split(',').map(s => s.trim()).filter(Boolean);
      await api.put(`/admin/users/${editingUser.id}`, {
        name: editingUser.name,
        roles: roles
      });
      setEditingUser(null);
      setRolesInput('');
      fetchUsers();
    } catch (error) {
      alert('사용자 정보 수정에 실패했습니다.');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('정말 이 사용자를 삭제하시겠습니까? 관련 모든 데이터가 삭제됩니다.')) return;
    try {
      await api.delete(`/admin/users/${id}`);
      fetchUsers();
    } catch (error) {
      alert('사용자 삭제에 실패했습니다.');
    }
  };

  const filteredUsers = users.filter(u => 
    u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (u.name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
      <p className="text-slate-500 font-medium">사용자 목록을 불러오는 중...</p>
    </div>
  );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight mb-0">사용자 관리</h2>
        </div>
      </div>

      <div 
        className="bg-white border border-slate-100 shadow-sm flex items-center px-4 gap-3 h-10 group focus-within:border-primary-400 transition-all" 
        style={{ borderRadius: '10px' }}
      >
        <Search className="w-4 h-4 text-slate-300 group-focus-within:text-primary-500 transition-colors shrink-0" />
        <input 
          type="text"
          placeholder="이름 또는 이메일로 검색..."
          className="w-full bg-transparent outline-none font-medium text-slate-600 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
          style={{ 
            fontSize: '14px',
            appearance: 'none',
            border: 'none',
            boxShadow: 'none',
            paddingLeft: '0px'
          }}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-1 gap-2">
        {filteredUsers.length > 0 ? (
          filteredUsers.map((user) => (
            <div key={user.id} className="w-full">
              <Card 
                padding="none" 
                className={`w-full border border-slate-100 transition-all group overflow-hidden ${editingUser?.id === user.id ? 'rounded-b-none border-b-0 shadow-none ring-1 ring-primary-100 relative z-10' : 'hover:border-primary-100'}`}
              >
                <div className="flex items-center justify-between px-4 py-2.5 bg-white">
                  <div className="flex items-center gap-3">
                    {user.picture ? (
                      <img src={user.picture} alt={user.name || ''} className="w-10 h-10 rounded-full object-cover border border-slate-50" />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-slate-50 flex items-center justify-center border border-slate-50">
                        <UserIcon className="w-5.5 h-5.5 text-slate-400" />
                      </div>
                    )}
                    <div>
                      <h6 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                        {user.name || '이름 없음'}
                        <div className="flex gap-1">
                          {user.roles.map(role => (
                            <Badge key={role} variant={role === 'admin' ? 'accent' : 'primary'} size="sm" className="px-1.5 py-0 font-bold text-[8px] uppercase">
                              {role}
                            </Badge>
                          ))}
                        </div>
                      </h6>
                      <div className="flex items-center gap-3 mt-0">
                        <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium whitespace-nowrap">
                          <Mail className="w-3 h-3 text-slate-400" /> {user.email}
                        </div>
                        <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium whitespace-nowrap">
                          <Calendar className="w-3 h-3 text-slate-400" /> {new Date(user.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
                    <button 
                      onClick={() => {
                        if (editingUser?.id === user.id) {
                          setEditingUser(null);
                          setRolesInput('');
                        } else {
                          setEditingUser(user);
                          setRolesInput(user.roles.join(', '));
                        }
                      }}
                      className={`p-1.5 rounded-md transition-all ${editingUser?.id === user.id ? 'bg-primary-500 text-white shadow-sm' : 'text-slate-400 hover:text-primary-600 hover:bg-primary-50'}`}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button 
                      onClick={() => handleDelete(user.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-all"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </Card>

              {/* Inline Edit Area */}
              {editingUser?.id === user.id && (
                <div className="w-full animate-in slide-in-from-top-1 duration-200">
                  <div className="bg-slate-50/40 border-x border-primary-100 border-b border-primary-100 rounded-b-xl border-t-0 p-5 space-y-6 ring-1 ring-primary-100 ring-t-0 relative z-0">
                    <div className="space-y-3">
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">부여된 역할 (콤마 구분)</label>
                      <div className="flex gap-3 px-4 bg-white border border-slate-200 rounded-xl focus-within:border-primary-400 transition-all shadow-sm h-10 items-center">
                        <Shield className="w-4 h-4 text-primary-500 shrink-0" />
                        <input 
                          type="text"
                          className="w-full bg-transparent outline-none font-semibold text-[13px] text-slate-700 placeholder:text-slate-300 border-none ring-0 focus:ring-0"
                          value={rolesInput}
                          onChange={(e) => setRolesInput(e.target.value)}
                          placeholder="admin, user 등 역할 입력"
                        />
                      </div>
                    </div>

                    <div className="flex justify-end gap-2 pt-5 border-t border-slate-100/60">
                      <button 
                        onClick={() => setEditingUser(null)}
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
            <UserMinus className="w-10 h-10 text-slate-200 mx-auto mb-4" />
            <p className="text-sm text-slate-400 font-medium">검색된 사용자가 없습니다.</p>
          </div>
        )}
      </div>
    </div>
  );
}
