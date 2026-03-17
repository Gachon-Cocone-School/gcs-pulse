import { Suspense } from 'react';
import { loginMetadata } from "@/app/metadata";
import LoginPageClient from "./LoginPageClient";

export const metadata = loginMetadata;

export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageClient />
    </Suspense>
  );
}
