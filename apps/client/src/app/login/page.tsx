import { loginMetadata } from "@/app/metadata";
import LoginPageClient from "./LoginPageClient";

export const metadata = loginMetadata;

export default function LoginPage() {
  return <LoginPageClient />;
}
