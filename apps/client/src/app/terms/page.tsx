import { termsMetadata } from "@/app/metadata";
import TermsPageClient from "./page.client";

export const metadata = termsMetadata;

export default function TermsPage() {
  return <TermsPageClient />;
}
