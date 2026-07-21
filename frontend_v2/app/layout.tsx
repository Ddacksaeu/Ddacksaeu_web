import type { Metadata } from "next";
import Script from "next/script";
import type { ReactNode } from "react";

import { DemoAuthBoundary } from "../src/features/auth/demo-auth-boundary";
import { isShowcaseMode, SHOWCASE_UNAVAILABLE_MESSAGE } from "../src/features/showcase/mode";
import "./globals.css";

export const metadata: Metadata = {
  title: "Graduate Outreach Assistant",
  description: "A focused workspace for graduate school outreach"
};

const enableDevTools = process.env.NODE_ENV === "development"
  && process.env["NEXT_PUBLIC_DISABLE_REACT_DEVTOOLS"] !== "1";

type RootLayoutProperties = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProperties) {
  const showcaseMode = isShowcaseMode();
  const showcaseFetchGuard = `(() => {
    const originalFetch = window.fetch.bind(window);
    const unavailable = ${JSON.stringify(SHOWCASE_UNAVAILABLE_MESSAGE)};
    window.fetch = (input, init) => {
      const requestUrl = typeof input === "string" ? input : input instanceof Request ? input.url : input.toString();
      const url = new URL(requestUrl, window.location.href);
      const backendFeature = url.origin === window.location.origin && (
        url.pathname.startsWith("/api/backend") ||
        url.pathname === "/api/auth/login" ||
        url.pathname === "/api/auth/signup" ||
        url.pathname === "/api/profile"
      );
      if (!backendFeature) return originalFetch(input, init);
      return Promise.resolve(new Response(JSON.stringify({ error: { code: "showcase_mode", message: unavailable }, detail: unavailable }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }));
    };
  })();`;

  return (
    <html lang="en">
      <head>
        {enableDevTools && (
          <>
            <Script
              src="//unpkg.com/react-grab/dist/index.global.js"
              crossOrigin="anonymous"
              strategy="beforeInteractive"
            />
            <Script
              src="//unpkg.com/react-scan/dist/auto.global.js"
              crossOrigin="anonymous"
              strategy="beforeInteractive"
            />
          </>
        )}
        {showcaseMode ? <Script id="showcase-fetch-guard" strategy="beforeInteractive">{showcaseFetchGuard}</Script> : null}
      </head>
      <body>
        {showcaseMode ? <aside className="showcase-notice" role="note">{SHOWCASE_UNAVAILABLE_MESSAGE}</aside> : null}
        <DemoAuthBoundary>{children}</DemoAuthBoundary>
      </body>
    </html>
  );
}
