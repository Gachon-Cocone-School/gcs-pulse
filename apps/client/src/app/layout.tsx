import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/auth-context";
import Script from "next/script";

import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "GCS Pulse",
  description: "GCS Pulse",
  icons: {
    icon: "/logo.svg",
    shortcut: "/logo.svg",
    apple: "/logo.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const isE2E = process.env.NEXT_PUBLIC_E2E_TEST === "true";
  const enableReactGrab =
    process.env.NODE_ENV === "development" &&
    process.env.CI !== "true" &&
    !isE2E &&
    process.env.NEXT_PUBLIC_ENABLE_REACT_GRAB === "true";

  return (
    <html lang="ko">
      <head>
        {enableReactGrab && (
          <Script id="react-grab-loader" strategy="afterInteractive">
            {`
              (function () {
                var scripts = [
                  "//unpkg.com/react-grab/dist/index.global.js",
                  "//unpkg.com/@react-grab/opencode/dist/client.global.js"
                ];

                for (var i = 0; i < scripts.length; i++) {
                  var s = document.createElement('script');
                  s.src = scripts[i];
                  s.async = true;
                  document.head.appendChild(s);
                }
              })();
            `}
          </Script>
        )}
      </head>
      <body>
        <AuthProvider>
          {children}
          <Toaster />
        </AuthProvider>
      </body>
    </html>
  );
}
