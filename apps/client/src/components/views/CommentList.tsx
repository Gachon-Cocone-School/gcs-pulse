'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { api } from '@/lib/api';
import { useAuth } from '@/context/auth-context';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Trash2, Edit2, Send } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import type { Comment, CommentListProps } from '@/lib/types';

const EMPTY_COMMENTS: Comment[] = [];

const MarkdownRenderer = dynamic(() => import('./MarkdownRenderer'), {
  loading: () => <p className="text-sm text-slate-500">댓글을 불러오는 중입니다...</p>,
});

export function CommentList({ dailySnippetId, weeklySnippetId, initialComments, highlightCommentId }: CommentListProps) {
  const { user } = useAuth();
  const hasInitialComments = initialComments !== undefined;
  const [comments, setComments] = React.useState<Comment[]>(initialComments ?? EMPTY_COMMENTS);
  const [loading, setLoading] = React.useState(!hasInitialComments);
  const [submitting, setSubmitting] = React.useState(false);
  const [newComment, setNewComment] = React.useState('');
  const [editingId, setEditingId] = React.useState<number | null>(null);
  const [editContent, setEditContent] = React.useState('');
  const commentElementRefs = React.useRef<Record<number, HTMLDivElement | null>>({});
  const commentBodyElementRefs = React.useRef<Record<number, HTMLDivElement | null>>({});

  // defensive: ensure comments is an array and compute count
  const commentCount = Array.isArray(comments) ? comments.length : 0;

  const fetchComments = React.useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (dailySnippetId) params.append('daily_snippet_id', dailySnippetId.toString());
      if (weeklySnippetId) params.append('weekly_snippet_id', weeklySnippetId.toString());

      const res = await api.get<Comment[]>(`/comments?${params.toString()}`);
      setComments(res);
    } catch (err) {
      console.error('Failed to fetch comments', err);
    } finally {
      setLoading(false);
    }
  }, [dailySnippetId, weeklySnippetId]);

  React.useEffect(() => {
    if (!hasInitialComments) {
      fetchComments();
      return;
    }
    setLoading(false);
  }, [fetchComments, hasInitialComments]);

  React.useEffect(() => {
    if (!highlightCommentId) return;
    const target = commentElementRefs.current[highlightCommentId];
    const targetBody = commentBodyElementRefs.current[highlightCommentId];
    if (!target || !targetBody) return;

    target.scrollIntoView({ behavior: 'smooth', block: 'center' });

    const startTimer = window.setTimeout(() => {
      targetBody.classList.remove('comment-highlight-active');
      void targetBody.offsetWidth;
      targetBody.classList.add('comment-highlight-active');
    }, 250);

    const endTimer = window.setTimeout(() => {
      targetBody.classList.remove('comment-highlight-active');
    }, 3250);

    return () => {
      window.clearTimeout(startTimer);
      window.clearTimeout(endTimer);
    };
  }, [highlightCommentId, comments]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    try {
      setSubmitting(true);
      const created = await api.post<Comment>('/comments', {
        content: newComment,
        daily_snippet_id: dailySnippetId,
        weekly_snippet_id: weeklySnippetId,
      });
      setComments((prev) => [...prev, created]);
      setNewComment('');
    } catch (err) {
      console.error('Failed to post comment', err);
      await fetchComments();
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (commentId: number) => {
    if (!confirm('댓글을 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/comments/${commentId}`);
      setComments(prev => prev.filter(c => c.id !== commentId));
    } catch (err) {
      console.error('Failed to delete comment', err);
    }
  };

  const canManageComment = (comment: Comment) =>
    Boolean(user?.email && comment.user?.email && user.email === comment.user.email);

  const startEdit = (comment: Comment) => {
    setEditingId(comment.id);
    setEditContent(comment.content);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  const handleUpdate = async (commentId: number) => {
    if (!editContent.trim()) return;
    try {
      const updated = await api.put<Comment>(`/comments/${commentId}`, { content: editContent });
      setComments((prev) => prev.map((comment) => (comment.id === commentId ? updated : comment)));
      setEditingId(null);
      setEditContent('');
    } catch (err) {
      console.error('Failed to update comment', err);
      await fetchComments();
    }
  };

  if (loading && commentCount === 0) {
    return (
      <div className="flex justify-center py-4">
        <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div data-testid="comment-count" className="text-sm text-slate-500">{commentCount} {commentCount === 1 ? 'comment' : 'comments'}</div>
        {comments.map((comment) => (
          <div
            key={comment.id}
            ref={(el) => {
              commentElementRefs.current[comment.id] = el;
            }}
            className="flex gap-3 group rounded-md transition-shadow"
          >
            <Avatar className="w-8 h-8 mt-1">
              <AvatarImage src={comment.user?.picture} />
              <AvatarFallback>{comment.user?.name?.[0]}</AvatarFallback>
            </Avatar>
            <div className="flex-1 space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-slate-900">{comment.user?.name}</span>
                  <span className="text-xs text-slate-500">
                    {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true, locale: ko })}
                  </span>
                </div>
                {canManageComment(comment) && (
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => startEdit(comment)}>
                      <Edit2 className="w-3 h-3 text-slate-500" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-6 w-6 hover:text-red-500" onClick={() => handleDelete(comment.id)}>
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                )}
              </div>

              {editingId === comment.id ? (
                <div
                  ref={(el) => {
                    commentBodyElementRefs.current[comment.id] = el;
                  }}
                  className="space-y-2"
                >
                  <Textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="min-h-[80px] text-sm"
                  />
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={cancelEdit}>취소</Button>
                    <Button size="sm" onClick={() => handleUpdate(comment.id)}>수정</Button>
                  </div>
                </div>
              ) : (
                <div
                  ref={(el) => {
                    commentBodyElementRefs.current[comment.id] = el;
                  }}
                  className="prose prose-sm max-w-none text-slate-700 bg-slate-50 rounded-lg px-3 py-2"
                >
                  <MarkdownRenderer content={comment.content} useRemarkGfm />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 pt-4 border-t border-slate-100">
        <Avatar className="w-8 h-8 mt-1">
          <AvatarImage src={user?.picture ?? undefined} />
          <AvatarFallback>{user?.name?.[0]}</AvatarFallback>
        </Avatar>
        <form onSubmit={handleSubmit} className="flex-1 flex gap-2">
          <Textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="댓글을 남겨보세요... (Markdown 지원)"
            className="min-h-[40px] h-[40px] py-2 resize-none focus:h-[80px] transition-all"
          />
          <Button type="submit" disabled={submitting || !newComment.trim()} size="icon" className="shrink-0 h-10 w-10">
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </form>
      </div>
    </div>
  );
}
