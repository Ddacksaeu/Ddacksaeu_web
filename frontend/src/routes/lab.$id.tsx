import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import {
  ExternalLink,
  Heart,
  MapPin,
  Mail,
  CalendarPlus,
  ChevronRight,
  Users,
  Sparkles,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LabCard, MatchBar } from "@/components/lab/LabCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LABS, type Lab } from "@/lib/mock-data";
import { useAppState } from "@/lib/app-state";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/lab/$id")({
  loader: ({ params }) => {
    const lab = LABS.find((l) => l.id === params.id);
    if (!lab) throw notFound();
    return { lab } satisfies { lab: Lab };
  },
  component: LabDetail,
  head: ({ loaderData }) => ({
    meta: [
      { title: loaderData ? `${loaderData.lab.name} · 딱새우` : "연구실 · 딱새우" },
      { name: "description", content: loaderData?.lab.summary ?? "포스텍 연구실 상세" },
    ],
  }),
});

function LabDetail() {
  const { lab } = Route.useLoaderData() as { lab: Lab };
  const { isFavorite, toggleFavorite, addEvent } = useAppState();
  const navigate = useNavigate();
  const fav = isFavorite(lab.id);
  const similar = LABS.filter((l) => l.id !== lab.id && l.field === lab.field).slice(0, 3).length
    ? LABS.filter((l) => l.id !== lab.id && l.field === lab.field).slice(0, 3)
    : LABS.filter((l) => l.id !== lab.id).slice(0, 3);
  const matchedKeywords = ["Computer Vision", "Multimodal", "Diffusion Model"].filter((k) =>
    lab.keywords.some((lk) => lk.toLowerCase().includes(k.toLowerCase())),
  );

  return (
    <AppShell
      title={lab.name}
      description={`${lab.professor} · ${lab.department}`}
      actions={
        <>
          <Button
            variant="outline"
            className="gap-2 rounded-full"
            onClick={() => toggleFavorite(lab.id)}
          >
            <Heart
              className={cn(
                "h-4 w-4",
                fav && "fill-[color:var(--point)] text-[color:var(--point)]",
              )}
            />
            {fav ? "저장됨" : "관심 저장"}
          </Button>
          <Button
            asChild
            className="gap-2 rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)]"
          >
            <a href={lab.homepage} target="_blank" rel="noreferrer">
              <ExternalLink className="h-4 w-4" /> 홈페이지
            </a>
          </Button>
        </>
      }
    >
      {/* Breadcrumb */}
      <nav
        aria-label="breadcrumb"
        className="mb-4 flex items-center gap-1.5 text-xs text-muted-foreground"
      >
        <Link to="/" className="hover:text-[color:var(--deep)]">
          연구실 탐색
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span>{lab.department}</span>
        <ChevronRight className="h-3 w-3" />
        <span className="text-[color:var(--navy)]">{lab.name}</span>
      </nav>

      {/* Header card */}
      <section className="rounded-2xl border border-border bg-white p-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className="rounded-full border border-[color:var(--point)]/30 bg-[color:var(--point)]/10 text-[color:var(--deep)] hover:bg-[color:var(--point)]/10">
            내 연구 관심사와 {lab.matchScore}% 일치
          </Badge>
          <Badge
            variant="outline"
            className="rounded-full border-border bg-[color:var(--surface)] font-normal text-foreground/70"
          >
            {lab.field}
          </Badge>
          <span className="text-xs text-muted-foreground">데이터 업데이트 {lab.updatedAt}</span>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_260px] sm:items-start">
          <p className="text-sm leading-relaxed text-foreground/85">{lab.summary}</p>
          <div className="rounded-xl bg-[color:var(--surface)] p-4">
            <div className="text-[11px] uppercase tracking-widest text-muted-foreground">
              내 프로필 일치율
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <div className="text-3xl font-semibold tabular-nums text-[color:var(--navy)]">
                {lab.matchScore}%
              </div>
            </div>
            <div className="mt-2">
              <MatchBar score={lab.matchScore} />
            </div>
            {matchedKeywords.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {matchedKeywords.map((k) => (
                  <span
                    key={k}
                    className="rounded-full border border-[color:var(--point)]/30 bg-[color:var(--point)]/10 px-2 py-0.5 text-[11px] text-[color:var(--deep)]"
                  >
                    {k}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Main grid */}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          <Tabs defaultValue="overview">
            <TabsList className="rounded-full bg-[color:var(--surface)] p-1">
              <TabsTrigger
                value="overview"
                className="rounded-full data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
              >
                개요
              </TabsTrigger>
              <TabsTrigger
                value="fields"
                className="rounded-full data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
              >
                연구 분야
              </TabsTrigger>
              <TabsTrigger
                value="papers"
                className="rounded-full data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
              >
                최근 논문
              </TabsTrigger>
              <TabsTrigger
                value="info"
                className="rounded-full data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
              >
                연구실 정보
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-5 space-y-5">
              <SectionCard title="연구실 소개">
                <p className="text-sm leading-relaxed text-foreground/85">{lab.summary}</p>
              </SectionCard>
              <SectionCard title="핵심 연구 분야">
                <div className="flex flex-wrap gap-1.5">
                  {lab.keywords.map((k) => (
                    <Badge
                      key={k}
                      variant="outline"
                      className="rounded-full border-border bg-[color:var(--surface)] font-normal"
                    >
                      {k}
                    </Badge>
                  ))}
                </div>
              </SectionCard>
              <SectionCard title="현재 연구 주제">
                <ul className="space-y-2 text-sm">
                  {lab.recentTopics.map((t) => (
                    <li key={t} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--point)]" />
                      <span>{t}</span>
                    </li>
                  ))}
                </ul>
              </SectionCard>
              <SectionCard title="지원자에게 기대하는 역량">
                <ul className="space-y-2 text-sm">
                  {lab.requirements.map((t) => (
                    <li key={t} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--deep)]" />
                      <span>{t}</span>
                    </li>
                  ))}
                </ul>
              </SectionCard>
            </TabsContent>

            <TabsContent value="fields" className="mt-5">
              <SectionCard title="연구 방향">
                <div className="grid gap-3 sm:grid-cols-2">
                  {lab.recentTopics.map((t, i) => (
                    <div
                      key={t}
                      className="rounded-xl border border-border bg-[color:var(--surface)] p-4"
                    >
                      <div className="text-xs uppercase tracking-widest text-muted-foreground">
                        방향 {i + 1}
                      </div>
                      <div className="mt-1 text-sm font-medium text-[color:var(--navy)]">{t}</div>
                    </div>
                  ))}
                </div>
              </SectionCard>
            </TabsContent>

            <TabsContent value="papers" className="mt-5">
              <SectionCard title={`최근 논문 · ${lab.papers.length}편`}>
                <ul className="divide-y divide-border">
                  {lab.papers.map((p) => (
                    <li
                      key={p.title}
                      className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-[color:var(--navy)]">
                          {p.title}
                        </div>
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          {p.venue} · {p.year}
                        </div>
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {p.keywords.map((k) => (
                            <span
                              key={k}
                              className="rounded-full bg-[color:var(--surface)] px-2 py-0.5 text-[11px] text-foreground/70"
                            >
                              {k}
                            </span>
                          ))}
                        </div>
                      </div>
                      <span className="shrink-0 rounded-full border border-border px-2 py-0.5 text-[11px] tabular-nums text-muted-foreground">
                        {p.year}
                      </span>
                    </li>
                  ))}
                </ul>
              </SectionCard>
            </TabsContent>

            <TabsContent value="info" className="mt-5">
              <SectionCard title="연구실 구성">
                <div className="grid grid-cols-3 gap-3">
                  <Stat
                    icon={<Users className="h-4 w-4" />}
                    label="교수"
                    value={`${lab.members.professor}명`}
                  />
                  <Stat
                    icon={<Users className="h-4 w-4" />}
                    label="박사"
                    value={`${lab.members.phd}명`}
                  />
                  <Stat
                    icon={<Users className="h-4 w-4" />}
                    label="석사"
                    value={`${lab.members.ms}명`}
                  />
                </div>
              </SectionCard>
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar summary */}
        <aside className="space-y-4">
          <SectionCard title="주요 키워드">
            <div className="flex flex-wrap gap-1.5">
              {lab.keywords.map((k) => (
                <Badge
                  key={k}
                  variant="outline"
                  className="rounded-full border-border bg-[color:var(--surface)] font-normal"
                >
                  {k}
                </Badge>
              ))}
            </div>
          </SectionCard>
          <SectionCard title="연락 · 위치">
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2 text-foreground/80">
                <MapPin className="h-4 w-4 text-muted-foreground" /> {lab.location}
              </li>
              <li className="flex items-center gap-2 text-foreground/80">
                <Mail className="h-4 w-4 text-muted-foreground" /> {lab.email}
              </li>
              <li className="text-xs text-muted-foreground">마지막 업데이트 · {lab.updatedAt}</li>
            </ul>
          </SectionCard>
          <div className="grid grid-cols-1 gap-3 min-[420px]:grid-cols-2">
            <Button
              variant="outline"
              className="h-11 w-full gap-2 rounded-xl border-[color:var(--point)]/30 bg-white text-[color:var(--deep)] hover:bg-[color:var(--point)]/10 hover:text-[color:var(--deep)]"
              onClick={() => {
                const today = new Date();
                const in7 = new Date(today.getTime() + 7 * 86400000);
                const iso = in7.toISOString().slice(0, 10);
                addEvent({
                  title: `${lab.name} 컨택`,
                  kind: "contact",
                  date: iso,
                  labId: lab.id,
                });
                toast.success("지원 캘린더에 컨택 일정을 추가했어요", {
                  description: iso,
                  action: { label: "캘린더 열기", onClick: () => navigate({ to: "/calendar" }) },
                });
              }}
            >
              <CalendarPlus className="h-4 w-4" strokeWidth={1.8} />
              <span className="truncate">지원 일정에 추가</span>
            </Button>
            <Button
              type="button"
              className="h-11 w-full gap-2 rounded-xl bg-[color:var(--point)] text-white hover:bg-[color:var(--deep)]"
              onClick={() => navigate({ to: "/lab/$id/email", params: { id: lab.id } })}
            >
              <Sparkles className="h-4 w-4" strokeWidth={1.8} />
              <span className="truncate">컨택 이메일 작성</span>
            </Button>
          </div>
        </aside>
      </div>

      {/* Similar labs */}
      <section className="mt-10">
        <h2 className="text-base font-semibold text-[color:var(--navy)]">
          이 연구실과 유사한 연구실
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {similar.map((l) => (
            <LabCard key={l.id} lab={l} />
          ))}
        </div>
      </section>
    </AppShell>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-border bg-white p-5">
      <h3 className="text-sm font-semibold text-[color:var(--navy)]">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-[color:var(--surface)] p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold text-[color:var(--navy)]">{value}</div>
    </div>
  );
}
