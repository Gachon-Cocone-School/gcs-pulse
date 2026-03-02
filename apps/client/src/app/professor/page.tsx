import { professorMetadata } from '@/app/metadata';
import ProfessorPageClient from './page.client';

export const metadata = professorMetadata;

export default function ProfessorPage() {
  return <ProfessorPageClient />;
}
