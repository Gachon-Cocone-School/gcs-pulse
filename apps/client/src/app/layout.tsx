import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/auth-context";
import Script from "next/script";
import { ThemeProvider } from "next-themes";
import { Noto_Serif_KR, Press_Start_2P } from "next/font/google";

import { Toaster } from "@/components/ui/sonner";
import { APP_THEME_VALUES } from "@/lib/theme";

export const metadata: Metadata = {
  title: "GCS Pulse",
  description: "GCS Pulse",
  icons: {
    icon: "/logo.svg",
    shortcut: "/logo.svg",
    apple: "/logo.svg",
  },
};

const retroDotFont = Press_Start_2P({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-retro-dot",
});

const matchaFont = Noto_Serif_KR({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-matcha",
});

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
    <html
      lang="ko"
      suppressHydrationWarning
      className={`${retroDotFont.variable} ${matchaFont.variable}`}
    >
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
        <ThemeProvider
          attribute="data-theme"
          defaultTheme="gcs"
          themes={[...APP_THEME_VALUES]}
          enableSystem={false}
          disableTransitionOnChange
        >
          <AuthProvider>
            {children}
            <Toaster />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
