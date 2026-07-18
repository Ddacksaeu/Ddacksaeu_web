import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Check, FileText, Info, Sparkles, Upload } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  analyzeDocument,
  recomputeRecommendations,
  type DocumentAnalysis,
  type Recommendation,
} from "@/lib/api/recommendations";

export const Route = createFileRoute("/recommendations")({
  component: RecommendationsPage,
  head: () => ({ meta: [{ title: "CV-Based Recommendations 쨌 Ddaksaeu" }] }),
});

type Status = "idle" | "analyzing" | "recommending" | "done" | "error";

function RecommendationsPage() {
  const [status, setStatus] = useState<Status>("idle");
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const run = async (selected: File) => {
    if (selected.type !== "application/pdf" || selected.size > 10 * 1024 * 1024) {
      setError("Upload one text-based PDF no larger than 10 MB.");
      setStatus("error");
      return;
    }
    setFile(selected);
    setError(null);
    setStatus("analyzing");
    try {
      const result = await analyzeDocument(selected);
      setAnalysis(result);
      setStatus("recommending");
      setRecommendations(await recomputeRecommendations());
      setStatus("done");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Analysis failed. Please try again.");
      setStatus("error");
    }
  };

  const reset = () => {
    setStatus("idle");
    setAnalysis(null);
    setRecommendations([]);
    setError(null);
    setFile(null);
  };
  const retry = () => file && run(file);

  return (
    <AppShell
      title="CV-Based Recommendations"
      description="Analyze a PDF CV to find labs that fit your background."
      actions={
        status === "done" ? (
          <Button variant="outline" className="rounded-full" onClick={reset}>
            Analyze another PDF
          </Button>
        ) : undefined
      }
    >
      {(status === "idle" || status === "error") && (
        <section className="rounded-2xl border border-border bg-white p-6 sm:p-10">
          <div className="mx-auto max-w-2xl text-center">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[color:var(--surface)] text-[color:var(--deep)]">
              <Upload className="h-6 w-6" />
            </div>
            <h2 className="mt-4 text-lg font-semibold text-[color:var(--navy)]">
              Upload your CV or portfolio
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              PDF only, up to 10 MB. The backend extracts structured information for review.
            </p>
            <label className="mx-auto mt-6 flex min-h-40 max-w-lg cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border bg-[color:var(--surface)] p-6 transition-colors hover:border-[color:var(--point)]/60">
              <FileText className="h-6 w-6" />
              <span className="text-sm font-medium">Choose a text-based PDF</span>
              <input
                type="file"
                accept="application/pdf,.pdf"
                className="sr-only"
                onChange={(event) => {
                  const next = event.target.files?.[0];
                  if (next) void run(next);
                }}
              />
            </label>
            {error ? (
              <div className="mt-5 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                {error}
                <br />
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={retry}
                  disabled={!file}
                >
                  Retry
                </Button>
              </div>
            ) : null}
            <p className="mt-5 flex justify-center gap-1 text-xs text-muted-foreground">
              <Info className="h-3 w-3" />
              No demo analysis is substituted when the API fails.
            </p>
          </div>
        </section>
      )}
      {(status === "analyzing" || status === "recommending") && (
        <section className="rounded-2xl border border-border bg-white p-8 sm:p-10">
          <div className="mx-auto max-w-md text-center">
            <Sparkles className="mx-auto h-8 w-8 animate-pulse text-[color:var(--point)]" />
            <h2 className="mt-4 text-lg font-semibold">
              {status === "analyzing" ? "Analyzing your PDF" : "Calculating recommendations"}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">This can take a moment.</p>
            <Progress value={status === "analyzing" ? 45 : 80} className="mt-6 h-1.5" />
          </div>
        </section>
      )}
      {status === "done" && analysis && (
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="space-y-6">
            <section className="rounded-2xl border border-border bg-white p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-semibold">Extracted profile</h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    AI-generated extraction — review before making decisions.
                  </p>
                </div>
                <Badge className="rounded-full">Completed</Badge>
              </div>
              <p className="mt-4 text-sm text-foreground/80">{analysis.short_summary}</p>
              <TermGroup title="Research interests" values={analysis.research_interests} />
              <TermGroup title="Keywords" values={analysis.keywords} />
              <TermGroup title="Skills" values={analysis.skills} />
            </section>
            <section>
              <h2 className="text-base font-semibold text-[color:var(--navy)]">Recommended labs</h2>
              <div className="mt-4 space-y-4">
                {recommendations.map((item) => (
                  <article
                    key={item.lab_id}
                    className="rounded-2xl border border-border bg-white p-5"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-xs text-muted-foreground">
                          {item.university} · {item.department}
                        </div>
                        <h3 className="mt-1 text-base font-semibold">{item.lab_name}</h3>
                        <p className="text-sm text-muted-foreground">{item.professor_name}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-semibold">{item.total_score}%</div>
                        <div className="text-xs text-muted-foreground">
                          Confidence {item.confidence}%
                        </div>
                      </div>
                    </div>
                    <p className="mt-3 text-sm">{item.short_reason}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.matched_keywords.map((term) => (
                        <Badge key={term} variant="outline" className="rounded-full">
                          <Check className="mr-1 h-3 w-3" />
                          {term}
                        </Badge>
                      ))}
                      {item.missing_keywords.map((term) => (
                        <Badge key={term} variant="outline" className="rounded-full border-dashed">
                          Gap · {term}
                        </Badge>
                      ))}
                    </div>
                    <details className="mt-4 text-sm">
                      <summary className="cursor-pointer text-[color:var(--deep)]">
                        View score breakdown
                      </summary>
                      <ul className="mt-2 space-y-1 text-muted-foreground">
                        {Object.entries(item.score_breakdown).map(([name, part]) => (
                          <li key={name}>
                            {name}:{" "}
                            {part.unavailable
                              ? "unavailable"
                              : `${part.score} points (${part.contribution.toFixed(1)} contribution)`}
                          </li>
                        ))}
                      </ul>
                    </details>
                    <p className="mt-3 text-xs text-muted-foreground">
                      Next step: {item.recommended_action}
                    </p>
                    <Button asChild size="sm" className="mt-4 rounded-full">
                      <Link to="/lab/$id" params={{ id: item.lab_id }}>
                        View details
                      </Link>
                    </Button>
                  </article>
                ))}
              </div>
            </section>
          </div>
          <aside className="space-y-4">
            <section className="rounded-2xl border border-border bg-white p-5">
              <h3 className="font-semibold">Analysis summary</h3>
              <div className="mt-3 space-y-2 text-sm">
                <p>Keywords: {analysis.keywords.length}</p>
                <p>Skills: {analysis.skills.length}</p>
                <p>Projects: {analysis.projects.length}</p>
                <p>Recommendations: {recommendations.length}</p>
              </div>
            </section>
            {analysis.missing_information.length ? (
              <section className="rounded-2xl border border-[color:var(--point)]/30 bg-[color:var(--point)]/5 p-5">
                <h3 className="font-semibold">Improve your profile</h3>
                <ul className="mt-2 text-sm">
                  {analysis.missing_information.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            ) : null}
          </aside>
        </div>
      )}
    </AppShell>
  );
}

function TermGroup({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="mt-5">
      <div className="text-xs uppercase tracking-widest text-muted-foreground">{title}</div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {values.length ? (
          values.map((value) => (
            <Badge key={value} variant="outline" className="rounded-full">
              {value}
            </Badge>
          ))
        ) : (
          <span className="text-sm text-muted-foreground">Not found</span>
        )}
      </div>
    </div>
  );
}
