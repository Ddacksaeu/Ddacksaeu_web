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
  if (q) activeChips.push({ label: `검색: ${q}`, onRemove: () => setQ("") });

  return (
    <AppShell
      title="나에게 맞는 포스텍 연구실을 찾아보세요"
      description="연구 분야와 키워드를 기준으로 연구실 정보를 한곳에서 비교해보세요."
      actions={
        <Button
          size="lg"
          className="gap-2 rounded-full bg-[color:var(--point)] px-5 hover:bg-[color:var(--deep)]"
          onClick={() => navigate({ to: "/recommendations" })}
        >
          <Sparkles className="h-4 w-4" /> CV 기반 추천받기
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
            placeholder="교수명, 연구실명, 연구 키워드 검색"
            aria-label="연구실 검색"
            className="h-14 rounded-xl border-border bg-[color:var(--surface)] pl-12 pr-4 text-base placeholder:text-muted-foreground focus-visible:border-[color:var(--point)] focus-visible:ring-2 focus-visible:ring-[color:var(--point)]/30"
          />
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,220px)_1fr_minmax(0,180px)] sm:items-center">
          <Select value={dept} onValueChange={setDept}>
            <SelectTrigger className="h-11 rounded-lg border-border bg-white">
              <SelectValue placeholder="전체 학과" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">전체 학과</SelectItem>
              {DEPARTMENTS.map((d) => (
                <SelectItem key={d} value={d}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 flex items-center gap-1 text-xs text-muted-foreground">
              <SlidersHorizontal className="h-3.5 w-3.5" /> 연구 분야
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
              <SelectItem value="match">추천 일치율 순</SelectItem>
              <SelectItem value="recent">최근 업데이트 순</SelectItem>
              <SelectItem value="name">이름 순</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>

      {/* Results summary */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-foreground/80">
            <span className="font-semibold text-[color:var(--navy)]">{filtered.length}</span>개의
            연구실
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
                모두 초기화
              </button>
            </>
          )}
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-border bg-white p-1">
          <button
            aria-label="카드 보기"
            onClick={() => setView("grid")}
            className={cn(
              "grid h-8 w-8 place-items-center rounded-md text-muted-foreground",
              view === "grid" && "bg-[color:var(--surface)] text-[color:var(--deep)]",
            )}
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
          <button
            aria-label="리스트 보기"
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
            조건에 맞는 연구실이 없어요
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            필터를 조정하거나 검색어를 지워보세요.
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
            필터 초기화
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
            더 보기
          </Button>
        </div>
      )}

      {/* Featured recommendation CTA */}
      <section className="mt-10 overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-[color:var(--navy)] to-[color:var(--deep)] p-6 text-white sm:p-8">
        <div className="grid gap-6 sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-[11px] uppercase tracking-widest">
              <Sparkles className="h-3 w-3" /> AI 매칭
            </div>
            <h2 className="mt-3 text-xl font-semibold sm:text-2xl">
              CV를 올리면 나에게 맞는 연구실을 자동으로 골라드려요
            </h2>
            <p className="mt-2 max-w-xl text-sm text-white/70">
              연구 관심사, 기술 스택, 프로젝트 경험을 분석해 일치율 순으로 정렬된 추천 리스트를
              제공합니다.
            </p>
          </div>
          <Button
            asChild
            size="lg"
            className="rounded-full bg-white text-[color:var(--deep)] hover:bg-white/90"
          >
            <Link to="/recommendations">지금 분석하기</Link>
          </Button>
        </div>
      </section>
    </AppShell>
  );
}
