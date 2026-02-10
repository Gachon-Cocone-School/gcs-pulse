"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { APIToken, APITokenCreateResponse } from "@/lib/types/auth";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Trash2, Plus, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";

export function TokenManager() {
  const [tokens, setTokens] = useState<APIToken[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [description, setDescription] = useState("");
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchTokens = async () => {
    try {
      setLoading(true);
      const data = await api.get<APIToken[]>("/auth/tokens");
      setTokens(data);
    } catch (error) {
      console.error("Failed to fetch tokens", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTokens();
  }, []);

  const handleCreateToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;

    try {
      const result = await api.post<APITokenCreateResponse>("/auth/tokens", {
        description,
      });
      setNewToken(result.token);
      setTokens((prev) => [result, ...prev]);
      setDescription("");
      toast.success("토큰이 생성되었습니다");
    } catch (error) {
      // 사용자용 메시지: 네트워크 에러(상태 0)와 기타 서버 에러를 구분하여 표시
      const status = (error as any)?.status;
      if (status === 0) {
        toast.error('네트워크 오류: 백엔드가 실행 중인지 확인해 주세요');
      } else {
        toast.error('토큰 생성에 실패했습니다');
      }

      // 디버깅용 최소 정보만 출력(스택을 그대로 노출하지 않음)
      console.debug('Token create failed', { message: (error as any)?.message, status });
    }
  };

  const handleDeleteToken = async (id: string) => {
    if (!confirm("이 토큰을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) {
      return;
    }

    try {
      await api.delete(`/auth/tokens/${id}`);
      setTokens((prev) => prev.filter((t) => t.id !== id));
      toast.success("토큰이 삭제되었습니다");
    } catch (error) {
      console.error("Failed to delete token", error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("클립보드에 복사되었습니다");
    setTimeout(() => setCopied(false), 2000);
  };

  const closeDialog = () => {
    setIsCreateDialogOpen(false);
    setNewToken(null);
    setCopied(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">API 액세스 토큰</h2>
          <p className="text-slate-600">
            API에 접근하기 위한 개인 액세스 토큰을 안전하게 관리하세요.
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-rose-500 hover:bg-rose-600 text-white shadow-sm transition-all active:scale-95" onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              새 토큰 생성
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md rounded-xl border-white/40 bg-white/95 backdrop-blur-xl">
            {newToken ? (
              <>
                <DialogHeader>
                  <DialogTitle className="text-xl font-bold text-slate-900">토큰이 성공적으로 생성되었습니다</DialogTitle>
                  <DialogDescription className="text-rose-600 font-medium bg-rose-50 p-3 rounded-md border border-rose-100 mt-2">
                    보안을 위해 이 토큰은 다시 표시되지 않습니다. 지금 복사하여 안전한 곳에 저장하세요.
                  </DialogDescription>
                </DialogHeader>
                <div className="mt-4 flex items-center space-x-2 rounded-lg border border-slate-200 bg-slate-50 p-4 transition-all focus-within:ring-2 focus-within:ring-rose-500/20">
                  <code className="flex-1 break-all text-sm font-mono font-bold text-slate-800 selection:bg-rose-100">
                    {newToken}
                  </code>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="shrink-0 hover:bg-white hover:text-rose-500 transition-colors"
                    onClick={() => copyToClipboard(newToken)}
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <DialogFooter className="mt-6">
                  <Button className="w-full bg-slate-900 hover:bg-slate-800 text-white" onClick={closeDialog}>
                    완료 및 닫기
                  </Button>
                </DialogFooter>
              </>
            ) : (
              <form onSubmit={handleCreateToken}>
                <DialogHeader>
                  <DialogTitle className="text-xl font-bold text-slate-900">새 API 토큰 생성</DialogTitle>
                  <DialogDescription className="text-slate-500">
                    토큰의 용도를 식별할 수 있는 간단한 설명을 입력해 주세요.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-6">
                  <div className="grid gap-2">
                    <Label htmlFor="description" className="text-sm font-semibold text-slate-700">설명</Label>
                    <Input
                      id="description"
                      placeholder="예: 개발 서버용, CI/CD 배포"
                      className="h-10 border-slate-200 focus:border-rose-500 focus:ring-rose-500/20 rounded-md transition-all"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      required
                      autoFocus
                    />
                  </div>
                </div>
                <DialogFooter className="gap-2 sm:gap-0">
                  <Button
                    type="button"
                    variant="ghost"
                    className="hover:bg-slate-100 text-slate-600"
                    onClick={() => setIsCreateDialogOpen(false)}
                  >
                    취소
                  </Button>
                  <Button type="submit" className="bg-rose-500 hover:bg-rose-600 text-white px-8">생성하기</Button>
                </DialogFooter>
              </form>
            )}
          </DialogContent>
        </Dialog>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white/50 shadow-sm transition-all hover:shadow-md">
        <Table>
          <TableHeader className="bg-slate-50/50">
            <TableRow className="hover:bg-transparent border-slate-200">
              <TableHead className="font-semibold text-slate-700 py-4">설명</TableHead>
              <TableHead className="font-semibold text-slate-700">생성일</TableHead>
              <TableHead className="font-semibold text-slate-700">마지막 사용</TableHead>
              <TableHead className="w-[100px] text-right font-semibold text-slate-700">관리</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i} className="border-slate-100">
                  <TableCell className="py-4"><Skeleton className="h-5 w-[200px] rounded-full" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-[120px] rounded-full" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-[140px] rounded-full" /></TableCell>
                  <TableCell className="text-right"><Skeleton className="ml-auto h-8 w-8 rounded-md" /></TableCell>
                </TableRow>
              ))
            ) : tokens.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="h-40 text-center">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <div className="rounded-full bg-slate-100 p-3">
                      <Plus className="h-6 w-6 text-slate-400" />
                    </div>
                    <p className="text-slate-500 font-medium">생성된 API 토큰이 없습니다</p>
                    <p className="text-slate-400 text-sm">새 토큰을 생성하여 API 연동을 시작하세요</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              tokens.map((token) => (
                <TableRow key={token.id} className="group hover:bg-rose-50/30 transition-colors border-slate-100">
                  <TableCell className="font-semibold text-slate-800 py-4">
                    {token.description}
                  </TableCell>
                  <TableCell className="text-slate-600">
                    {new Date(token.created_at).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </TableCell>
                  <TableCell className="text-slate-600">
                    {token.last_used_at
                      ? new Date(token.last_used_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })
                      : <span className="text-slate-400 italic text-xs">사용 기록 없음</span>}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-slate-400 hover:text-rose-600 hover:bg-rose-100/50 transition-all rounded-md opacity-0 group-hover:opacity-100"
                      onClick={() => handleDeleteToken(token.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
