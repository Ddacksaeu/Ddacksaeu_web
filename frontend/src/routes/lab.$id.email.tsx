import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import {
  ChevronRight,
  Copy,
  Save,
  Send,
  Sparkles,
  Bold,
  Underline,
  List,
  Link2,
  Undo2,
  Redo2,
  Paperclip,
  Check,
  X,
  Plus,
  Loader2,
  Info,
  ShieldCheck,
  Wand2,
  Eye,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { LABS, type Lab, type UserProfile } from "@/lib/mock-data";
import { useAppState } from "@/lib/app-state";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/lab/$id/email")({
  loader: ({ params }) => {
    const lab = LABS.find((l) => l.id === params.id);
    if (!lab) throw notFound();
    return { lab } satisfies { lab: Lab };
  },
  component: EmailComposer,
  head: ({ loaderData }) => ({
    meta: [
      {
        title: loaderData ? `${loaderData.lab.name} 컨택 이메일 · 딱새우` : "컨택 이메일 · 딱새우",
      },
      {
        name: "description",
        content: "CV와 연구실 정보를 바탕으로 컨택 메일 초안을 작성하고 검토합니다.",
      },
    ],
  }),
});

type Tone = "polite" | "concise" | "passionate";
type Length = "short" | "normal" | "detailed";
type Purpose = "apply" | "intern" | "meeting";
type Lang = "ko" | "en";

const TONE_LABEL: Record<Tone, string> = {
  polite: "정중함",
  concise: "간결함",
  passionate: "열정적",
};
const LEN_LABEL: Record<Length, string> = { short: "짧게", normal: "보통", detailed: "자세히" };
const PURPOSE_LABEL: Record<Purpose, string> = {
  apply: "대학원 지원 문의",
  intern: "인턴 문의",
  meeting: "면담 요청",
};

function makeDraft(
  lab: Lab,
  profile: UserProfile,
  opts: { tone: Tone; length: Length; purpose: Purpose; lang: Lang },
) {
  const topic = lab.recentTopics[0];
  const topic2 = lab.recentTopics[1] ?? lab.recentTopics[0];
  const project = profile.projects[0];
  const purposeLine =
    opts.purpose === "apply"
      ? "2026학년도 대학원 과정 지원을 준비하며"
      : opts.purpose === "intern"
        ? "학부 연구 인턴 기회를 알아보던 중"
        : "짧게라도 연구 관련 면담을 요청드리고자";
  const closing =
    opts.tone === "passionate"
      ? "교수님 연구실에서 배우고 기여할 수 있기를 진심으로 희망합니다."
      : opts.tone === "concise"
        ? "짧게라도 답변 주시면 감사하겠습니다."
        : "바쁘신 와중에 메일 읽어주셔서 감사드리며, 답장 주시면 큰 도움이 되겠습니다.";
  const extra =
    opts.length === "detailed"
      ? `\n\n특히 최근 발표하신 "${lab.papers[0]?.title ?? topic}" 연구를 흥미롭게 읽었고, ${topic2}에 대한 방법론적 접근이 제 관심 방향과 잘 맞는다고 느꼈습니다. 관련하여 진행한 ${profile.projects[1] ?? project} 경험도 도움이 될 수 있을 것 같습니다.`
      : opts.length === "short"
        ? ""
        : `\n\n특히 ${topic2} 방향에 관심이 있으며, 관련하여 사전에 논문을 읽고 준비하고 있습니다.`;

  const skillsLine = profile.skills.slice(0, 2).join(", ") || "관련 기술";
  const interestsLine = profile.interests[0] ?? lab.field;
  return `${lab.professor}님께,

안녕하십니까. 저는 ${profile.interests.slice(0, 2).join(" · ") || lab.field}에 관심을 가지고 있는 ${profile.affiliation}의 ${profile.status} ${profile.name}입니다. ${purposeLine} ${lab.name}의 연구를 접하고 메일 드립니다.

저는 그동안 ${skillsLine}을(를) 활용해 연구·프로젝트를 수행해왔고, 최근에는 "${project}"를 진행하며 ${interestsLine} 관련 실험을 이어갔습니다. 이 과정에서 표현 학습과 방법론의 중요성을 체감하게 되었습니다.

${lab.name}에서 진행 중인 ${topic} 연구가 제가 관심 있는 방향과 밀접하게 맞닿아 있다고 생각합니다.${extra}

또한 ${profile.program} 진학을 준비하고 있어, 가능하시다면 짧게라도 면담 기회를 주실 수 있을지 여쭙고자 합니다. 요청하시는 자료(CV, 성적표, 포트폴리오 등)는 언제든 회신드릴 수 있도록 준비되어 있습니다.

${closing}

감사합니다.
${profile.name} 드림
연락처: 010-1234-5678`;
}

// Mock spellcheck corrections applied to the initial draft.
function makeCorrections(_body: string) {
  return [
    {
      id: "c1",
      original: "안녕하십니까.",
      suggestion: "안녕하세요.",
      reason: "격식은 유지하되 더 자연스러운 인사말입니다.",
    },
    {
      id: "c2",
      original: "여쭙고자 합니다.",
      suggestion: "여쭙고 싶습니다.",
      reason: "'-고자 합니다'는 다소 딱딱하게 느껴질 수 있어요.",
    },
    {
      id: "c3",
      original: "밀접하게 맞닿아",
      suggestion: "긴밀하게 연결되어",
      reason: "표현이 조금 더 학술적이고 명확해집니다.",
    },
  ];
}

function EmailComposer() {
  const { lab } = Route.useLoaderData() as { lab: Lab };
  const navigate = useNavigate();
  const { profile } = useAppState();

  const [lang, setLang] = useState<Lang>("ko");
  const [tone, setTone] = useState<Tone>("polite");
  const [length, setLength] = useState<Length>("normal");
  const [purpose, setPurpose] = useState<Purpose>("apply");

  const [subject, setSubject] = useState(
    `[대학원 지원 문의] ${profile.name} — ${lab.name} 컨택드립니다`,
  );
  const initial = useMemo(() => makeDraft(lab, profile, { tone, length, purpose, lang }), []); // eslint-disable-line react-hooks/exhaustive-deps
  const [body, setBody] = useState(initial);
  const historyRef = useRef<{ stack: string[]; index: number }>({ stack: [initial], index: 0 });
  const [lastEdited, setLastEdited] = useState<Date>(new Date());
  const [regenLoading, setRegenLoading] = useState(false);

  // Attachments
  const [attachments, setAttachments] = useState([
    { id: "cv", name: `${profile.name}_CV.pdf`, checked: true, size: "312 KB" },
  ]);

  // Checklist
  const [checks, setChecks] = useState({
    name: false,
    facts: false,
    files: false,
    schedule: false,
    tone: false,
  });

  // AI helper state
  const [helperTab, setHelperTab] = useState<"context" | "settings" | "attach" | "ai">("context");
  const [aiTool, setAiTool] = useState<
    "spell" | "polish" | "duplicate" | "style" | "shorten" | "translate"
  >("spell");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiRan, setAiRan] = useState(false);
  const [corrections, setCorrections] = useState<ReturnType<typeof makeCorrections>>([]);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [polishResult, setPolishResult] = useState<null | { before: string; after: string }>(null);

  // Export dialog
  const [exportOpen, setExportOpen] = useState(false);
  // Diff preview dialog
  const [diffOpen, setDiffOpen] = useState<null | { before: string; after: string; label: string }>(
    null,
  );

  const pushHistory = (next: string) => {
    const h = historyRef.current;
    const cut = h.stack.slice(0, h.index + 1);
    cut.push(next);
    historyRef.current = { stack: cut, index: cut.length - 1 };
  };
  const updateBody = (next: string) => {
    pushHistory(next);
    setBody(next);
    setLastEdited(new Date());
  };
  const undo = () => {
    const h = historyRef.current;
    if (h.index <= 0) return;
    h.index -= 1;
    setBody(h.stack[h.index]);
  };
  const redo = () => {
    const h = historyRef.current;
    if (h.index >= h.stack.length - 1) return;
    h.index += 1;
    setBody(h.stack[h.index]);
  };

  const charCount = body.length;
  const readMin = Math.max(1, Math.round(body.length / 500));

  const doneChecks = Object.values(checks).filter(Boolean).length;
  const totalChecks = Object.keys(checks).length;
  const canExport = doneChecks === totalChecks;

  const regenerate = () => {
    setRegenLoading(true);
    setTimeout(() => {
      const next = makeDraft(lab, profile, { tone, length, purpose, lang });
      updateBody(next);
      setRegenLoading(false);
      setCorrections([]);
      setAiRan(false);
      toast.success("초안을 다시 생성했어요");
    }, 900);
  };

  const runAi = () => {
    setAiLoading(true);
    setPolishResult(null);
    setTimeout(() => {
      if (aiTool === "spell") {
        setCorrections(makeCorrections(body).filter((c) => body.includes(c.original)));
        setDismissed([]);
      } else if (aiTool === "polish") {
        const before = body.split("\n\n")[2] ?? body.slice(0, 120);
        const after = before
          .replace("생각합니다", "생각합니다")
          .replace("있다고", "잘 맞닿아 있다고");
        setPolishResult({ before, after });
      }
      setAiLoading(false);
      setAiRan(true);
    }, 900);
  };

  const applyCorrection = (id: string) => {
    const c = corrections.find((x) => x.id === id);
    if (!c || !body.includes(c.original)) return;
    const next = body.replace(c.original, c.suggestion);
    updateBody(next);
    setCorrections((s) => s.filter((x) => x.id !== id));
    toast.success("수정을 적용했어요");
  };
  const dismissCorrection = (id: string) => {
    setDismissed((s) => [...s, id]);
    setCorrections((s) => s.filter((x) => x.id !== id));
  };
  const applyAll = () => {
    let next = body;
    corrections.forEach((c) => {
      if (next.includes(c.original)) next = next.replace(c.original, c.suggestion);
    });
    if (next !== body) {
      updateBody(next);
      toast.success(`${corrections.length}건의 수정을 모두 적용했어요`);
    }
    setCorrections([]);
  };
  const openDiff = () => {
    if (corrections.length === 0) return;
    let after = body;
    corrections.forEach((c) => {
      if (after.includes(c.original)) after = after.replace(c.original, c.suggestion);
    });
    setDiffOpen({ before: body, after, label: "맞춤법 · 표현 수정" });
  };

  // Toolbar helpers: wrap selection in textarea
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wrapSelection = (l: string, r = l) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const s = ta.selectionStart;
    const e = ta.selectionEnd;
    const sel = body.slice(s, e) || "텍스트";
    const next = body.slice(0, s) + l + sel + r + body.slice(e);
    updateBody(next);
    requestAnimationFrame(() => {
      ta.focus();
      ta.selectionStart = s + l.length;
      ta.selectionEnd = s + l.length + sel.length;
    });
  };

  // Personalization highlight preview — highlight lab/professor/topic/project mentions.
  const highlightTerms = [
    lab.name,
    lab.professor,
    profile.name,
    ...lab.recentTopics,
    ...profile.projects,
    ...profile.interests,
    ...profile.skills,
  ].filter(Boolean);

  const personalizedPreview = useMemo(() => {
    const escaped = highlightTerms
      .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .filter(Boolean)
      .sort((a, b) => b.length - a.length);
    if (escaped.length === 0) return [{ text: body, hit: false }];
    const re = new RegExp(`(${escaped.join("|")})`, "g");
    const parts = body.split(re);
    return parts.map((p, i) => ({ text: p, hit: i % 2 === 1 }));
  }, [body, highlightTerms]);

  const openAssistant = (tab: "settings" | "ai", tool?: "spell" | "style") => {
    setHelperTab(tab);
    if (tool) {
      setAiTool(tool);
      setAiRan(false);
    }
    window.setTimeout(() => {
      document.getElementById("email-ai-tools")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 0);
  };

  return (
    <TooltipProvider delayDuration={200}>
      <AppShell
        title="컨택 이메일 작성"
        description={`${lab.name} · ${lab.professor}`}
        actions={
          <span className="hidden items-center gap-2 text-xs text-muted-foreground lg:flex">
            <span className="grid h-5 w-5 place-items-center rounded-full bg-[color:var(--success)]/15 text-[color:var(--success)]">
              <Check className="h-3 w-3" />
            </span>
            자동 저장됨 · 방금 전
          </span>
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
          <Link to="/lab/$id" params={{ id: lab.id }} className="hover:text-[color:var(--deep)]">
            {lab.name}
          </Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-[color:var(--navy)]">컨택 이메일 작성</span>
        </nav>

        {/* Send-safety notice — always visible at top */}
        <section className="rounded-2xl border-2 border-[color:var(--warning)]/50 bg-[color:var(--warning)]/10 p-4">
          <div className="flex items-start gap-3">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[color:var(--warning)]/25 text-[color:oklch(0.42_0.09_75)]">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[color:oklch(0.36_0.09_75)]">
                딱새우는 초안 작성만 도와드리며, 교수님께 이메일을 직접 발송하지 않습니다.
              </p>
              <p className="mt-1 text-xs leading-relaxed text-[color:oklch(0.42_0.09_75)]">
                최종 검토와 발송은 반드시 본인이 사용하는 메일 앱(예: Gmail, Outlook)에서 직접
                진행해주세요. 교수님 성함·소속·논문 인용 등 사실관계는 발송 전에 스스로 한 번 더
                확인해야 합니다.
              </p>
            </div>
          </div>
        </section>

        {/* Intro */}
        <section className="mt-4 rounded-2xl border border-border bg-white p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-[color:var(--navy)]">
                교수님께 보낼 컨택 이메일을 준비해보세요
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                내 프로필과 연구실 정보를 바탕으로 초안을 만들고, 직접 검토한 뒤 내가 사용하는 메일
                앱으로 옮겨 발송하세요.
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-[color:var(--surface)] px-2.5 py-1 text-[11px] text-muted-foreground">
              <Info className="h-3 w-3" /> 초안 작성 및 검토 전용 도구
            </span>
          </div>
        </section>

        {/* AI feature shortcuts — UI-first, ready for a real model later */}
        <section className="mt-4 grid gap-3 md:grid-cols-3" aria-label="AI 이메일 도구">
          <button
            type="button"
            onClick={() => openAssistant("settings")}
            className="rounded-2xl border border-border bg-white p-4 text-left transition hover:border-[color:var(--point)]/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--point)]"
          >
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-[color:var(--point)]/10 text-[color:var(--deep)]">
              <Sparkles className="h-4 w-4" />
            </span>
            <strong className="mt-3 block text-sm text-[color:var(--navy)]">
              AI로 이메일 초안 작성
            </strong>
            <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
              내 CV와 연구실 정보를 조합해 목적·문체별 초안을 준비합니다.
            </span>
            <span className="mt-3 inline-flex text-xs font-medium text-[color:var(--deep)]">
              설정 열기 →
            </span>
          </button>
          <button
            type="button"
            onClick={() => openAssistant("ai", "spell")}
            className="rounded-2xl border border-border bg-white p-4 text-left transition hover:border-[color:var(--point)]/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--point)]"
          >
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-[color:var(--point)]/10 text-[color:var(--deep)]">
              <Check className="h-4 w-4" />
            </span>
            <strong className="mt-3 block text-sm text-[color:var(--navy)]">
              맞춤법과 표현 검사
            </strong>
            <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
              오탈자와 어색한 표현을 찾아 수정안을 나란히 보여줍니다.
            </span>
            <span className="mt-3 inline-flex text-xs font-medium text-[color:var(--deep)]">
              검사 도구 열기 →
            </span>
          </button>
          <button
            type="button"
            onClick={() => openAssistant("ai", "style")}
            className="rounded-2xl border border-border bg-white p-4 text-left transition hover:border-[color:var(--point)]/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--point)]"
          >
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-[color:var(--point)]/10 text-[color:var(--deep)]">
              <ShieldCheck className="h-4 w-4" />
            </span>
            <strong className="mt-3 block text-sm text-[color:var(--navy)]">AI로 메일 점검</strong>
            <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
              정중함·명확성·구체성과 과장 표현 여부를 발송 전에 확인합니다.
            </span>
            <span className="mt-3 inline-flex text-xs font-medium text-[color:var(--deep)]">
              점검 도구 열기 →
            </span>
          </button>
        </section>

        {/* Main */}
        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          {/* Editor column */}
          <div className="min-w-0 space-y-5">
            <section className="rounded-2xl border border-border bg-white">
              {/* Header meta */}
              <div className="space-y-3 border-b border-border p-5">
                <div className="grid gap-2">
                  <Label htmlFor="to" className="text-xs text-muted-foreground">
                    받는 사람
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="to"
                      readOnly
                      value={`${lab.professor} <${lab.email}>`}
                      className="h-10 flex-1 rounded-lg bg-[color:var(--surface)] font-mono text-sm"
                    />
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-10 w-10 shrink-0 rounded-lg"
                          onClick={() => {
                            navigator.clipboard?.writeText(lab.email);
                            toast.success("이메일 주소를 복사했어요");
                          }}
                          aria-label="이메일 주소 복사"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>이메일 주소 복사</TooltipContent>
                    </Tooltip>
                  </div>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="subject" className="text-xs text-muted-foreground">
                    제목
                  </Label>
                  <Input
                    id="subject"
                    value={subject}
                    onChange={(e) => {
                      setSubject(e.target.value);
                      setLastEdited(new Date());
                    }}
                    className="h-10 rounded-lg text-sm"
                  />
                </div>
              </div>

              {/* Toolbar */}
              <div className="flex flex-wrap items-center gap-1 border-b border-border px-3 py-2">
                <ToolBtn label="실행 취소" onClick={undo} disabled={historyRef.current.index <= 0}>
                  <Undo2 className="h-4 w-4" />
                </ToolBtn>
                <ToolBtn
                  label="다시 실행"
                  onClick={redo}
                  disabled={historyRef.current.index >= historyRef.current.stack.length - 1}
                >
                  <Redo2 className="h-4 w-4" />
                </ToolBtn>
                <span className="mx-1 h-4 w-px bg-border" />
                <ToolBtn label="굵게" onClick={() => wrapSelection("**")}>
                  <Bold className="h-4 w-4" />
                </ToolBtn>
                <ToolBtn label="밑줄" onClick={() => wrapSelection("__")}>
                  <Underline className="h-4 w-4" />
                </ToolBtn>
                <ToolBtn label="글머리 기호" onClick={() => wrapSelection("\n- ", "")}>
                  <List className="h-4 w-4" />
                </ToolBtn>
                <ToolBtn label="링크" onClick={() => wrapSelection("[", "](https://)")}>
                  <Link2 className="h-4 w-4" />
                </ToolBtn>
                <div className="ml-auto flex items-center gap-1 text-[11px] text-muted-foreground">
                  <span className="hidden sm:inline">본문 편집</span>
                </div>
              </div>

              {/* Personalized preview */}
              <details className="border-b border-border" open>
                <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-5 py-2.5 text-xs text-muted-foreground hover:bg-[color:var(--surface)]">
                  <span className="flex items-center gap-1.5">
                    <Eye className="h-3.5 w-3.5" /> 개인화 미리보기 · 삽입된 정보를 하이라이트로
                    확인
                  </span>
                  <span className="text-[11px]">펼치기/접기</span>
                </summary>
                <div className="max-h-40 overflow-y-auto whitespace-pre-wrap px-5 pb-4 text-[13px] leading-relaxed text-foreground/85">
                  {personalizedPreview.map((p, i) =>
                    p.hit ? (
                      <mark
                        key={i}
                        className="rounded-sm bg-[color:var(--point)]/15 px-0.5 text-[color:var(--deep)]"
                      >
                        {p.text}
                      </mark>
                    ) : (
                      <span key={i}>{p.text}</span>
                    ),
                  )}
                </div>
              </details>

              {/* Body */}
              <div className="p-5">
                <Label htmlFor="body" className="sr-only">
                  본문
                </Label>
                <Textarea
                  id="body"
                  ref={textareaRef}
                  value={body}
                  onChange={(e) => updateBody(e.target.value)}
                  className="min-h-[420px] resize-y rounded-lg font-sans text-sm leading-relaxed"
                  aria-label="이메일 본문"
                />
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-[11px] text-muted-foreground">
                  <div className="flex flex-wrap items-center gap-3 tabular-nums">
                    <span>{charCount.toLocaleString()}자</span>
                    <span className="text-border">·</span>
                    <span>예상 읽기 {readMin}분</span>
                    <span className="text-border">·</span>
                    <span>
                      마지막 수정{" "}
                      {lastEdited.toLocaleTimeString("ko-KR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap items-center justify-end gap-2 border-t border-border p-4">
                <Button
                  variant="ghost"
                  className="gap-2 rounded-lg text-muted-foreground hover:text-[color:var(--navy)]"
                  onClick={() => toast.success("초안을 저장했어요")}
                >
                  <Save className="h-4 w-4" /> 초안 저장
                </Button>
                <Button
                  variant="outline"
                  className="gap-2 rounded-lg"
                  onClick={() => {
                    navigator.clipboard?.writeText(`${subject}\n\n${body}`);
                    toast.success("클립보드에 복사했어요");
                  }}
                >
                  <Copy className="h-4 w-4" /> 클립보드에 복사
                </Button>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span tabIndex={0}>
                      <Button
                        className={cn(
                          "gap-2 rounded-lg bg-[color:var(--point)] text-white hover:bg-[color:var(--deep)]",
                          !canExport && "cursor-not-allowed opacity-60",
                        )}
                        disabled={!canExport}
                        onClick={() => setExportOpen(true)}
                      >
                        <Send className="h-4 w-4" /> 이메일로 내보내기
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!canExport && (
                    <TooltipContent side="top">
                      아래 검토 체크리스트를 모두 확인해야 내보낼 수 있어요 ({doneChecks}/
                      {totalChecks})
                    </TooltipContent>
                  )}
                </Tooltip>
              </div>
            </section>

            {/* Review checklist */}
            <section className="rounded-2xl border border-border bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[color:var(--navy)]">
                    발송 전 검토 체크리스트
                  </h3>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    실제 발송 전에 아래 항목을 한 번 더 확인해주세요.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-32">
                    <Progress value={(doneChecks / totalChecks) * 100} className="h-1.5" />
                  </div>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {doneChecks}/{totalChecks}
                  </span>
                  {canExport && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-[color:var(--success)]/30 bg-[color:var(--success)]/10 px-2 py-0.5 text-[11px] font-medium text-[color:var(--success)]">
                      <Check className="h-3 w-3" /> 검토 완료
                    </span>
                  )}
                </div>
              </div>
              <ul className="mt-4 space-y-2">
                {(
                  [
                    ["name", "교수님 성함과 연구실명이 정확한지 확인했어요"],
                    ["facts", "언급한 논문·연구 주제의 사실관계를 확인했어요"],
                    ["files", "CV와 포트폴리오 첨부 준비를 확인했어요"],
                    ["schedule", "면담 요청 일정과 연락처를 확인했어요"],
                    ["tone", "개인정보 노출·과장 표현이 없는지 검토했어요"],
                  ] as const
                ).map(([key, label]) => (
                  <li
                    key={key}
                    className="flex items-start gap-3 rounded-lg border border-border bg-[color:var(--surface)]/60 px-3 py-2.5"
                  >
                    <Checkbox
                      id={`chk-${key}`}
                      checked={checks[key]}
                      onCheckedChange={(v) => setChecks((s) => ({ ...s, [key]: v === true }))}
                      className="mt-0.5"
                    />
                    <Label
                      htmlFor={`chk-${key}`}
                      className="cursor-pointer text-sm leading-relaxed text-foreground/85"
                    >
                      {label}
                    </Label>
                  </li>
                ))}
              </ul>
            </section>
          </div>

          {/* Right assistant panel */}
          <aside id="email-ai-tools" className="min-w-0 scroll-mt-24">
            <div className="sticky top-24 rounded-2xl border border-border bg-white">
              <Tabs value={helperTab} onValueChange={(v) => setHelperTab(v as typeof helperTab)}>
                <TabsList className="grid w-full grid-cols-4 rounded-none rounded-t-2xl border-b border-border bg-[color:var(--surface)] p-1">
                  <TabsTrigger
                    value="context"
                    className="rounded-lg text-xs data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
                  >
                    사용된 정보
                  </TabsTrigger>
                  <TabsTrigger
                    value="settings"
                    className="rounded-lg text-xs data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
                  >
                    메일 설정
                  </TabsTrigger>
                  <TabsTrigger
                    value="attach"
                    className="rounded-lg text-xs data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
                  >
                    첨부
                  </TabsTrigger>
                  <TabsTrigger
                    value="ai"
                    className="rounded-lg text-xs data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
                  >
                    <Wand2 className="mr-1 h-3.5 w-3.5" />
                    도우미
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="context" className="space-y-4 p-4">
                  <PanelSection title="내 CV">
                    <ul className="space-y-1.5 text-sm">
                      {[
                        "관심 분야: 컴퓨터 비전, 멀티모달",
                        "기술 스택: PyTorch, OpenCV",
                        "프로젝트: 의료 영상 분류, 비디오 이해",
                        "학부 연구 인턴 경험",
                      ].map((t) => (
                        <li key={t} className="flex items-start gap-2 text-foreground/85">
                          <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--success)]" />
                          <span>{t}</span>
                        </li>
                      ))}
                    </ul>
                    <Link
                      to="/profile"
                      className="mt-2 inline-flex items-center gap-1 text-xs text-[color:var(--deep)] hover:underline"
                    >
                      정보 수정 <ChevronRight className="h-3 w-3" />
                    </Link>
                  </PanelSection>
                  <PanelSection title="연구실 정보">
                    <ul className="space-y-1.5 text-sm">
                      <li className="flex items-start gap-2 text-foreground/85">
                        <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--success)]" />
                        <span>
                          {lab.professor} · {lab.name}
                        </span>
                      </li>
                      <li className="flex items-start gap-2 text-foreground/85">
                        <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--success)]" />
                        <span>키워드: {lab.keywords.slice(0, 4).join(", ")}</span>
                      </li>
                      <li className="flex items-start gap-2 text-foreground/85">
                        <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--success)]" />
                        <span>최근 주제: {lab.recentTopics[0]}</span>
                      </li>
                    </ul>
                    <Link
                      to="/lab/$id"
                      params={{ id: lab.id }}
                      className="mt-2 inline-flex items-center gap-1 text-xs text-[color:var(--deep)] hover:underline"
                    >
                      연구실 정보 보기 <ChevronRight className="h-3 w-3" />
                    </Link>
                  </PanelSection>
                </TabsContent>

                <TabsContent value="settings" className="space-y-4 p-4">
                  <SettingRow label="언어">
                    <SegSelect
                      value={lang}
                      onChange={(v) => setLang(v as Lang)}
                      options={[
                        { v: "ko", l: "한국어" },
                        { v: "en", l: "영어" },
                      ]}
                    />
                  </SettingRow>
                  <SettingRow label="문체">
                    <SegSelect
                      value={tone}
                      onChange={(v) => setTone(v as Tone)}
                      options={[
                        { v: "polite", l: "정중함" },
                        { v: "concise", l: "간결함" },
                        { v: "passionate", l: "열정적" },
                      ]}
                    />
                  </SettingRow>
                  <SettingRow label="길이">
                    <SegSelect
                      value={length}
                      onChange={(v) => setLength(v as Length)}
                      options={[
                        { v: "short", l: "짧게" },
                        { v: "normal", l: "보통" },
                        { v: "detailed", l: "자세히" },
                      ]}
                    />
                  </SettingRow>
                  <SettingRow label="목적">
                    <Select value={purpose} onValueChange={(v) => setPurpose(v as Purpose)}>
                      <SelectTrigger className="h-9 w-full rounded-lg text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.keys(PURPOSE_LABEL) as Purpose[]).map((k) => (
                          <SelectItem key={k} value={k}>
                            {PURPOSE_LABEL[k]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </SettingRow>
                  <Button
                    className="w-full gap-2 rounded-lg bg-[color:var(--deep)] hover:bg-[color:var(--navy)]"
                    onClick={regenerate}
                    disabled={regenLoading}
                  >
                    {regenLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4" />
                    )}
                    초안 다시 생성
                  </Button>
                  <p className="text-[11px] leading-relaxed text-muted-foreground">
                    설정을 바꾸면 기존 편집 내용이 새 초안으로 덮어써집니다. 실행 취소로 되돌릴 수
                    있어요.
                  </p>
                </TabsContent>

                <TabsContent value="attach" className="space-y-3 p-4">
                  {attachments.map((a) => (
                    <div
                      key={a.id}
                      className="flex items-center gap-3 rounded-lg border border-border bg-[color:var(--surface)]/60 px-3 py-2.5"
                    >
                      <Checkbox
                        checked={a.checked}
                        onCheckedChange={(v) =>
                          setAttachments((s) =>
                            s.map((x) => (x.id === a.id ? { ...x, checked: v === true } : x)),
                          )
                        }
                      />
                      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white text-[color:var(--deep)]">
                        <Paperclip className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium text-[color:var(--navy)]">
                          {a.name}
                        </div>
                        <div className="text-[11px] text-muted-foreground">{a.size}</div>
                      </div>
                      <button
                        onClick={() => setAttachments((s) => s.filter((x) => x.id !== a.id))}
                        aria-label="첨부 제거"
                        className="text-muted-foreground hover:text-[color:var(--navy)]"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => {
                      setAttachments((s) => [
                        ...s,
                        {
                          id: `pf${s.length}`,
                          name: `포트폴리오_${s.length}.pdf`,
                          checked: true,
                          size: "1.2 MB",
                        },
                      ]);
                      toast.success("포트폴리오를 추가했어요");
                    }}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border px-3 py-3 text-sm text-muted-foreground transition-colors hover:border-[color:var(--point)]/40 hover:bg-[color:var(--point)]/5 hover:text-[color:var(--deep)]"
                  >
                    <Plus className="h-4 w-4" /> 포트폴리오 추가
                  </button>
                  <p className="text-[11px] text-muted-foreground">
                    프로토타입에서는 파일 업로드가 로컬 UI에만 반영됩니다.
                  </p>
                </TabsContent>

                <TabsContent value="ai" className="p-4">
                  <div className="mb-3 flex flex-wrap gap-1">
                    {(
                      [
                        ["spell", "맞춤법 검사"],
                        ["polish", "문장 다듬기"],
                        ["duplicate", "중복 표현"],
                        ["style", "문체 점검"],
                        ["shorten", "길이 줄이기"],
                        ["translate", "영문 변환"],
                      ] as const
                    ).map(([k, l]) => (
                      <button
                        key={k}
                        onClick={() => {
                          setAiTool(k);
                          setAiRan(false);
                          setPolishResult(null);
                        }}
                        className={cn(
                          "rounded-full border px-2.5 py-1 text-[11px] transition-colors",
                          aiTool === k
                            ? "border-[color:var(--point)]/40 bg-[color:var(--point)]/10 text-[color:var(--deep)]"
                            : "border-border bg-white text-muted-foreground hover:text-[color:var(--navy)]",
                        )}
                      >
                        {l}
                      </button>
                    ))}
                  </div>
                  <Button
                    className="w-full gap-2 rounded-lg bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
                    onClick={runAi}
                    disabled={aiLoading}
                  >
                    {aiLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Wand2 className="h-4 w-4" />
                    )}
                    실행
                  </Button>

                  {/* Results */}
                  <div className="mt-4 space-y-3">
                    {aiLoading && (
                      <div className="space-y-2">
                        <div className="h-16 animate-pulse rounded-lg bg-[color:var(--surface)]" />
                        <div className="h-16 animate-pulse rounded-lg bg-[color:var(--surface)]" />
                      </div>
                    )}

                    {!aiLoading && aiTool === "spell" && aiRan && corrections.length === 0 && (
                      <EmptyResult
                        label={
                          dismissed.length > 0
                            ? "모든 제안을 처리했어요."
                            : "발견된 문제가 없습니다. 훌륭해요."
                        }
                        onRetry={runAi}
                      />
                    )}

                    {!aiLoading && aiTool === "spell" && corrections.length > 0 && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-muted-foreground">
                            {corrections.length}개의 제안
                          </span>
                          <div className="flex gap-1">
                            <button
                              onClick={openDiff}
                              className="rounded-md px-2 py-1 text-[11px] text-[color:var(--deep)] hover:bg-[color:var(--point)]/10"
                            >
                              변경 미리보기
                            </button>
                            <button
                              onClick={applyAll}
                              className="rounded-md bg-[color:var(--deep)] px-2 py-1 text-[11px] font-medium text-white hover:bg-[color:var(--navy)]"
                            >
                              모두 적용
                            </button>
                          </div>
                        </div>
                        {corrections.map((c) => (
                          <div key={c.id} className="rounded-lg border border-border p-3">
                            <div className="flex items-start gap-2 text-xs">
                              <span className="rounded bg-[color:var(--warning)]/15 px-1.5 py-0.5 text-[color:oklch(0.5_0.11_75)] line-through decoration-[color:var(--warning)]">
                                {c.original}
                              </span>
                              <ChevronRight className="mt-0.5 h-3 w-3 text-muted-foreground" />
                              <span className="rounded bg-[color:var(--success)]/15 px-1.5 py-0.5 font-medium text-[color:var(--success)]">
                                {c.suggestion}
                              </span>
                            </div>
                            <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                              {c.reason}
                            </p>
                            <div className="mt-2 flex justify-end gap-1">
                              <button
                                onClick={() => dismissCorrection(c.id)}
                                className="rounded-md px-2 py-1 text-[11px] text-muted-foreground hover:bg-[color:var(--surface)]"
                              >
                                무시
                              </button>
                              <button
                                onClick={() => applyCorrection(c.id)}
                                className="rounded-md bg-[color:var(--point)] px-2 py-1 text-[11px] font-medium text-white hover:bg-[color:var(--deep)]"
                              >
                                적용
                              </button>
                            </div>
                          </div>
                        ))}
                      </>
                    )}

                    {!aiLoading && aiTool === "polish" && polishResult && (
                      <div className="rounded-lg border border-border p-3">
                        <div className="text-[11px] uppercase tracking-widest text-muted-foreground">
                          원문
                        </div>
                        <p className="mt-1 text-xs text-foreground/80">{polishResult.before}</p>
                        <div className="mt-3 text-[11px] uppercase tracking-widest text-muted-foreground">
                          제안
                        </div>
                        <p className="mt-1 text-xs text-[color:var(--navy)]">
                          {polishResult.after}
                        </p>
                        <div className="mt-3 flex justify-end gap-1">
                          <button
                            onClick={() =>
                              setDiffOpen({
                                before: body,
                                after: body.replace(polishResult.before, polishResult.after),
                                label: "문장 다듬기",
                              })
                            }
                            className="rounded-md px-2 py-1 text-[11px] text-[color:var(--deep)] hover:bg-[color:var(--point)]/10"
                          >
                            변경 미리보기
                          </button>
                          <button
                            onClick={() => {
                              updateBody(body.replace(polishResult.before, polishResult.after));
                              setPolishResult(null);
                              toast.success("다듬은 문장을 적용했어요");
                            }}
                            className="rounded-md bg-[color:var(--point)] px-2 py-1 text-[11px] font-medium text-white hover:bg-[color:var(--deep)]"
                          >
                            적용
                          </button>
                        </div>
                      </div>
                    )}

                    {!aiLoading && aiTool === "duplicate" && aiRan && (
                      <div className="rounded-lg border border-border p-3 text-xs text-foreground/80">
                        <p className="font-medium text-[color:var(--navy)]">중복 표현 2건</p>
                        <ul className="mt-2 space-y-1.5 text-muted-foreground">
                          <li>
                            · "관심" 표현이 3회 이상 반복됩니다. 다른 표현으로 대체를 권장합니다.
                          </li>
                          <li>· "짧게라도"가 두 문장에 등장합니다.</li>
                        </ul>
                      </div>
                    )}

                    {!aiLoading && aiTool === "style" && aiRan && (
                      <div className="space-y-3 rounded-lg border border-border p-3">
                        {[
                          ["정중함", 88],
                          ["명확성", 74],
                          ["구체성", 62],
                        ].map(([l, v]) => (
                          <div key={l as string}>
                            <div className="mb-1 flex items-center justify-between text-xs">
                              <span className="text-foreground/80">{l}</span>
                              <span className="tabular-nums text-muted-foreground">{v}점</span>
                            </div>
                            <Progress value={v as number} className="h-1.5" />
                          </div>
                        ))}
                        <p className="text-[11px] text-muted-foreground">
                          구체성을 높이려면 관심 있는 논문·주제를 한 문단 더 언급해보세요.
                        </p>
                      </div>
                    )}

                    {!aiLoading && aiTool === "shorten" && aiRan && (
                      <button
                        onClick={() => {
                          const short = body
                            .split("\n\n")
                            .filter((_, i) => i < 4)
                            .join("\n\n");
                          setDiffOpen({ before: body, after: short, label: "길이 줄이기" });
                        }}
                        className="w-full rounded-lg border border-border p-3 text-left text-xs hover:bg-[color:var(--surface)]"
                      >
                        <p className="font-medium text-[color:var(--navy)]">
                          약 30% 짧은 초안 준비 완료
                        </p>
                        <p className="mt-1 text-muted-foreground">클릭하여 변경 미리보기 열기</p>
                      </button>
                    )}

                    {!aiLoading && aiTool === "translate" && aiRan && (
                      <button
                        onClick={() => {
                          const en = `Dear Prof. ${lab.professor.replace(" 교수", "")},\n\nI hope this email finds you well. I am ${profile.name}, interested in ${lab.field}. I was drawn to your work on ${lab.recentTopics[0]} and would appreciate the chance to discuss potential graduate study in your lab.\n\nBest regards,\n${profile.name}`;
                          setDiffOpen({ before: body, after: en, label: "영문 변환" });
                        }}
                        className="w-full rounded-lg border border-border p-3 text-left text-xs hover:bg-[color:var(--surface)]"
                      >
                        <p className="font-medium text-[color:var(--navy)]">영문 초안 준비 완료</p>
                        <p className="mt-1 text-muted-foreground">클릭하여 변경 미리보기 열기</p>
                      </button>
                    )}

                    {!aiRan && !aiLoading && (
                      <p className="rounded-lg border border-dashed border-border p-4 text-center text-xs text-muted-foreground">
                        원하는 도구를 선택하고 실행을 눌러주세요.
                      </p>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </aside>
        </div>

        {/* Export confirmation */}
        <Dialog open={exportOpen} onOpenChange={setExportOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>내 메일 앱으로 옮기기</DialogTitle>
              <DialogDescription>
                딱새우는 메일을 대신 보내지 않습니다. 아래 요약을 확인하고, 내가 사용하는 메일
                앱에서 최종 검토 후 직접 발송해주세요.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 rounded-xl border border-border bg-[color:var(--surface)] p-3 text-sm">
              <SummaryRow k="받는 사람" v={`${lab.professor} <${lab.email}>`} />
              <SummaryRow k="제목" v={subject} />
              <SummaryRow
                k="첨부"
                v={
                  attachments
                    .filter((a) => a.checked)
                    .map((a) => a.name)
                    .join(", ") || "첨부 없음"
                }
              />
            </div>
            <div className="flex items-start gap-2 rounded-lg border border-[color:var(--warning)]/40 bg-[color:var(--warning)]/10 px-3 py-2 text-[11px] text-[color:oklch(0.42_0.09_75)]">
              <Info className="mt-0.5 h-3 w-3 shrink-0" />
              <p>
                발송의 최종 책임은 본인에게 있습니다. 첨부 파일과 수신자 주소를 다시 한 번
                확인해주세요.
              </p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setExportOpen(false)} className="rounded-lg">
                취소
              </Button>
              <Button
                className="gap-2 rounded-lg bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
                onClick={() => {
                  setExportOpen(false);
                  toast.success("메일 앱을 여는 것으로 표시했어요", {
                    description: "프로토타입에서는 외부 앱을 실제로 열지 않아요.",
                    action: {
                      label: "캘린더로 이동",
                      onClick: () => navigate({ to: "/calendar" }),
                    },
                  });
                }}
              >
                <Send className="h-4 w-4" /> 메일 앱에서 열기
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Diff preview */}
        <Dialog open={!!diffOpen} onOpenChange={(o) => !o && setDiffOpen(null)}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>{diffOpen?.label} · 변경 미리보기</DialogTitle>
              <DialogDescription>
                변경 전과 변경 후를 비교하고 적용 여부를 결정하세요.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border bg-[color:var(--surface)] p-3">
                <div className="mb-2 text-[11px] uppercase tracking-widest text-muted-foreground">
                  변경 전
                </div>
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-[12px] leading-relaxed text-foreground/85">
                  {diffOpen?.before}
                </pre>
              </div>
              <div className="rounded-lg border border-[color:var(--point)]/30 bg-[color:var(--point)]/5 p-3">
                <div className="mb-2 text-[11px] uppercase tracking-widest text-[color:var(--deep)]">
                  변경 후
                </div>
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-[12px] leading-relaxed text-[color:var(--navy)]">
                  {diffOpen?.after}
                </pre>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDiffOpen(null)} className="rounded-lg">
                취소
              </Button>
              <Button
                className="rounded-lg bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
                onClick={() => {
                  if (diffOpen) {
                    updateBody(diffOpen.after);
                    toast.success("변경 사항을 적용했어요");
                  }
                  setDiffOpen(null);
                }}
              >
                적용
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </AppShell>
    </TooltipProvider>
  );
}

function ToolBtn({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={label}
          onClick={onClick}
          disabled={disabled}
          className={cn(
            "grid h-8 w-8 place-items-center rounded-md text-muted-foreground transition-colors",
            "hover:bg-[color:var(--surface)] hover:text-[color:var(--navy)]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--point)]",
            disabled &&
              "cursor-not-allowed opacity-40 hover:bg-transparent hover:text-muted-foreground",
          )}
        >
          {children}
        </button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

function PanelSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-[color:var(--surface)]/60 p-3">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
        {title}
      </div>
      {children}
    </div>
  );
}

function SettingRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-xs text-muted-foreground">{label}</div>
      {children}
    </div>
  );
}

function SegSelect<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { v: T; l: string }[];
}) {
  return (
    <div className="inline-flex w-full rounded-lg border border-border bg-[color:var(--surface)] p-0.5">
      {options.map((o) => (
        <button
          key={o.v}
          onClick={() => onChange(o.v)}
          className={cn(
            "flex-1 rounded-md px-2 py-1.5 text-xs transition-colors",
            value === o.v
              ? "bg-white text-[color:var(--navy)] shadow-sm"
              : "text-muted-foreground hover:text-[color:var(--navy)]",
          )}
        >
          {o.l}
        </button>
      ))}
    </div>
  );
}

function EmptyResult({ label, onRetry }: { label: string; onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-dashed border-border p-4 text-center">
      <p className="text-xs text-muted-foreground">{label}</p>
      <button
        onClick={onRetry}
        className="mt-2 rounded-md px-2 py-1 text-[11px] text-[color:var(--deep)] hover:bg-[color:var(--point)]/10"
      >
        다시 실행
      </button>
    </div>
  );
}

function SummaryRow({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-16 shrink-0 text-[11px] uppercase tracking-widest text-muted-foreground">
        {k}
      </div>
      <div className="min-w-0 flex-1 break-words text-foreground/85">{v}</div>
    </div>
  );
}
