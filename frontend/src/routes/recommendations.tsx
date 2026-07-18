import { createFileRoute } from "@tanstack/react-router";
import { Upload, FileText, X, Sparkles, Check, Info, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { LabCard, MatchBar } from "@/components/lab/LabCard";
import { LABS, USER_PROFILE } from "@/lib/mock-data";
import { useAppState, type CVAnalysis } from "@/lib/app-state";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/recommendations")({
  component: RecPage,
  head: () => ({
    meta: [
      { title: "CV-Based Recommendations · Ddaksaeu" },
      { name: "description", content: "Upload your CV to receive POSTECH lab recommendations matched to your interests." },
    ],
  }),
});

const DEMO_CV: CVAnalysis = {
  keywords: ["Computer Vision", "Multimodal", "Diffusion Model", "3D Vision", "Representation Learning"],
  skills: ["Python", "PyTorch", "OpenCV", "CUDA", "Git"],
  methodologies: ["Deep Learning", "Generative Models", "Representation Learning"],
  projects: USER_PROFILE.projects,
  completeness: 82,
};

type Status = "idle" | "uploading" | "analyzing" | "done";

function RecPage() {
  const { cv, setCV } = useAppState();
  const [status, setStatus] = useState<Status>(cv ? "done" : "idle");
  const [progress, setProgress] = useState(0);
  const [newKeyword, setNewKeyword] = useState("");

  useEffect(() => {
    if (status !== "analyzing") return;
    setProgress(0);
    const start = Date.now();
    const iv = setInterval(() => {
      const p = Math.min(100, ((Date.now() - start) / 1600) * 100);
      setProgress(p);
      if (p >= 100) {
        clearInterval(iv);
        setCV(DEMO_CV);
        setStatus("done");
        toast.success("Analysis complete");
      }
    }, 80);
    return () => clearInterval(iv);
  }, [status, setCV]);

  const startAnalysis = () => setStatus("analyzing");
  const reset = () => {
    setCV(null);
    setStatus("idle");
  };

  const addKeyword = () => {
    const k = newKeyword.trim();
    if (!k || !cv) return;
    setCV({ ...cv, keywords: [...cv.keywords, k] });
    setNewKeyword("");
  };
  const removeKeyword = (k: string) => {
    if (!cv) return;
    setCV({ ...cv, keywords: cv.keywords.filter((x) => x !== k) });
  };

  // Recommendations: score labs against cv keywords
  const recs = cv
    ? [...LABS]
        .map((l) => {
          const matches = l.keywords.filter((k) =>
            cv.keywords.some(
              (u) =>
                k.toLowerCase().includes(u.toLowerCase()) ||
                u.toLowerCase().includes(k.toLowerCase()),
            ),
          );
          const missing = ["Reasoning", "Alignment", "Robotics"].filter(
            (m) => l.keywords.some((k) => k.toLowerCase().includes(m.toLowerCase())) && !cv.keywords.some((u) => u.toLowerCase().includes(m.toLowerCase())),
          );
          const score = Math.min(99, 40 + matches.length * 12 + Math.round(l.matchScore * 0.3));
          return { lab: l, matches, missing, score };
        })
        .sort((a, b) => b.score - a.score)
        .slice(0, 5)
    : [];

  return (
    <AppShell
      title="CV-Based Recommendations"
      description="Analyze your CV and personal statement to find labs that fit you."
      actions={
        status === "done" ? (
          <Button variant="outline" className="rounded-full" onClick={reset}>
            Analyze again
          </Button>
        ) : undefined
      }
    >
      {status === "idle" && (
        <section className="rounded-2xl border border-border bg-white p-6 sm:p-10">
          <div className="mx-auto max-w-2xl text-center">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[color:var(--surface)] text-[color:var(--deep)]">
              <Upload className="h-6 w-6" />
            </div>
            <h2 className="mt-4 text-lg font-semibold text-[color:var(--navy)]">
              Upload your CV or personal statement
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              PDF and DOCX are supported. Personal data is not sent to a server in this demo.
            </p>

            <label
              htmlFor="cv-upload"
              className="mx-auto mt-6 flex min-h-40 max-w-lg cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border bg-[color:var(--surface)] p-6 text-center transition-colors hover:border-[color:var(--point)]/60 hover:bg-[color:var(--point)]/5"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                setStatus("uploading");
                setTimeout(() => setStatus("analyzing"), 700);
              }}
            >
              <FileText className="h-6 w-6 text-[color:var(--deep)]" />
              <div className="text-sm font-medium text-[color:var(--navy)]">
                Drop your file here
              </div>
              <div className="text-xs text-muted-foreground">or click to browse · up to 10 MB</div>
              <input
                id="cv-upload"
                type="file"
                accept=".pdf,.docx"
                className="sr-only"
                onChange={() => {
                  setStatus("uploading");
                  setTimeout(() => setStatus("analyzing"), 700);
                }}
              />
            </label>

            <div className="mt-5 flex flex-col items-center gap-2">
              <Button
                onClick={startAnalysis}
                size="lg"
                className="gap-2 rounded-full bg-[color:var(--point)] px-6 hover:bg-[color:var(--deep)]"
              >
                <Sparkles className="h-4 w-4" /> Analyze demo CV
              </Button>
              <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                <Info className="h-3 w-3" /> Preview the analysis with demo data
              </p>
            </div>
          </div>
        </section>
      )}

      {(status === "uploading" || status === "analyzing") && (
        <section className="rounded-2xl border border-border bg-white p-8 sm:p-10">
          <div className="mx-auto max-w-md text-center">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[color:var(--point)]/10 text-[color:var(--point)]">
              <Sparkles className="h-6 w-6 animate-pulse" />
            </div>
            <h2 className="mt-4 text-lg font-semibold text-[color:var(--navy)]">
              {status === "uploading" ? "Uploading file" : "Analyzing your CV"}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Extracting research interests and skills…
            </p>
            <div className="mt-6">
              <Progress value={status === "analyzing" ? progress : 30} className="h-1.5" />
            </div>
            <div className="mt-6 grid gap-2 text-left">
              {["Extract text", "Identify keywords", "Match labs"].map((s, i) => (
                <div key={s} className="flex items-center gap-2 text-sm">
                  <span
                    className={cn(
                      "grid h-5 w-5 place-items-center rounded-full border text-[10px]",
                      progress > (i + 1) * 30
                        ? "border-[color:var(--point)] bg-[color:var(--point)] text-white"
                        : "border-border text-muted-foreground",
                    )}
                  >
                    {progress > (i + 1) * 30 ? <Check className="h-3 w-3" /> : i + 1}
                  </span>
                  <span className="text-foreground/80">{s}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="mx-auto mt-8 grid max-w-2xl gap-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-16 rounded-xl" />
            ))}
          </div>
        </section>
      )}

      {status === "done" && cv && (
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="space-y-6">
            <section className="rounded-2xl border border-border bg-white p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-[color:var(--navy)]">
                    Analyzed profile
                  </h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    You can add or remove keywords
                  </p>
                </div>
                <Badge className="rounded-full border border-[color:var(--point)]/30 bg-[color:var(--point)]/10 text-[color:var(--deep)] hover:bg-[color:var(--point)]/10">
                  Completeness {cv.completeness}%
                </Badge>
              </div>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <ChipGroup label="Research interests" items={cv.keywords} removable onRemove={removeKeyword} />
                <ChipGroup label="Skills" items={cv.skills} />
                <ChipGroup label="Research methods" items={cv.methodologies} />
                <div>
                  <div className="text-[11px] uppercase tracking-widest text-muted-foreground">
                    Project experience
                  </div>
                  <ul className="mt-2 space-y-1.5 text-sm">
                    {cv.projects.map((p) => (
                      <li key={p} className="flex items-start gap-2">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--point)]" />
                        <span className="text-foreground/85">{p}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap items-center gap-2 rounded-xl bg-[color:var(--surface)] p-3">
                <input
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addKeyword()}
                  placeholder="Add keyword (e.g. Multimodal)"
                  className="min-w-0 flex-1 border-0 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                />
                <Button size="sm" onClick={addKeyword} className="gap-1 rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)]">
                  <Plus className="h-3.5 w-3.5" /> Add
                </Button>
              </div>
            </section>

            <section>
              <div className="flex items-end justify-between">
                <div>
                  <h2 className="text-base font-semibold text-[color:var(--navy)]">Recommended labs</h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Ranked by match with your profile
                  </p>
                </div>
              </div>
              <div className="mt-4 space-y-4">
                {recs.map((r) => (
                  <div key={r.lab.id} className="rounded-2xl border border-border bg-white p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-xs text-muted-foreground">
                          {r.lab.department} · {r.lab.field}
                        </div>
                        <h3 className="mt-1 text-base font-semibold text-[color:var(--navy)]">
                          {r.lab.name}
                        </h3>
                        <div className="mt-0.5 text-sm text-muted-foreground">{r.lab.professor}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-semibold tabular-nums text-[color:var(--navy)]">
                          {r.score}%
                        </div>
                        <MatchBar score={r.score} />
                      </div>
                    </div>
                    <div className="mt-3 rounded-xl bg-[color:var(--surface)] p-3">
                      <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                        Why this recommendation?
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {r.matches.slice(0, 5).map((k) => (
                          <span
                            key={k}
                            className="inline-flex items-center gap-1 rounded-full border border-[color:var(--point)]/30 bg-[color:var(--point)]/10 px-2.5 py-0.5 text-[11px] text-[color:var(--deep)]"
                          >
                            <Check className="h-3 w-3" /> {k}
                          </span>
                        ))}
                        {r.missing.slice(0, 3).map((k) => (
                          <span
                            key={k}
                            className="inline-flex items-center gap-1 rounded-full border border-dashed border-border bg-white px-2.5 py-0.5 text-[11px] text-muted-foreground"
                          >
                            Gap · {k}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap justify-end gap-2">
                      <Button asChild variant="outline" size="sm" className="rounded-full">
                        <a href={r.lab.homepage} target="_blank" rel="noreferrer">Website</a>
                      </Button>
                      <Button asChild size="sm" className="rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)]">
                        <a href={`/lab/${r.lab.id}`}>View details</a>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <aside className="space-y-4">
            <section className="rounded-2xl border border-border bg-white p-5">
              <h3 className="text-sm font-semibold text-[color:var(--navy)]">Analysis summary</h3>
              <div className="mt-3 space-y-3 text-sm">
                <SummaryRow label="Extracted keywords" value={`${cv.keywords.length}`} />
                <SummaryRow label="Skills" value={`${cv.skills.length}`} />
                <SummaryRow label="Projects" value={`${cv.projects.length}`} />
                <SummaryRow label="Recommended labs" value={`${recs.length}`} />
              </div>
            </section>
            <section className="rounded-2xl border border-[color:var(--point)]/30 bg-[color:var(--point)]/5 p-5">
              <div className="text-[11px] font-medium uppercase tracking-widest text-[color:var(--deep)]">
                Tip
              </div>
              <p className="mt-1 text-sm text-foreground/85">
                Add at least two representative projects to improve recommendation accuracy.
              </p>
            </section>
          </aside>
        </div>
      )}
    </AppShell>
  );
}

function ChipGroup({
  label,
  items,
  removable,
  onRemove,
}: {
  label: string;
  items: string[];
  removable?: boolean;
  onRemove?: (v: string) => void;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {items.map((k) => (
          <span
            key={k}
            className="inline-flex items-center gap-1 rounded-full border border-border bg-[color:var(--surface)] px-2.5 py-1 text-xs text-foreground/80"
          >
            {k}
            {removable && (
              <button
                onClick={() => onRemove?.(k)}
                aria-label={`${k} Remove`}
                className="text-muted-foreground hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-[color:var(--navy)]">{value}</span>
    </div>
  );
}
