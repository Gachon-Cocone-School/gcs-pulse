"use client";

import { useEffect, useReducer } from "react";
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
import { v4 as uuidv4 } from "uuid";

type State = {
  tokens: APIToken[];
  loading: boolean;
  isCreateDialogOpen: boolean;
  description: string;
  newToken: string | null;
  copied: boolean;
};

type Action =
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_TOKENS"; payload: APIToken[] }
  | { type: "SET_CREATE_DIALOG_OPEN"; payload: boolean }
  | { type: "SET_DESCRIPTION"; payload: string }
  | { type: "ADD_CREATED_TOKEN"; payload: APITokenCreateResponse }
  | { type: "DELETE_TOKEN"; payload: string }
  | { type: "SET_NEW_TOKEN"; payload: string | null }
  | { type: "SET_COPIED"; payload: boolean }
  | { type: "CLOSE_DIALOG" };

const initialState: State = {
  tokens: [],
  loading: true,
  isCreateDialogOpen: false,
  description: "",
  newToken: null,
  copied: false,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_LOADING":
      return { ...state, loading: action.payload };
    case "SET_TOKENS":
      return { ...state, tokens: action.payload };
    case "SET_CREATE_DIALOG_OPEN":
      return { ...state, isCreateDialogOpen: action.payload };
    case "SET_DESCRIPTION":
      return { ...state, description: action.payload };
    case "ADD_CREATED_TOKEN":
      return {
        ...state,
        newToken: action.payload.token,
        tokens: [action.payload, ...state.tokens],
        description: "",
      };
    case "DELETE_TOKEN":
      return { ...state, tokens: state.tokens.filter((t) => t.id !== action.payload) };
    case "SET_NEW_TOKEN":
      return { ...state, newToken: action.payload };
    case "SET_COPIED":
      return { ...state, copied: action.payload };
    case "CLOSE_DIALOG":
      return {
        ...state,
        isCreateDialogOpen: false,
        newToken: null,
        copied: false,
      };
    default:
      return state;
  }
}

export function TokenManager() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const fetchTokens = async () => {
    try {
      dispatch({ type: "SET_LOADING", payload: true });
      const data = await api.get<APIToken[]>("/auth/tokens");
      dispatch({ type: "SET_TOKENS", payload: data });
    } catch (error) {
      console.error("Failed to fetch tokens", error);
    } finally {
      dispatch({ type: "SET_LOADING", payload: false });
    }
  };

  useEffect(() => {
    fetchTokens();
  }, []);

  const handleCreateToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!state.description.trim()) return;

    try {
      const idempotencyKey = uuidv4();
      const result = await api.post<APITokenCreateResponse>(
        "/auth/tokens",
        {
          description: state.description,
        },
        {
          headers: {
            "Idempotency-Key": idempotencyKey,
          },
        }
      );

      dispatch({ type: "ADD_CREATED_TOKEN", payload: result });
      toast.success("토큰이 생성되었습니다");
    } catch (error) {
      const status = (error as any)?.status;
      if (status === 0) {
        toast.error("네트워크 오류: 백엔드가 실행 중인지 확인해 주세요");
      } else {
        toast.error("토큰 생성에 실패했습니다");
      }

      console.debug("Token create failed", { message: (error as any)?.message, status });
    }
  };

  const handleDeleteToken = async (id: string) => {
    if (!confirm("이 토큰을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) {
      return;
    }

    try {
      await api.delete(`/auth/tokens/${id}`);
      dispatch({ type: "DELETE_TOKEN", payload: id });
      toast.success("토큰이 삭제되었습니다");
    } catch (error) {
      console.error("Failed to delete token", error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    dispatch({ type: "SET_COPIED", payload: true });
    toast.success("클립보드에 복사되었습니다");
    setTimeout(() => dispatch({ type: "SET_COPIED", payload: false }), 2000);
  };

  const closeDialog = () => {
    dispatch({ type: "CLOSE_DIALOG" });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">API 토큰</h2>
          <p className="text-muted-foreground">
            API에 접근하기 위한 개인 액세스 토큰을 안전하게 관리하세요.
          </p>
        </div>
        <Dialog
          open={state.isCreateDialogOpen}
          onOpenChange={(open) => dispatch({ type: "SET_CREATE_DIALOG_OPEN", payload: open })}
        >
          <DialogTrigger asChild>
            <Button
              className="shadow-sm transition-all active:scale-95"
              onClick={() => dispatch({ type: "SET_CREATE_DIALOG_OPEN", payload: true })}
            >
              <Plus className="mr-2 h-4 w-4" />
              새 토큰 생성
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md rounded-xl border-white/40 bg-card/75 backdrop-blur-md">
            {state.newToken ? (
              <>
                <DialogHeader>
                  <DialogTitle className="text-xl font-bold text-foreground">토큰이 성공적으로 생성되었습니다</DialogTitle>
                  <DialogDescription className="text-destructive font-medium bg-destructive/10 p-3 rounded-md border border-destructive/20 mt-2">
                    보안을 위해 이 토큰은 다시 표시되지 않습니다. 지금 복사하여 안전한 곳에 저장하세요.
                  </DialogDescription>
                </DialogHeader>
                <div className="mt-4 flex items-center space-x-2 rounded-lg border border-border bg-muted p-4 transition-all focus-within:ring-2 focus-within:ring-ring/20">
                  <code className="flex-1 break-all text-sm font-mono font-bold text-foreground selection:bg-primary/20">
                    {state.newToken}
                  </code>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="shrink-0 hover:bg-card hover:text-primary transition-colors"
                    onClick={() => copyToClipboard(state.newToken!)}
                  >
                    {state.copied ? (
                      <Check className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <DialogFooter className="mt-6">
                  <Button className="w-full bg-foreground hover:bg-foreground/90 text-background" onClick={closeDialog}>
                    완료 및 닫기
                  </Button>
                </DialogFooter>
              </>
            ) : (
              <form onSubmit={handleCreateToken}>
                <DialogHeader>
                  <DialogTitle className="text-xl font-bold text-foreground">새 API 토큰 생성</DialogTitle>
                  <DialogDescription className="text-muted-foreground">
                    토큰의 용도를 식별할 수 있는 간단한 설명을 입력해 주세요.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-6">
                  <div className="grid gap-2">
                    <Label htmlFor="description" className="text-sm font-semibold text-foreground">설명</Label>
                    <Input
                      id="description"
                      placeholder="예: 개발 서버용, CI/CD 배포"
                      className="h-10 border-border focus:border-ring focus:ring-ring/20 rounded-md transition-all"
                      value={state.description}
                      onChange={(e) => dispatch({ type: "SET_DESCRIPTION", payload: e.target.value })}
                      required
                    />
                  </div>
                </div>
                <DialogFooter className="gap-2 sm:gap-0">
                  <Button
                    type="button"
                    variant="ghost"
                    className="hover:bg-muted text-muted-foreground"
                    onClick={() => dispatch({ type: "SET_CREATE_DIALOG_OPEN", payload: false })}
                  >
                    취소
                  </Button>
                  <Button type="submit" className="bg-primary hover:bg-primary/90 text-primary-foreground px-8">생성하기</Button>
                </DialogFooter>
              </form>
            )}
          </DialogContent>
        </Dialog>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card/70 shadow-sm transition-all hover:shadow-md">
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow className="hover:bg-transparent border-border">
              <TableHead className="font-semibold text-foreground py-4">설명</TableHead>
              <TableHead className="font-semibold text-foreground">생성일</TableHead>
              <TableHead className="font-semibold text-foreground">마지막 사용</TableHead>
              <TableHead className="w-[100px] text-right font-semibold text-foreground">관리</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {state.loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i} className="border-border/70">
                  <TableCell className="py-4"><Skeleton className="h-5 w-[200px] rounded-full" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-[120px] rounded-full" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-[140px] rounded-full" /></TableCell>
                  <TableCell className="text-right"><Skeleton className="ml-auto h-8 w-8 rounded-md" /></TableCell>
                </TableRow>
              ))
            ) : state.tokens.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="h-40 text-center">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <div className="rounded-full bg-muted p-3">
                      <Plus className="h-6 w-6 text-muted-foreground" />
                    </div>
                    <p className="text-muted-foreground font-medium">생성된 API 토큰이 없습니다</p>
                    <p className="text-muted-foreground text-sm">새 토큰을 생성하여 API 연동을 시작하세요</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              state.tokens.map((token) => (
                <TableRow key={token.id} className="group hover:bg-destructive/10 transition-colors border-border/70">
                  <TableCell className="font-semibold text-foreground py-4">
                    {token.description}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(token.created_at).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {token.last_used_at
                      ? new Date(token.last_used_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })
                      : <span className="text-muted-foreground italic text-xs">사용 기록 없음</span>}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-primary/20 transition-all rounded-md opacity-0 group-hover:opacity-100"
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
