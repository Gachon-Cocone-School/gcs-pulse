'use client';

import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import MarkdownRenderer from './MarkdownRenderer';

interface SnippetPreviewProps {
  content: string;
  contentClassName?: string;
}

/**
 * 스니펫의 마크다운 내용을 렌더링하는 컴포넌트입니다.
 * 프로젝트의 'prose' 스타일을 적용하며, GFM(GitHub Flavored Markdown)을 지원합니다.
 */
export default function SnippetPreview({ content, contentClassName }: SnippetPreviewProps) {
  return (
    <Card className="p-6 border-[var(--sys-current-border)] bg-card rounded-md">
      <div
        className={cn(
          'prose max-w-none p-0 m-0 overflow-x-auto overflow-y-auto break-words text-foreground [--tw-prose-body:var(--color-foreground)] [--tw-prose-headings:var(--color-foreground)] [--tw-prose-links:var(--color-foreground)] [--tw-prose-bold:var(--color-foreground)] [--tw-prose-bullets:var(--color-foreground)] [--tw-prose-counters:var(--color-foreground)] [&_h1]:text-2xl [&_h2]:text-xl [&_h3]:text-lg [&_h4]:text-base [&_h5]:text-sm [&_h6]:text-sm [&_p]:break-words [&_li]:break-words [&_pre]:max-w-full [&_pre]:overflow-x-auto',
          contentClassName,
        )}
      >
        <MarkdownRenderer content={content} useRemarkGfm useRehypeRaw />
      </div>
    </Card>
  );
}
