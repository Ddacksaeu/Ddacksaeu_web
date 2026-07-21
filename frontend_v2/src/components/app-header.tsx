"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { endDemoSession } from "../features/auth/demo-session";

type AppHeaderProperties = {
  readonly current?: "dashboard" | "professors" | "cv" | "contact" | "calendar" | "profile";
  readonly setup?: boolean;
};

const ITEMS = [
  { id: "dashboard", href: "/dashboard", label: "Home" },
  { id: "professors", href: "/professors", label: "Professors" },
  { id: "calendar", href: "/calendar", label: "Calendar" },
  { id: "profile", href: "/profile", label: "Profile" },
] as const;

export function AppHeader({ current, setup = false }: AppHeaderProperties) {
  const router = useRouter();
  const workspace = current !== undefined;

  function logout(): void {
    void fetch("/api/auth/logout", { method: "POST" });
    endDemoSession(window.localStorage);
    router.replace("/");
  }

  return (
    <header className={`site-header${workspace || setup ? " site-header-workspace" : ""}`}>
      <div className="site-header-inner">
        <Link className="brand" href={setup ? "/onboarding" : workspace ? "/dashboard" : "/"}>
          <Image alt="" className="brand-logo" height={24} src="/brand-shrimp.png" width={24} />
          <span>Ddaksaeu</span>
        </Link>
        <nav aria-label="Main navigation" className="main-nav">
          {workspace ? ITEMS.map((item) => (
            <Link aria-current={item.id === current ? "page" : undefined} href={item.href} key={item.id}>
              {item.label}
            </Link>
          )) : null}
          {setup ? <span className="header-status">Onboarding</span> : null}
          {workspace || setup ? <button className="logout-button" onClick={logout} type="button">Sign out</button> : <Link href="/login">Sign in</Link>}
        </nav>
      </div>
    </header>
  );
}
