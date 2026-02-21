'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

type MarkdownRendererProps = {
  content: string;
  useRemarkGfm?: boolean;
  useRehypeRaw?: boolean;
};

export default function MarkdownRenderer({
  content,
  useRemarkGfm = false,
  useRehypeRaw = false,
}: MarkdownRendererProps) {
  const remarkPlugins = useRemarkGfm ? [remarkGfm] : [];
  const rehypePlugins = useRehypeRaw ? [rehypeRaw] : [];

  return (
    <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>
      {content}
    </ReactMarkdown>
  );
}
