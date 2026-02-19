import { homeMetadata } from "@/app/metadata";
import HomePageClient from "./page.client";

export const metadata = homeMetadata;

export default function HomePage() {
  return <HomePageClient />;
}
