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
      { title: "CV 기반 맞춤 추천 · 딱새우" },
      {
        name: "description",
        content: "CV를 업로드하면 연구 관심사에 맞는 포스텍 연구실을 추천해드립니다.",
      },
    ],
  }),
});

const DEMO_CV: CVAnalysis = {
  keywords: [
    "Computer Vision",
    "Multimodal",
    "Diffusion Model",
    "3D Vision",
    "Representation Learning",
  ],
  skills: ["Python", "PyTorch", "OpenCV", "CUDA", "Git"],
  methodologies: ["딥러닝", "생성 모델", "표현 학습"],
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
        toast.success("분석이 완료됐어요");
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
            (m) =>
              l.keywords.some((k) => k.toLowerCase().includes(m.toLowerCase())) &&
              !cv.keywords.some((u) => u.toLowerCase().includes(m.toLowerCase())),
          );
          const score = Math.min(99, 40 + matches.length * 12 + Math.round(l.matchScore * 0.3));
          return { lab: l, matches, missing, score };
        })
        .sort((a, b) => b.score - a.score)
        .slice(0, 5)
    : [];

  return (
    <AppShell
      title="CV 기반 맞춤 추천"
      description="이력서와 자소서를 분석해 나에게 맞는 연구실을 골라드립니다."
      actions={
        status === "done" ? (
          <Button variant="outline" className="rounded-full" onClick={reset}>
            다시 분석하기
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
              CV 또는 자기소개서를 업로드하세요
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              PDF · DOCX 형식을 지원합니다. 개인정보는 이 데모에서 서버로 전송되지 않습니다.
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
                파일을 여기로 끌어다 놓기
              </div>
              <div className="text-xs text-muted-foreground">또는 클릭하여 선택 · 최대 10MB</div>
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
                <Sparkles className="h-4 w-4" /> 데모 CV로 분석해보기
              </Button>
              <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                <Info className="h-3 w-3" /> 데모 데이터를 사용해 분석 화면을 미리 볼 수 있어요
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
              {status === "uploading" ? "파일 업로드 중" : "CV를 분석하고 있어요"}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              연구 관심사와 기술 스택을 추출하고 있어요…
            </p>
            <div className="mt-6">
              <Progress value={status === "analyzing" ? progress : 30} className="h-1.5" />
            </div>
            <div className="mt-6 grid gap-2 text-left">
              {["텍스트 추출", "키워드 인식", "연구실 매칭"].map((s, i) => (
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
                    분석된 내 프로필
                  </h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    키워드는 추가하거나 삭제할 수 있어요
                  </p>
                </div>
                <Badge className="rounded-full border border-[color:var(--point)]/30 bg-[color:var(--point)]/10 text-[color:var(--deep)] hover:bg-[color:var(--point)]/10">
                  완성도 {cv.completeness}%
                </Badge>
              </div>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <ChipGroup
                  label="연구 관심사"
                  items={cv.keywords}
                  removable
                  onRemove={removeKeyword}
                />
                <ChipGroup label="기술 스택" items={cv.skills} />
                <ChipGroup label="연구 방법론" items={cv.methodologies} />
                <div>
                  <div className="text-[11px] uppercase tracking-widest text-muted-foreground">
                    프로젝트 경험
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
                  placeholder="키워드 추가 (예: Multimodal)"
                  className="min-w-0 flex-1 border-0 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                />
                <Button
                  size="sm"
                  onClick={addKeyword}
                  className="gap-1 rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)]"
                >
                  <Plus className="h-3.5 w-3.5" /> 추가
                </Button>
              </div>
            </section>

            <section>
              <div className="flex items-end justify-between">
                <div>
                  <h2 className="text-base font-semibold text-[color:var(--navy)]">추천 연구실</h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    내 프로필과 일치율이 높은 순서로 정렬돼 있어요
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
                        <div className="mt-0.5 text-sm text-muted-foreground">
                          {r.lab.professor}
                        </div>
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
                        왜 추천되었나요?
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
                            보완 · {k}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap justify-end gap-2">
                      <Button asChild variant="outline" size="sm" className="rounded-full">
                        <a href={r.lab.homepage} target="_blank" rel="noreferrer">
                          홈페이지
                        </a>
                      </Button>
                      <Button
                        asChild
                        size="sm"
                        className="rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)]"
                      >
                        <a href={`/lab/${r.lab.id}`}>자세히 보기</a>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <aside className="space-y-4">
            <section className="rounded-2xl border border-border bg-white p-5">
              <h3 className="text-sm font-semibold text-[color:var(--navy)]">분석 요약</h3>
              <div className="mt-3 space-y-3 text-sm">
                <SummaryRow label="추출 키워드" value={`${cv.keywords.length}개`} />
                <SummaryRow label="기술 스택" value={`${cv.skills.length}개`} />
                <SummaryRow label="프로젝트" value={`${cv.projects.length}건`} />
                <SummaryRow label="추천 연구실" value={`${recs.length}개`} />
              </div>
            </section>
            <section className="rounded-2xl border border-[color:var(--point)]/30 bg-[color:var(--point)]/5 p-5">
              <div className="text-[11px] font-medium uppercase tracking-widest text-[color:var(--deep)]">
                Tip
              </div>
              <p className="mt-1 text-sm text-foreground/85">
                프로필에 대표 프로젝트를 2개 이상 추가하면 추천 정확도가 크게 올라갑니다.
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
                aria-label={`${k} 제거`}
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
