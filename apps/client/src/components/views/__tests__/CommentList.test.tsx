import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, it, expect, vi } from 'vitest';

// Mock modules used by CommentList (must run before importing the component)
vi.mock('@/context/auth-context', () => ({
  useAuth: () => ({
    user: { id: 1, name: 'Tester', picture: '' },
    isAuthenticated: true,
    isLoading: false,
    checkAuth: async () => {},
    logout: async () => {},
  }),
}));

vi.mock('@/lib/api', () => ({
  api: {
    get: async () => [],
    post: async () => ({}),
    put: async () => ({}),
    delete: async () => ({}),
  },
}));

vi.mock('@/components/ui/avatar', () => ({
  Avatar: (props: any) => React.createElement('div', props, props.children),
  AvatarImage: (props: any) => React.createElement('img', props),
  AvatarFallback: (props: any) => React.createElement('div', props, props.children),
}));

vi.mock('@/components/ui/button', () => ({
  Button: (props: any) => React.createElement('button', props, props.children),
}));

vi.mock('@/components/ui/textarea', () => ({
  Textarea: (props: any) => React.createElement('textarea', props, props.children),
}));

vi.mock('lucide-react', () => ({
  Loader2: (props: any) => React.createElement('span', props, 'loader'),
  Trash2: (props: any) => React.createElement('span', props, 'trash'),
  Edit2: (props: any) => React.createElement('span', props, 'edit'),
  Send: (props: any) => React.createElement('span', props, 'send'),
  X: (props: any) => React.createElement('span', props, 'x'),
}));

vi.mock('react-markdown', () => ({ default: (props: any) => React.createElement('div', null, props.children) }));
vi.mock('remark-gfm', () => ({ default: {} }));
vi.mock('date-fns', () => ({ formatDistanceToNow: () => '방금 전' }));
vi.mock('date-fns/locale', () => ({ ko: {} }));

import { CommentList } from '../CommentList';

const comments = [
  {
    id: 1,
    user_id: 1,
    user: { id: 1, name: 'Alice', email: 'a@example.com', picture: '' },
    content: 'First comment',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    user_id: 2,
    user: { id: 2, name: 'Bob', email: 'b@example.com', picture: '' },
    content: 'Second comment',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

describe('CommentList', () => {
  it('renders correct comment count', () => {
    const html = renderToStaticMarkup(<CommentList initialComments={comments} />);
    expect(/2 comments/i.test(html)).toBe(true);
  });
});
