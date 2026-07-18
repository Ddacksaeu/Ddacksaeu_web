import { createFileRoute } from "@tanstack/react-router";
import {
  Check,
  Plus,
  X,
  Sparkles,
  Circle,
  Pencil,
  Info,
  GripVertical,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  INTEREST_SUGGESTIONS,
  PROGRAM_OPTIONS,
  SKILL_SUGGESTIONS,
  STATUS_OPTIONS,
  type UserProfile,
} from "@/lib/mock-data";
import { useAppState } from "@/lib/app-state";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/profile")({
  component: ProfilePage,
  head: () => ({
    meta: [
      { title: "내 프로필 · 딱새우" },
      { name: "description", content: "관심 분야, 기술 스택, CV 분석 결과를 관리합니다." },
    ],
  }),
});

function ProfilePage() {
  const { cv, profile, updateProfile } = useAppState();
  const [editOpen, setEditOpen] = useState(false);

  const interests = profile.interests;
  const skills = profile.skills;

  const checklist = [
    { label: "이름·소속 입력", done: !!profile.name && !!profile.affiliation },
    { label: "현재 상태 · 희망 과정 선택", done: !!profile.status && !!profile.program },
    { label: "관심 연구 분야 3개 이상", done: interests.length >= 3 },
    { label: "보유 기술 3개 이상", done: skills.length >= 3 },
    { label: "CV 업로드 및 분석", done: !!cv },
  ];
  const completion = Math.round((checklist.filter((c) => c.done).length / checklist.length) * 100);

  const removeInterest = (t: string) =>
    updateProfile({ interests: interests.filter((x) => x !== t) });
  const addInterest = (t: string) => {
    const v = t.trim();
    if (!v || interests.includes(v)) return;
    updateProfile({ interests: [...interests, v] });
  };
  const removeSkill = (t: string) => updateProfile({ skills: skills.filter((x) => x !== t) });
  const addSkill = (t: string) => {
    const v = t.trim();
    if (!v || skills.includes(v)) return;
    updateProfile({ skills: [...skills, v] });
  };
  const moveSkill = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= skills.length) return;
    const next = [...skills];
    [next[i], next[j]] = [next[j], next[i]];
    updateProfile({ skills: next });
  };

  return (
    <AppShell
      title="내 프로필"
      description="추천 정확도를 높이려면 관심 분야와 CV를 최신 상태로 유지하세요."
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <section className="rounded-2xl border border-border bg-white p-6">
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-center gap-4">
                <div className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-[color:var(--point)] to-[color:var(--deep)] text-lg font-semibold text-white">
                  {profile.name.slice(0, 1)}
                </div>
                <div className="min-w-0">
                  <div className="text-lg font-semibold text-[color:var(--navy)]">
                    {profile.name}
                  </div>
                  <div className="text-sm text-muted-foreground">{profile.affiliation}</div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <Badge
                      variant="outline"
                      className="rounded-full border-border bg-[color:var(--surface)] font-normal text-foreground/80"
                    >
                      {profile.status}
                    </Badge>
                    <Badge className="rounded-full border-[color:var(--point)]/30 bg-[color:var(--point)]/10 font-normal text-[color:var(--deep)] hover:bg-[color:var(--point)]/10">
                      {profile.program} 희망
                    </Badge>
                  </div>
                </div>
              </div>
              <Button
                onClick={() => setEditOpen(true)}
                variant="outline"
                className="shrink-0 gap-1.5 rounded-full"
              >
                <Pencil className="h-3.5 w-3.5" /> 프로필 수정
              </Button>
            </div>
            <div className="mt-4 flex items-start gap-2 rounded-xl border border-[color:var(--point)]/25 bg-[color:var(--point)]/5 px-3 py-2 text-xs text-[color:var(--deep)]">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <p>
                입력하신 정보는 연구실 추천 정확도 향상과 컨택 이메일 초안 작성에만 사용되며,
                교수님께 자동으로 전송되지 않습니다.
              </p>
            </div>
          </section>

          <section className="rounded-2xl border border-border bg-white p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[color:var(--navy)]">관심 연구 분야</h2>
              <span className="text-xs text-muted-foreground">{interests.length}개</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {interests.length === 0 && (
                <p className="text-xs text-muted-foreground">아직 등록된 관심 분야가 없어요.</p>
              )}
              {interests.map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 rounded-full border border-[color:var(--point)]/30 bg-[color:var(--point)]/10 px-3 py-1 text-sm text-[color:var(--deep)]"
                >
                  {t}
                  <button
                    onClick={() => removeInterest(t)}
                    aria-label={`${t} 제거`}
                    className="hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <InlineAdder
              placeholder="관심 분야 추가 (예: Diffusion Model)"
              suggestions={INTEREST_SUGGESTIONS.filter((s) => !interests.includes(s))}
              onAdd={addInterest}
            />
          </section>

          <section className="rounded-2xl border border-border bg-white p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[color:var(--navy)]">보유 기술</h2>
              <span className="text-xs text-muted-foreground">
                우선순위 순으로 정렬 · {skills.length}개
              </span>
            </div>
            <ul className="mt-3 space-y-1.5">
              {skills.length === 0 && (
                <li className="text-xs text-muted-foreground">기술을 추가해보세요.</li>
              )}
              {skills.map((s, i) => (
                <li
                  key={s}
                  className="flex items-center gap-2 rounded-lg border border-border bg-[color:var(--surface)]/60 px-3 py-2"
                >
                  <GripVertical className="h-4 w-4 text-muted-foreground" />
                  <span className="w-5 text-xs tabular-nums text-muted-foreground">{i + 1}</span>
                  <span className="flex-1 text-sm text-foreground/85">{s}</span>
                  <button
                    onClick={() => moveSkill(i, -1)}
                    disabled={i === 0}
                    aria-label="위로"
                    className="rounded p-1 text-muted-foreground hover:bg-white hover:text-[color:var(--navy)] disabled:opacity-30"
                  >
                    <ArrowUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => moveSkill(i, 1)}
                    disabled={i === skills.length - 1}
                    aria-label="아래로"
                    className="rounded p-1 text-muted-foreground hover:bg-white hover:text-[color:var(--navy)] disabled:opacity-30"
                  >
                    <ArrowDown className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => removeSkill(s)}
                    aria-label={`${s} 제거`}
                    className="rounded p-1 text-muted-foreground hover:bg-white hover:text-destructive"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
            <InlineAdder
              placeholder="기술 추가 (예: PyTorch)"
              suggestions={SKILL_SUGGESTIONS.filter((s) => !skills.includes(s))}
              onAdd={addSkill}
            />
          </section>

          <section className="rounded-2xl border border-border bg-white p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-[color:var(--navy)]">
                  CV 분석 결과 요약
                </h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  최근 업로드한 CV에서 추출된 정보
                </p>
              </div>
              {cv && (
                <span className="rounded-full border border-[color:var(--point)]/30 bg-[color:var(--point)]/10 px-2.5 py-1 text-[11px] text-[color:var(--deep)]">
                  완성도 {cv.completeness}%
                </span>
              )}
            </div>
            {cv ? (
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <SummaryBlock label="연구 관심사" items={cv.keywords} />
                <SummaryBlock label="기술 스택" items={cv.skills} />
                <SummaryBlock label="연구 방법론" items={cv.methodologies} />
                <SummaryBlock label="프로젝트" items={cv.projects} muted />
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-dashed border-border p-6 text-center">
                <div className="mx-auto grid h-10 w-10 place-items-center rounded-full bg-[color:var(--surface)] text-[color:var(--deep)]">
                  <Sparkles className="h-5 w-5" />
                </div>
                <p className="mt-3 text-sm text-foreground/80">아직 분석된 CV가 없어요.</p>
                <Button
                  asChild
                  size="sm"
                  className="mt-3 rounded-full bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
                >
                  <a href="/recommendations">CV 업로드하기</a>
                </Button>
              </div>
            )}
          </section>
        </div>

        <aside className="space-y-4">
          <section className="rounded-2xl border border-border bg-white p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-[color:var(--navy)]">프로필 완성도</h3>
              <span className="text-sm font-semibold text-[color:var(--deep)]">{completion}%</span>
            </div>
            <Progress value={completion} className="mt-3 h-1.5" />
            <ul className="mt-4 space-y-2 text-sm">
              {checklist.map((c) => (
                <li key={c.label} className="flex items-center gap-2">
                  <span
                    className={cn(
                      "grid h-5 w-5 place-items-center rounded-full border text-[10px]",
                      c.done
                        ? "border-[color:var(--point)] bg-[color:var(--point)] text-white"
                        : "border-border text-muted-foreground",
                    )}
                  >
                    {c.done ? <Check className="h-3 w-3" /> : <Circle className="h-2 w-2" />}
                  </span>
                  <span className={cn(c.done ? "text-foreground/80" : "text-muted-foreground")}>
                    {c.label}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-2xl border border-[color:var(--point)]/30 bg-[color:var(--point)]/5 p-5">
            <div className="text-[11px] font-medium uppercase tracking-widest text-[color:var(--deep)]">
              추천 정확도 팁
            </div>
            <p className="mt-1 text-sm text-foreground/85">
              관심 키워드는 논문에서 실제로 사용되는 표현으로 적을수록 매칭이 정확해져요.
            </p>
          </section>
        </aside>
      </div>

      <ProfileEditDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        initial={profile}
        onSave={(next) => {
          updateProfile(next);
          setEditOpen(false);
          toast.success("프로필을 업데이트했어요", {
            description: "변경 사항이 추천과 이메일 초안에 반영됩니다.",
          });
        }}
      />
    </AppShell>
  );
}

function InlineAdder({
  placeholder,
  suggestions,
  onAdd,
}: {
  placeholder: string;
  suggestions: string[];
  onAdd: (v: string) => void;
}) {
  const [v, setV] = useState("");
  return (
    <div className="mt-4 space-y-2">
      <div className="flex items-center gap-2 rounded-xl bg-[color:var(--surface)] p-3">
        <input
          value={v}
          onChange={(e) => setV(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              onAdd(v);
              setV("");
            }
          }}
          placeholder={placeholder}
          className="min-w-0 flex-1 border-0 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
        <Button
          size="sm"
          onClick={() => {
            onAdd(v);
            setV("");
          }}
          className="gap-1 rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)]"
        >
          <Plus className="h-3.5 w-3.5" /> 추가
        </Button>
      </div>
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {suggestions.slice(0, 8).map((s) => (
            <button
              key={s}
              onClick={() => onAdd(s)}
              className="rounded-full border border-dashed border-border px-2.5 py-0.5 text-xs text-muted-foreground transition-colors hover:border-[color:var(--point)]/40 hover:bg-[color:var(--point)]/5 hover:text-[color:var(--deep)]"
            >
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ProfileEditDialog({
  open,
  onOpenChange,
  initial,
  onSave,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initial: UserProfile;
  onSave: (next: Partial<UserProfile>) => void;
}) {
  const [name, setName] = useState(initial.name);
  const [affiliation, setAffiliation] = useState(initial.affiliation);
  const [status, setStatus] = useState(initial.status);
  const [program, setProgram] = useState(initial.program);
  const [interests, setInterests] = useState<string[]>(initial.interests);

  const toggleInterest = (t: string) =>
    setInterests((s) => (s.includes(t) ? s.filter((x) => x !== t) : [...s, t]));

  const canSave = name.trim() && affiliation.trim() && status && program;

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (o) {
          setName(initial.name);
          setAffiliation(initial.affiliation);
          setStatus(initial.status);
          setProgram(initial.program);
          setInterests(initial.interests);
        }
        onOpenChange(o);
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>프로필 수정</DialogTitle>
          <DialogDescription>
            정확할수록 연구실 매칭과 이메일 초안의 개인화 품질이 향상됩니다.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="pf-name" className="text-xs text-muted-foreground">
              이름
            </Label>
            <Input
              id="pf-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={40}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="pf-aff" className="text-xs text-muted-foreground">
              현재 소속 · 전공
            </Label>
            <Textarea
              id="pf-aff"
              value={affiliation}
              onChange={(e) => setAffiliation(e.target.value)}
              placeholder="예: 포항공대 컴퓨터공학과 학부"
              maxLength={120}
              className="min-h-[64px] resize-none"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label className="text-xs text-muted-foreground">현재 상태</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger className="h-10 rounded-lg text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label className="text-xs text-muted-foreground">희망 과정</Label>
              <Select value={program} onValueChange={setProgram}>
                <SelectTrigger className="h-10 rounded-lg text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROGRAM_OPTIONS.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-2">
            <Label className="text-xs text-muted-foreground">
              관심 연구 분야 <span className="ml-1 text-[10px]">({interests.length}개 선택)</span>
            </Label>
            <div className="flex flex-wrap gap-1.5 rounded-xl border border-border bg-[color:var(--surface)]/60 p-3">
              {INTEREST_SUGGESTIONS.map((t) => {
                const on = interests.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleInterest(t)}
                    className={cn(
                      "rounded-full border px-2.5 py-1 text-xs transition-colors",
                      on
                        ? "border-[color:var(--point)] bg-[color:var(--point)]/15 text-[color:var(--deep)]"
                        : "border-border bg-white text-muted-foreground hover:text-[color:var(--navy)]",
                    )}
                  >
                    {on && <Check className="mr-1 inline h-3 w-3" />}
                    {t}
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] text-muted-foreground">
              세부 관심 분야는 저장 후 프로필 화면에서 자유롭게 추가·삭제할 수 있어요.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-lg">
            취소
          </Button>
          <Button
            disabled={!canSave}
            onClick={() =>
              onSave({
                name: name.trim(),
                affiliation: affiliation.trim(),
                status,
                program,
                interests,
              })
            }
            className="rounded-lg bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
          >
            변경사항 저장
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function SummaryBlock({
  label,
  items,
  muted,
}: {
  label: string;
  items: string[];
  muted?: boolean;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-muted-foreground">{label}</div>
      {muted ? (
        <ul className="mt-2 space-y-1.5 text-sm">
          {items.map((p) => (
            <li key={p} className="flex items-start gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--point)]" />
              <span className="text-foreground/85">{p}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {items.map((k) => (
            <span
              key={k}
              className="rounded-full border border-border bg-[color:var(--surface)] px-2.5 py-1 text-xs text-foreground/80"
            >
              {k}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
