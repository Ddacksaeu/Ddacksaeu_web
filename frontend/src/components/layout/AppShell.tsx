import { Link, useRouterState } from "@tanstack/react-router";
import {
  Search,
  Sparkles,
  Heart,
  Calendar as CalendarIcon,
  User,
  Menu,
  X,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type NavItem = {
  to: "/" | "/recommendations" | "/favorites" | "/calendar" | "/profile";
  label: string;
  icon: typeof Search;
  exact?: boolean;
};

const NAV: NavItem[] = [
  { to: "/", label: "Explore Labs", icon: Search, exact: true },
  { to: "/recommendations", label: "Recommendations", icon: Sparkles },
  { to: "/favorites", label: "Saved Labs", icon: Heart },
  { to: "/calendar", label: "Application Calendar", icon: CalendarIcon },
  { to: "/profile", label: "My Profile", icon: User },
];

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[color:var(--point)] text-white shadow-[0_4px_14px_-4px_oklch(0.62_0.18_258/0.5)]">
        {/* stylized shrimp/search mark */}
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5">
          <path
            d="M6 14c0-3.3 2.7-6 6-6 2 0 3.8 1 4.9 2.5M17 8l1.5-1.5M15 14a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm0 0 3.5 3.5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      {!compact && (
        <div className="min-w-0">
          <div className="text-base font-semibold tracking-tight text-white">Ddaksaeu</div>
          <div className="text-[11px] leading-none text-white/60">POSTECH Lab Finder</div>
        </div>
      )}
    </div>
  );
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <nav className="flex flex-col gap-1 px-3">
      {NAV.map((item) => {
        const active = item.exact ? pathname === item.to : pathname.startsWith(item.to);
        const Icon = item.icon;
        return (
          <Link
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={cn(
              "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
              "text-white/70 hover:bg-white/5 hover:text-white",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--point)]",
              active && "bg-white/10 text-white shadow-inner",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" strokeWidth={1.8} />
            <span className="truncate">{item.label}</span>
            {active && (
              <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[color:var(--point)]" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}

function UserCard() {
  return (
    <div className="mx-3 mb-3 flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[color:var(--point)] to-[color:var(--deep)] text-sm font-semibold text-white">
        AK
      </div>
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-white">Alex Kim</div>
        <div className="truncate text-[11px] text-white/60">AI · Computer Vision</div>
      </div>
    </div>
  );
}

export function AppShell({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="min-h-screen bg-[color:var(--surface)] text-foreground">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-[color:var(--navy)] lg:flex">
        <div className="px-5 py-5">
          <Logo />
        </div>
        <div className="mt-2 flex-1 overflow-y-auto">
          <div className="px-5 pb-2 text-[11px] font-medium uppercase tracking-widest text-white/40">
            Menu
          </div>
          <NavList />
        </div>
        <UserCard />
      </aside>

      {/* Mobile top header */}
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
        <div className="flex items-center gap-2">
          <button
            aria-label="Open menu"
            onClick={() => setMobileOpen(true)}
            className="grid h-9 w-9 place-items-center rounded-lg border border-border text-foreground"
          >
            <Menu className="h-4 w-4" />
          </button>
          <span className="text-sm font-semibold text-[color:var(--navy)]">Ddaksaeu</span>
        </div>
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-72 flex-col bg-[color:var(--navy)]">
            <div className="flex items-center justify-between px-5 py-5">
              <Logo />
              <button
                aria-label="Close menu"
                onClick={() => setMobileOpen(false)}
                className="grid h-8 w-8 place-items-center rounded-lg text-white/70 hover:bg-white/10"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <NavList onNavigate={() => setMobileOpen(false)} />
            </div>
            <UserCard />
          </div>
        </div>
      )}

      {/* Main */}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 hidden border-b border-border bg-white/85 px-8 py-5 backdrop-blur lg:block">
          <div className="flex items-end justify-between gap-6">
            <div className="min-w-0">
              <h1 className="truncate text-xl font-semibold tracking-tight text-[color:var(--navy)]">
                {title}
              </h1>
              {description && (
                <p className="mt-1 text-sm text-muted-foreground">{description}</p>
              )}
            </div>
            {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
          </div>
        </header>
        <main className="px-4 py-6 pb-24 sm:px-6 lg:px-8 lg:py-8 lg:pb-12">
          {/* Mobile title area */}
          <div className="mb-5 lg:hidden">
            <h1 className="text-xl font-semibold tracking-tight text-[color:var(--navy)]">
              {title}
            </h1>
            {description && (
              <p className="mt-1 text-sm text-muted-foreground">{description}</p>
            )}
            {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
          </div>
          {children}
        </main>
      </div>

      {/* Mobile bottom nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-20 border-t border-border bg-white/95 backdrop-blur lg:hidden">
        <div className="grid grid-cols-5">
          {NAV.map((item) => {
            const active = item.exact ? pathname === item.to : pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex flex-col items-center gap-1 py-2 text-[11px]",
                  active
                    ? "text-[color:var(--point)]"
                    : "text-muted-foreground",
                )}
              >
                <Icon className="h-5 w-5" strokeWidth={active ? 2.2 : 1.6} />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
