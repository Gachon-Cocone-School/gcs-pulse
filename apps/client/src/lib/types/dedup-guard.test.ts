import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const authContextPath = resolve(process.cwd(), 'src/context/auth-context.tsx');
const commentListPath = resolve(process.cwd(), 'src/components/views/CommentList.tsx');

describe('type dedup guard', () => {
  it('removes local interface declarations from auth-context and CommentList', () => {
    const authContextSource = readFileSync(authContextPath, 'utf8');
    const commentListSource = readFileSync(commentListPath, 'utf8');

    expect(authContextSource).not.toMatch(/^\s*interface\s+\w+/m);
    expect(commentListSource).not.toMatch(/^\s*interface\s+\w+/m);
  });

  it('imports shared types from /lib/types in both files', () => {
    const authContextSource = readFileSync(authContextPath, 'utf8');
    const commentListSource = readFileSync(commentListPath, 'utf8');

    expect(authContextSource).toMatch(/from ['"]@\/lib\/types['"]/);
    expect(commentListSource).toMatch(/from ['"]@\/lib\/types['"]/);
  });
});
