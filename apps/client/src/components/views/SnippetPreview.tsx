'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { Card } from '@/components/ui/card';

interface SnippetPreviewProps {
  content: string;
}

/**
 * 스니펫의 마크다운 내용을 렌더링하는 컴포넌트입니다.
 * 프로젝트의 'prose' 스타일을 적용하며, GFM(GitHub Flavored Markdown)을 지원합니다.
 */
export default function SnippetPreview({ content }: SnippetPreviewProps) {
  return (
    <Card className="p-6 border bg-card rounded-md">
      <div className="prose max-w-none dark:prose-invert p-0 m-0">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
          {content}
        </ReactMarkdown>
      </div>
    </Card>
  );
}
