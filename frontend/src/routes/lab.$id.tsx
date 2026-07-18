import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { CalendarPlus, ExternalLink, Heart, MapPin, Mail, Sparkles, Users } from "lucide-react";
import { LabCard, MatchBar } from "@/components/lab/LabCard";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { labQueryOptions, similarLabsQueryOptions } from "@/lib/api/labs";
import { useAppState } from "@/lib/app-state";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/lab/$id")({
  component: LabDetailPage,
  head: () => ({
    meta: [
      { title: "Lab details 쨌 Ddaksaeu" },
      { name: "description", content: "Research lab details with source provenance." },
    ],
  }),
});

function LabDetailPage() {
  const { id } = Route.useParams();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const labQuery = useQuery(labQueryOptions(id));
  const similarQuery = useQuery({ ...similarLabsQueryOptions(id), enabled: labQuery.isSuccess });
  const { isFavorite, toggleFavorite, addEvent } = useAppState();
  const navigate = useNavigate();

  if (pathname.startsWith(`/lab/${id}/email`)) return <Outlet />;

  if (labQuery.isLoading) {
    return (
      <AppShell title="Loading lab" description="Loading verified lab information.">
        <div className="h-96 animate-pulse rounded-2xl bg-[color:var(--surface)]" />
      </AppShell>
    );
  }

  if (labQuery.isError || !labQuery.data) {
    return (
      <AppShell title="Lab unavailable" description="The lab details could not be loaded.">
        <Button asChild variant="outline" className="rounded-full">
          <Link to="/">Back to search</Link>
        </Button>
      </AppShell>
    );
  }

  const lab = labQuery.data;
  const facts = (type: string) =>
    lab.facts.flatMap((fact) => (fact.factType === type && fact.valueText ? [fact.valueText] : []));
  const memberCount = (audience: string) =>
    lab.facts.find((fact) => fact.factType === "member_count" && fact.audience === audience)
      ?.valueNumber;
  const hasSource = lab.sourceUrl || lab.sourceCheckedAt;
  const favorite = lab.isFavorite || isFavorite(lab.id);

  return (
    <AppShell
      title={lab.name}
      description={`${lab.professorName} 쨌 ${lab.department}`}
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
                favorite && "fill-[color:var(--point)] text-[color:var(--point)]",
              )}
            />
            {favorite ? "Saved" : "Save lab"}
          </Button>
          <Button
            variant="outline"
            className="gap-2 rounded-full"
            onClick={() => {
              const date = new Date(Date.now() + 7 * 86_400_000).toISOString().slice(0, 10);
              addEvent({ title: `${lab.name} contact`, kind: "contact", date, labId: lab.id });
              toast.success("Contact reminder added", { description: date });
            }}
          >
            <CalendarPlus className="h-4 w-4" />
            Add reminder
          </Button>
          <Button
            className="gap-2 rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)]"
            onClick={() => navigate({ to: "/lab/$id/email", params: { id: lab.id } })}
          >
            <Sparkles className="h-4 w-4" />
            Draft email
          </Button>
        </>
      }
    >
      <nav className="mb-4 flex items-center gap-2 text-xs text-muted-foreground">
        <Link to="/" className="hover:text-[color:var(--deep)]">
          Lab search
        </Link>
        <span>›</span>
        <span>{lab.department}</span>
        <span>›</span>
        <span>{lab.name}</span>
      </nav>

      <section className="rounded-2xl border border-border bg-white p-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="rounded-full">
            {lab.field}
          </Badge>
          {lab.recommendationScore !== null ? (
            <MatchBar score={lab.recommendationScore} />
          ) : (
            <span className="text-xs text-muted-foreground">No profile score yet</span>
          )}
        </div>
        <p className="mt-4 text-sm leading-relaxed text-foreground/85">
          {lab.summary ?? "No verified lab summary is available yet."}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {lab.keywords.map((keyword) => (
            <Badge key={keyword} variant="outline" className="rounded-full">
              {keyword}
            </Badge>
          ))}
        </div>
        {hasSource ? (
          <p className="mt-4 text-xs text-muted-foreground">
            Source: {lab.sourceUrl ?? "not provided"} · Last verified:{" "}
            {lab.sourceCheckedAt
              ? new Date(lab.sourceCheckedAt).toLocaleDateString()
              : "not provided"}
          </p>
        ) : null}
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <InfoCard
            title="Research topics"
            values={facts("recent_topic")}
            empty="No verified current topics are available."
          />
          <InfoCard
            title="Applicant expectations"
            values={facts("requirement")}
            empty="No verified requirements are available."
          />
          <section className="rounded-2xl border border-border bg-white p-5">
            <h2 className="text-sm font-semibold text-[color:var(--navy)]">Papers</h2>
            {lab.papers.length === 0 ? (
              <Empty text="No verified papers are available." />
            ) : (
              <ul className="mt-3 divide-y divide-border">
                {lab.papers.map((paper) => (
                  <li key={paper.id} className="py-3 first:pt-0">
                    <div className="text-sm font-medium text-[color:var(--navy)]">
                      {paper.title}
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {paper.venue} · {paper.publishedYear}
                    </div>
                    {paper.sourceUrl ? (
                      <a
                        className="mt-1 inline-block text-xs text-[color:var(--deep)] underline"
                        href={paper.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Source
                      </a>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="space-y-4">
          <section className="rounded-2xl border border-border bg-white p-5">
            <h2 className="text-sm font-semibold text-[color:var(--navy)]">Contact and location</h2>
            <div className="mt-3 space-y-2 text-sm text-foreground/80">
              <div className="flex gap-2">
                <MapPin className="h-4 w-4 shrink-0" />
                {lab.location ?? "Unavailable"}
              </div>
              <div className="flex gap-2">
                <Mail className="h-4 w-4 shrink-0" />
                {lab.contactEmail ?? "Unavailable"}
              </div>
            </div>
            {lab.homepageUrl ? (
              <Button asChild variant="outline" className="mt-4 w-full gap-2 rounded-xl">
                <a href={lab.homepageUrl} target="_blank" rel="noreferrer">
                  <ExternalLink className="h-4 w-4" />
                  Website
                </a>
              </Button>
            ) : null}
          </section>
          <section className="rounded-2xl border border-border bg-white p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-[color:var(--navy)]">
              <Users className="h-4 w-4" />
              Team
            </h2>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs text-muted-foreground">
              <div>
                Professor
                <br />
                <strong>{memberCount("professor") ?? "—"}</strong>
              </div>
              <div>
                PhD
                <br />
                <strong>{memberCount("phd") ?? "—"}</strong>
              </div>
              <div>
                MS
                <br />
                <strong>{memberCount("ms") ?? "—"}</strong>
              </div>
            </div>
          </section>
        </aside>
      </div>

      <section className="mt-10">
        <h2 className="text-base font-semibold text-[color:var(--navy)]">Similar labs</h2>
        {similarQuery.isLoading ? (
          <div className="mt-4 h-48 animate-pulse rounded-2xl bg-[color:var(--surface)]" />
        ) : null}
        {similarQuery.isError ? (
          <p className="mt-3 text-sm text-muted-foreground">Similar labs could not be loaded.</p>
        ) : null}
        {similarQuery.data?.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">No related labs are available.</p>
        ) : null}
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {similarQuery.data?.map((item) => (
            <LabCard key={item.id} lab={item} />
          ))}
        </div>
      </section>
    </AppShell>
  );
}

function InfoCard({ title, values, empty }: { title: string; values: string[]; empty: string }) {
  return (
    <section className="rounded-2xl border border-border bg-white p-5">
      <h2 className="text-sm font-semibold text-[color:var(--navy)]">{title}</h2>
      {values.length ? (
        <ul className="mt-3 space-y-2 text-sm">
          {values.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      ) : (
        <Empty text={empty} />
      )}
    </section>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="mt-3 text-sm text-muted-foreground">{text}</p>;
}
