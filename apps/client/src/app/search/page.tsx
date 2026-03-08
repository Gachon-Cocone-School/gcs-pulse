import { Suspense } from 'react';
import SearchPageClient from './page.client';

interface SearchPageProps {
  searchParams: Promise<{
    q?: string;
    type?: string;
    scope?: string;
  }>;
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const { q, type, scope } = await searchParams;

  return (
    <Suspense>
      <SearchPageClient qParam={q} typeParam={type} scopeParam={scope} />
    </Suspense>
  );
}
