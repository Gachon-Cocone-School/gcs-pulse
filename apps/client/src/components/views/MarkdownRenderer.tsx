'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';

// @mention 토큰을 <mark> 노드로 변환하는 remark 플러그인
function remarkMentions() {
  return (tree: any) => {
    walkNode(tree);
  };
}

function walkNode(node: any) {
  if (!node.children) return;

  const newChildren: any[] = [];
  for (const child of node.children) {
    if (child.type === 'text') {
      newChildren.push(...splitMentions(child.value));
    } else {
      walkNode(child);
      newChildren.push(child);
    }
  }
  node.children = newChildren;
}

function splitMentions(text: string): any[] {
  const MENTION_RE = /@([^\s@]+)/g;
  const parts: any[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = MENTION_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, match.index) });
    }
    parts.push({
      type: 'mention',
      value: match[0],
      data: {
        hName: 'mark',
        hProperties: {},
      },
      children: [{ type: 'text', value: match[0] }],
    });
    lastIndex = MENTION_RE.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) });
  }

  return parts.length > 0 ? parts : [{ type: 'text', value: text }];
}

type MarkdownRendererProps = {
  content: string;
  useRemarkGfm?: boolean;
  useRehypeRaw?: boolean;
  highlightMentions?: boolean;
};

export default function MarkdownRenderer({
  content,
  useRemarkGfm = false,
  useRehypeRaw = false,
  highlightMentions = false,
}: MarkdownRendererProps) {
  const remarkPlugins: any[] = [];
  if (useRemarkGfm) remarkPlugins.push(remarkGfm);
  if (highlightMentions) remarkPlugins.push(remarkMentions);

  const rehypePlugins = useRehypeRaw ? [rehypeRaw, rehypeSanitize] : [];

  return (
    <ReactMarkdown
      remarkPlugins={remarkPlugins}
      rehypePlugins={rehypePlugins}
      components={{
        mark: ({ children }) => (
          <span className="text-primary font-medium bg-primary/10 rounded px-0.5">{children}</span>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
