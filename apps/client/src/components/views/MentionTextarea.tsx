'use client';

import React from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { api } from '@/lib/api';
import type { MentionableUser } from '@/lib/types';

interface MentionTextareaProps {
  value: string;
  onChange: (value: string) => void;
  dailySnippetId?: number;
  weeklySnippetId?: number;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export interface MentionTextareaHandle {
  insertText: (text: string) => void;
}

export const MentionTextarea = React.forwardRef<MentionTextareaHandle, MentionTextareaProps>(
function MentionTextarea({
  value,
  onChange,
  dailySnippetId,
  weeklySnippetId,
  placeholder,
  className,
  disabled,
}, ref) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  React.useImperativeHandle(ref, () => ({
    insertText: (text: string) => {
      const textarea = textareaRef.current;
      const start = textarea?.selectionStart ?? value.length;
      const end = textarea?.selectionEnd ?? value.length;
      const newValue = value.slice(0, start) + text + value.slice(end);
      onChange(newValue);
      const newCursor = start + text.length;
      setTimeout(() => {
        textarea?.focus();
        textarea?.setSelectionRange(newCursor, newCursor);
      }, 0);
    },
  }));
  const [mentionableUsers, setMentionableUsers] = React.useState<MentionableUser[]>([]);
  const [usersFetched, setUsersFetched] = React.useState(false);
  const [showDropdown, setShowDropdown] = React.useState(false);
  const [filterText, setFilterText] = React.useState('');
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const [mentionStart, setMentionStart] = React.useState(-1);

  const fetchUsersIfNeeded = React.useCallback(async () => {
    if (usersFetched) return;
    setUsersFetched(true);
    try {
      const users = await api.getMentionableUsers({ dailySnippetId, weeklySnippetId });
      setMentionableUsers(users);
    } catch {
      // 실패해도 자동완성이 안 될 뿐, 댓글 작성에는 영향 없음
    }
  }, [dailySnippetId, weeklySnippetId, usersFetched]);

  const filteredUsers = React.useMemo(() => {
    if (!filterText) return mentionableUsers;
    const lower = filterText.toLowerCase();
    return mentionableUsers.filter((u) => u.name.toLowerCase().includes(lower));
  }, [mentionableUsers, filterText]);

  const handleChange = React.useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value;
      const cursor = e.target.selectionStart ?? newValue.length;
      onChange(newValue);

      const textUpToCursor = newValue.slice(0, cursor);
      const match = textUpToCursor.match(/@([^\s@]*)$/);

      if (match) {
        setFilterText(match[1]);
        setMentionStart(match.index!);
        setShowDropdown(true);
        setSelectedIndex(0);
        fetchUsersIfNeeded();
      } else {
        setShowDropdown(false);
        setMentionStart(-1);
      }
    },
    [onChange, fetchUsersIfNeeded],
  );

  const insertMention = React.useCallback(
    (user: MentionableUser) => {
      const textarea = textareaRef.current;
      if (!textarea || mentionStart === -1) return;

      const cursor = textarea.selectionStart ?? value.length;
      const before = value.slice(0, mentionStart);
      const after = value.slice(cursor);
      const inserted = `@${user.name} `;
      onChange(`${before}${inserted}${after}`);
      setShowDropdown(false);
      setMentionStart(-1);

      const newCursor = mentionStart + inserted.length;
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(newCursor, newCursor);
      }, 0);
    },
    [value, onChange, mentionStart],
  );

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (!showDropdown || filteredUsers.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filteredUsers.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredUsers.length) % filteredUsers.length);
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (filteredUsers[selectedIndex]) {
          insertMention(filteredUsers[selectedIndex]);
        }
      } else if (e.key === 'Escape') {
        setShowDropdown(false);
      }
    },
    [showDropdown, filteredUsers, selectedIndex, insertMention],
  );

  return (
    <div className="relative flex-1">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={className}
        disabled={disabled}
      />
      {showDropdown && filteredUsers.length > 0 && (
        <div className="absolute bottom-full left-0 mb-1 z-50 bg-card border border-border rounded-md shadow-lg overflow-hidden min-w-[180px] max-w-[280px] max-h-[200px] overflow-y-auto">
          {filteredUsers.map((user, index) => (
            <button
              key={user.id}
              type="button"
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm cursor-pointer transition-colors ${
                index === selectedIndex ? 'bg-accent' : 'hover:bg-accent/50'
              }`}
              onMouseDown={(e) => {
                e.preventDefault();
                insertMention(user);
              }}
            >
              <Avatar className="w-5 h-5 shrink-0">
                <AvatarImage src={user.picture} />
                <AvatarFallback className="text-xs">{user.name[0]}</AvatarFallback>
              </Avatar>
              <span className="truncate">{user.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
});

