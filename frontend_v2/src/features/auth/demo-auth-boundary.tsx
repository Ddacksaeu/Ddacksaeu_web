"use client";

import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { hasCompletedDemoOnboarding, hasDemoSession } from "./demo-session";

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/professors",
  "/calendar",
  "/profile",
  "/cv",
  "/contact",
  "/labs",
  "/onboarding",
] as const;

type DemoAuthBoundaryProperties = Readonly<{ children: ReactNode }>;

function requiresDemoSession(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function DemoAuthBoundary({ children }: DemoAuthBoundaryProperties) {
  const pathname = usePathname();
  const router = useRouter();
  const protectedRoute = requiresDemoSession(pathname);
  const [ready, setReady] = useState(!protectedRoute);

  useEffect(() => {
    const signedIn = hasDemoSession(window.localStorage);
    const onboardingComplete = hasCompletedDemoOnboarding(window.localStorage);

    if (protectedRoute && !signedIn) {
      router.replace("/login");
      return;
    }

    if (pathname === "/onboarding" && onboardingComplete) {
      router.replace("/dashboard");
      return;
    }

    if (protectedRoute && pathname !== "/onboarding" && !onboardingComplete) {
      router.replace("/onboarding");
      return;
    }

    const frame = window.requestAnimationFrame(() => setReady(true));
    return () => window.cancelAnimationFrame(frame);
  }, [pathname, protectedRoute, router]);

  if (!ready) {
    return <main className="auth-gate-status" role="status">Checking your session.</main>;
  }

  return children;
}
