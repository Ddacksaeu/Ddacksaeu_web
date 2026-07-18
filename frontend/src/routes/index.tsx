import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Search, SlidersHorizontal, LayoutGrid, List, Sparkles, X } from "lucide-react";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { LabCard } from "@/components/lab/LabCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LABS, DEPARTMENTS, FIELDS } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  component: ExplorePage,
});

function ExplorePage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [dept, setDept] = useState<string>("all");
  const [fields, setFields] = useState<string[]>([]);
  const [sort, setSort] = useState<"match" | "recent" | "name">("match");
  const [view, setView] = useState<"grid" | "list">("grid");

  const filtered = useMemo(() => {
    let out = LABS.filter((lab) => {
      const query = q.trim().toLowerCase();
      const matchQ =
        !query ||
        lab.name.toLowerCase().includes(query) ||
        lab.professor.toLowerCase().includes(query) ||
        lab.keywords.some((k) => k.toLowerCase().includes(query));
      const matchDept = dept === "all" || lab.department === dept;
      const matchField = fields.length === 0 || fields.includes(lab.field);
      return matchQ && matchDept && matchField;
    });
    if (sort === "match") out = [...out].sort((a, b) => b.matchScore - a.matchScore);
    if (sort === "recent") out = [...out].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
    if (sort === "name") out = [...out].sort((a, b) => a.name.localeCompare(b.name, "ko"));
    return out;
  }, [q, dept, fields, sort]);

  const toggleField = (f: string) =>
    setFields((s) => (s.includes(f) ? s.filter((x) => x !== f) : [...s, f]));

  const activeChips: { label: string; onRemove: () => void }[] = [];
  if (dept !== "all") activeChips.push({ label: dept, onRemove: () => setDept("all") });
  fields.forEach((f) => activeChips.push({ label: f, onRemove: () => toggleField(f) }));
  if (q) activeChips.push({ label: `Search: ${q}`, onRemove: () => setQ("") });

  return (
    <AppShell
      title="Find the POSTECH lab that fits you"
      description="Compare labs in one place by research field and keyword."
      actions={
        <Button
          size="lg"
          className="gap-2 rounded-full bg-[color:var(--point)] px-5 hover:bg-[color:var(--deep)]"
          onClick={() => navigate({ to: "/recommendations" })}
        >
          <Sparkles className="h-4 w-4" /> Get CV-based recommendations
        </Button>
      }
    >
      {/* Search bar */}
      <section className="rounded-2xl border border-border bg-white p-4 shadow-[0_1px_0_0_oklch(0.92_0.014_250)] sm:p-5">
        <div className="relative">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search professors, labs, or research keywords"
            aria-label="Search labs"
            className="h-14 rounded-xl border-border bg-[color:var(--surface)] pl-12 pr-4 text-base placeholder:text-muted-foreground focus-visible:border-[color:var(--point)] focus-visible:ring-2 focus-visible:ring-[color:var(--point)]/30"
          />
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,220px)_1fr_minmax(0,180px)] sm:items-center">
          <Select value={dept} onValueChange={setDept}>
            <SelectTrigger className="h-11 rounded-lg border-border bg-white">
              <SelectValue placeholder="All departments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All departments</SelectItem>
              {DEPARTMENTS.map((d) => (
                <SelectItem key={d} value={d}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 flex items-center gap-1 text-xs text-muted-foreground">
              <SlidersHorizontal className="h-3.5 w-3.5" /> Research fields
            </span>
            {FIELDS.slice(0, 8).map((f) => {
              const active = fields.includes(f);
              return (
                <button
                  key={f}
                  type="button"
                  onClick={() => toggleField(f)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs transition-colors",
                    active
                      ? "border-[color:var(--point)] bg-[color:var(--point)]/10 text-[color:var(--deep)]"
                      : "border-border bg-white text-foreground/70 hover:border-[color:var(--point)]/50 hover:text-[color:var(--deep)]",
                  )}
                  aria-pressed={active}
                >
                  {f}
                </button>
              );
            })}
          </div>

          <Select value={sort} onValueChange={(v) => setSort(v as typeof sort)}>
            <SelectTrigger className="h-11 rounded-lg border-border bg-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="match">Best match</SelectItem>
              <SelectItem value="recent">Recently updated</SelectItem>
              <SelectItem value="name">Name</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>

      {/* Results summary */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-foreground/80">
            <span className="font-semibold text-[color:var(--navy)]">{filtered.length}</span> labs
          </span>
          {activeChips.length > 0 && (
            <>
              <span className="text-border">|</span>
              {activeChips.map((c) => (
                <button
                  key={c.label}
                  onClick={c.onRemove}
                  className="inline-flex items-center gap-1 rounded-full border border-border bg-white px-2.5 py-1 text-xs text-foreground/70 hover:border-[color:var(--point)]/50 hover:text-[color:var(--deep)]"
                >
                  {c.label}
                  <X className="h-3 w-3" />
                </button>
              ))}
              <button
                onClick={() => {
                  setDept("all");
                  setFields([]);
                  setQ("");
                }}
                className="text-xs text-muted-foreground hover:text-[color:var(--deep)]"
              >
                Clear all
              </button>
            </>
          )}
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-border bg-white p-1">
          <button
            aria-label="Card view"
            onClick={() => setView("grid")}
            className={cn(
              "grid h-8 w-8 place-items-center rounded-md text-muted-foreground",
              view === "grid" && "bg-[color:var(--surface)] text-[color:var(--deep)]",
            )}
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
          <button
            aria-label="List view"
            onClick={() => setView("list")}
            className={cn(
              "grid h-8 w-8 place-items-center rounded-md text-muted-foreground",
              view === "list" && "bg-[color:var(--surface)] text-[color:var(--deep)]",
            )}
          >
            <List className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Results */}
      {filtered.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-dashed border-border bg-white p-12 text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-[color:var(--surface)] text-[color:var(--deep)]">
            <Search className="h-5 w-5" />
          </div>
          <h3 className="mt-4 text-base font-semibold text-[color:var(--navy)]">
            No labs match your criteria
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Adjust the filters or clear your search.
          </p>
          <Button
            variant="outline"
            className="mt-4 rounded-full"
            onClick={() => {
              setDept("all");
              setFields([]);
              setQ("");
            }}
          >
            Reset filters
          </Button>
        </div>
      ) : (
        <div
          className={cn(
            "mt-4 grid gap-4",
            view === "grid" ? "sm:grid-cols-2 xl:grid-cols-3" : "grid-cols-1",
          )}
        >
          {filtered.map((lab) => (
            <LabCard key={lab.id} lab={lab} variant={view} />
          ))}
        </div>
      )}

      {/* Load more */}
      {filtered.length > 0 && (
        <div className="mt-8 flex justify-center">
          <Button variant="outline" className="rounded-full px-6">
            Show more
          </Button>
        </div>
      )}

      {/* Featured recommendation CTA */}
      <section className="mt-10 overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-[color:var(--navy)] to-[color:var(--deep)] p-6 text-white sm:p-8">
        <div className="grid gap-6 sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-[11px] uppercase tracking-widest">
              <Sparkles className="h-3 w-3" /> AI matching
            </div>
            <h2 className="mt-3 text-xl font-semibold sm:text-2xl">
              Upload your CV to discover labs that fit your background
            </h2>
            <p className="mt-2 max-w-xl text-sm text-white/70">
              We analyze your interests, skills, and project experience to rank matching labs
              for you.
            </p>
          </div>
          <Button asChild size="lg" className="rounded-full bg-white text-[color:var(--deep)] hover:bg-white/90">
            <Link to="/recommendations">
              Analyze my CV
            </Link>
          </Button>
        </div>
      </section>
    </AppShell>
  );
}
