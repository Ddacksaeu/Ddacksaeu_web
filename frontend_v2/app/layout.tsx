import type { Metadata } from "next";
import Script from "next/script";
import type { ReactNode } from "react";

import { DemoAuthBoundary } from "../src/features/auth/demo-auth-boundary";
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
      </head>
      <body><DemoAuthBoundary>{children}</DemoAuthBoundary></body>
    </html>
  );
}
