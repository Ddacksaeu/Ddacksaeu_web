import {
  createFileRoute,
  Link,
  notFound,
  Outlet,
  useNavigate,
  useRouterState,
} from "@tanstack/react-router";
import {
  CalendarPlus,
  ChevronRight,
  ExternalLink,
  Heart,
  Mail,
  MapPin,
  Sparkles,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
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
    const lab = LABS.find((item) => item.id === params.id);
    if (!lab) throw notFound();
    return { lab } satisfies { lab: Lab };
  },
  component: LabDetail,
  head: ({ loaderData }) => ({
    meta: [
      { title: loaderData ? loaderData.lab.name + " · Ddaksaeu" : "Lab details · Ddaksaeu" },
      {
        name: "description",
        content: loaderData?.lab.summary ?? "Explore laboratory research details.",
      },
    ],
  }),
});

function LabDetail() {
  const { lab } = Route.useLoaderData() as { lab: Lab };
  const { isFavorite, toggleFavorite, addEvent } = useAppState();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const isSaved = isFavorite(lab.id);
  const similarLabs = getSimilarLabs(lab);
  const matchedKeywords = ["Computer Vision", "Multimodal", "Diffusion Model"].filter((keyword) =>
    lab.keywords.some((labKeyword) => labKeyword.toLowerCase().includes(keyword.toLowerCase())),
  );

  if (pathname.startsWith("/lab/" + lab.id + "/email")) {
    return <Outlet />;
  }

  const addContactReminder = () => {
    const reminderDate = new Date(Date.now() + 7 * 86_400_000).toISOString().slice(0, 10);
    addEvent({
      title: "Contact " + lab.professor,
      kind: "contact",
      date: reminderDate,
      labId: lab.id,
    });
    toast.success("Contact reminder added", {
      description: reminderDate,
      action: {
        label: "Open calendar",
        onClick: () => navigate({ to: "/calendar" }),
      },
    });
  };

  return (
    <AppShell
      title={lab.name}
      description={lab.professor + " · " + lab.department}
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
                isSaved && "fill-[color:var(--point)] text-[color:var(--point)]",
              )}
            />
            {isSaved ? "Saved" : "Save lab"}
          </Button>
          <Button asChild className="gap-2 rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)]">
            <a href={lab.homepage} target="_blank" rel="noreferrer">
              <ExternalLink className="h-4 w-4" /> Website
            </a>
          </Button>
        </>
      }
    >
      <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-1.5 text-xs text-muted-foreground">
        <Link to="/" className="hover:text-[color:var(--deep)]">Explore Labs</Link>
        <ChevronRight className="h-3 w-3" />
        <span>{lab.department}</span>
        <ChevronRight className="h-3 w-3" />
        <span className="text-[color:var(--navy)]">{lab.name}</span>
      </nav>

      <section className="rounded-2xl border border-border bg-white p-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className="rounded-full border border-[color:var(--point)]/30 bg-[color:var(--point)]/10 text-[color:var(--deep)] hover:bg-[color:var(--point)]/10">
            {lab.matchScore}% match with your profile
          </Badge>
          <Badge variant="outline" className="rounded-full border-border bg-[color:var(--surface)] font-normal text-foreground/70">
            {lab.field}
          </Badge>
          <span className="text-xs text-muted-foreground">Updated {lab.updatedAt}</span>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_260px] sm:items-start">
          <p className="text-sm leading-relaxed text-foreground/85">{lab.summary}</p>
          <div className="rounded-xl bg-[color:var(--surface)] p-4">
            <div className="text-[11px] uppercase tracking-widest text-muted-foreground">Profile match</div>
            <div className="mt-2 text-3xl font-semibold tabular-nums text-[color:var(--navy)]">
              {lab.matchScore}%
            </div>
            <div className="mt-2"><MatchBar score={lab.matchScore} /></div>
            {matchedKeywords.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {matchedKeywords.map((keyword) => (
                  <span key={keyword} className="rounded-full border border-[color:var(--point)]/30 bg-[color:var(--point)]/10 px-2 py-0.5 text-[11px] text-[color:var(--deep)]">
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          <Tabs defaultValue="overview">
            <TabsList className="rounded-full bg-[color:var(--surface)] p-1">
              <TabsTrigger value="overview" className="rounded-full data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm">
                Overview
              </TabsTrigger>
              <TabsTrigger value="research" className="rounded-full data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm">
                Research
              </TabsTrigger>
              <TabsTrigger value="papers" className="rounded-full data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm">
                Papers
              </TabsTrigger>
              <TabsTrigger value="people" className="rounded-full data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm">
                People
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-5 space-y-5">
              <SectionCard title="About this lab">
                <p className="text-sm leading-relaxed text-foreground/85">{lab.summary}</p>
              </SectionCard>
              <SectionCard title="Core research areas">
                <div className="flex flex-wrap gap-1.5">
                  {lab.keywords.map((keyword) => (
                    <Badge key={keyword} variant="outline" className="rounded-full border-border bg-[color:var(--surface)] font-normal">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </SectionCard>
              <SectionCard title="Current topics">
                <BulletList items={lab.recentTopics} />
              </SectionCard>
              <SectionCard title="What the lab values">
                <BulletList items={lab.requirements} accent="deep" />
              </SectionCard>
            </TabsContent>

            <TabsContent value="research" className="mt-5">
              <SectionCard title="Research directions">
                <div className="grid gap-3 sm:grid-cols-2">
                  {lab.recentTopics.map((topic, index) => (
                    <div key={topic} className="rounded-xl border border-border bg-[color:var(--surface)] p-4">
                      <div className="text-xs uppercase tracking-widest text-muted-foreground">Direction {index + 1}</div>
                      <div className="mt-1 text-sm font-medium text-[color:var(--navy)]">{topic}</div>
                    </div>
                  ))}
                </div>
              </SectionCard>
            </TabsContent>

            <TabsContent value="papers" className="mt-5">
              <SectionCard title={"Recent papers · " + lab.papers.length}>
                <ul className="divide-y divide-border">
                  {lab.papers.map((paper) => (
                    <li key={paper.title} className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-[color:var(--navy)]">{paper.title}</div>
                        <div className="mt-0.5 text-xs text-muted-foreground">{paper.venue} · {paper.year}</div>
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {paper.keywords.map((keyword) => (
                            <span key={keyword} className="rounded-full bg-[color:var(--surface)] px-2 py-0.5 text-[11px] text-foreground/70">
                              {keyword}
                            </span>
                          ))}
                        </div>
                      </div>
                      <span className="shrink-0 rounded-full border border-border px-2 py-0.5 text-[11px] tabular-nums text-muted-foreground">
                        {paper.year}
                      </span>
                    </li>
                  ))}
                </ul>
              </SectionCard>
            </TabsContent>

            <TabsContent value="people" className="mt-5">
              <SectionCard title="Lab members">
                <div className="grid grid-cols-3 gap-3">
                  <Stat icon={<Users className="h-4 w-4" />} label="Professor" value={String(lab.members.professor)} />
                  <Stat icon={<Users className="h-4 w-4" />} label="PhD students" value={String(lab.members.phd)} />
                  <Stat icon={<Users className="h-4 w-4" />} label="MS students" value={String(lab.members.ms)} />
                </div>
              </SectionCard>
            </TabsContent>
          </Tabs>
        </div>

        <aside className="space-y-4">
          <SectionCard title="Keywords">
            <div className="flex flex-wrap gap-1.5">
              {lab.keywords.map((keyword) => (
                <Badge key={keyword} variant="outline" className="rounded-full border-border bg-[color:var(--surface)] font-normal">
                  {keyword}
                </Badge>
              ))}
            </div>
          </SectionCard>
          <SectionCard title="Contact and location">
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2 text-foreground/80"><MapPin className="h-4 w-4 text-muted-foreground" /> {lab.location}</li>
              <li className="flex items-center gap-2 text-foreground/80"><Mail className="h-4 w-4 text-muted-foreground" /> {lab.email}</li>
              <li className="text-xs text-muted-foreground">Last updated · {lab.updatedAt}</li>
            </ul>
          </SectionCard>
          <div className="grid gap-3 min-[420px]:grid-cols-2 lg:grid-cols-1">
            <Button variant="outline" className="h-11 w-full gap-2 rounded-xl border-[color:var(--point)]/30 bg-white text-[color:var(--deep)] hover:bg-[color:var(--point)]/10 hover:text-[color:var(--deep)]" onClick={addContactReminder}>
              <CalendarPlus className="h-4 w-4" strokeWidth={1.8} /> Add contact reminder
            </Button>
            <Button type="button" className="h-11 w-full gap-2 rounded-xl bg-[color:var(--point)] text-white hover:bg-[color:var(--deep)]" onClick={() => navigate({ to: "/lab/$id/email", params: { id: lab.id } })}>
              <Sparkles className="h-4 w-4" strokeWidth={1.8} /> Write outreach email
            </Button>
          </div>
        </aside>
      </div>

      <section className="mt-10">
        <h2 className="text-base font-semibold text-[color:var(--navy)]">Similar labs</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {similarLabs.map((similarLab) => <LabCard key={similarLab.id} lab={similarLab} />)}
        </div>
      </section>
    </AppShell>
  );
}

function getSimilarLabs(lab: Lab) {
  const sameField = LABS.filter((item) => item.id !== lab.id && item.field === lab.field).slice(0, 3);
  return sameField.length > 0 ? sameField : LABS.filter((item) => item.id !== lab.id).slice(0, 3);
}

function SectionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-border bg-white p-5">
      <h3 className="text-sm font-semibold text-[color:var(--navy)]">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function BulletList({ items, accent = "point" }: { items: string[]; accent?: "point" | "deep" }) {
  return (
    <ul className="space-y-2 text-sm">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-2">
          <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", accent === "deep" ? "bg-[color:var(--deep)]" : "bg-[color:var(--point)]")} />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function Stat({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl bg-[color:var(--surface)] p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">{icon} {label}</div>
      <div className="mt-2 text-xl font-semibold text-[color:var(--navy)]">{value}</div>
    </div>
  );
}
