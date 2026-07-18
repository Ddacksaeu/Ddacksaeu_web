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
import { useRef, useState } from "react";
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
import { apiFetch } from "@/lib/api/client";
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
        title: loaderData
          ? `${loaderData.lab.name} Outreach Email · Ddaksaeu`
          : "Outreach Email · Ddaksaeu",
      },
      {
        name: "description",
        content:
          "Draft and review a personalized outreach email using your CV and lab information.",
      },
    ],
  }),
});

type Tone = "polite" | "concise" | "passionate";
type Length = "short" | "normal" | "detailed";
type Purpose = "apply" | "intern" | "meeting";
type Lang = "ko" | "en";

const TONE_LABEL: Record<Tone, string> = {
  polite: "Polite",
  concise: "Concise",
  passionate: "Enthusiastic",
};
const LEN_LABEL: Record<Length, string> = {
  short: "Short",
  normal: "Standard",
  detailed: "Detailed",
};
const PURPOSE_LABEL: Record<Purpose, string> = {
  apply: "Graduate application inquiry",
  intern: "Research internship inquiry",
  meeting: "Meeting request",
};


const API_LAB_IDS: Record<string, string> = {
  vislab: "fixture-vision-lab",
  nlplab: "fixture-multimodal-lab",
  roblab: "fixture-robotics-lab",
};

type EmailDraftApiResponse = {
  labId: string;
  subject: string;
  body: string;
  personalizationNotes: string[];
  generationMode: "ai" | "demo";
  model: string | null;
};

function makeDraft(
  lab: Lab,
  profile: UserProfile,
  opts: { tone: Tone; length: Length; purpose: Purpose; lang: Lang },
) {
  const topic = lab.recentTopics[0];
  const topic2 = lab.recentTopics[1] ?? lab.recentTopics[0];
  const project = profile.projects[0];

  if (opts.lang === "en") {
    const purpose =
      opts.purpose === "apply"
        ? `I am preparing to apply to the ${profile.program}`
        : opts.purpose === "intern"
          ? "I am exploring undergraduate research internship opportunities"
          : "I am writing to ask whether you might be available for a brief conversation about your research";
    const detail =
      opts.length === "detailed"
        ? `\n\nI also read your recent paper, "${lab.papers[0]?.title ?? topic}." Its approach to ${topic2} stood out to me, and I see a meaningful connection to my experience with ${profile.projects[1] ?? project}.`
        : opts.length === "short"
          ? ""
          : `\n\nI am especially interested in ${topic2} and have been reading related work to better understand the area.`;
    const closing =
      opts.tone === "passionate"
        ? "I would be excited to learn from and contribute to your group."
        : opts.tone === "concise"
          ? "I would appreciate any guidance you may be able to share."
          : "Thank you for your time. I would appreciate the opportunity to hear whether there may be a fit.";
    const skills = profile.skills.slice(0, 2).join(" and ") || "relevant technical methods";

    return `Dear ${lab.professor},

My name is ${profile.name}, and I am ${profile.affiliation}. ${purpose}, and I am reaching out after learning about the work at ${lab.name}.

Through projects using ${skills}, including "${project}," I have developed a strong interest in ${profile.interests[0] ?? lab.field}. Your group's work on ${topic} connects closely with the questions I hope to explore.${detail}

If you are currently considering prospective students or interns, I would be grateful for the chance to briefly discuss your research and potential opportunities. I can provide my CV, transcript, portfolio, or any other materials that would be helpful.

${closing}

Best regards,
${profile.name}`;
  }

  const koreanProfessor = lab.professor.replace(/^Professor\s+/, "");
  const koreanAffiliation =
    profile.affiliation === "an undergraduate in Computer Science at POSTECH"
      ? "포항공대 컴퓨터공학과 학부"
      : profile.affiliation;
  const koreanStatus =
    {
      "Current undergraduate": "학부 재학생",
      "Expected graduate": "졸업 예정자",
      Graduate: "졸업생",
      "Current master's student": "석사과정 재학생",
      "Working professional": "직장인",
    }[profile.status] ?? profile.status;
  const koreanProgram =
    {
      "Master's program": "석사과정",
      "PhD program": "박사과정",
      "Integrated MS/PhD program": "석박사통합과정",
      Undecided: "진학 과정 미정",
    }[profile.program] ?? profile.program;
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
  return `${koreanProfessor} 교수님께,

안녕하십니까. 저는 ${profile.interests.slice(0, 2).join(" · ") || lab.field}에 관심을 가지고 있는 ${koreanAffiliation}의 ${koreanStatus} ${profile.name}입니다. ${purposeLine} ${lab.name}의 연구를 접하고 메일 드립니다.

저는 그동안 ${skillsLine}을(를) 활용해 연구·프로젝트를 수행해왔고, 최근에는 "${project}"를 진행하며 ${interestsLine} 관련 실험을 이어갔습니다. 이 과정에서 표현 학습과 방법론의 중요성을 체감하게 되었습니다.

${lab.name}에서 진행 중인 ${topic} 연구가 제가 관심 있는 방향과 밀접하게 맞닿아 있다고 생각합니다.${extra}

또한 ${koreanProgram} 진학을 준비하고 있어, 가능하시다면 짧게라도 면담 기회를 주실 수 있을지 여쭙고자 합니다. 요청하시는 자료(CV, 성적표, 포트폴리오 등)는 언제든 회신드릴 수 있도록 준비되어 있습니다.

${closing}

감사합니다.
${profile.name} 드림
연락처: 010-1234-5678`;
}

function applyNaturalStyle(draft: string, lab: Lab, profile: UserProfile) {
  const personalAnchor = profile.projects[0] ?? profile.interests[0] ?? lab.field;
  const researchAnchor = lab.recentTopics[0] ?? lab.keywords[0] ?? lab.field;

  return draft
    .replace(
      "바쁘신 와중에 메일 읽어주셔서 감사드리며, 답장 주시면 큰 영광으로 생각하겠습니다.",
      "읽어주셔서 감사합니다. 가능하실 때 답변 주시면 감사하겠습니다.",
    )
    .replace(
      "교수님의 연구실에서 진행 중인",
      `연구실 홈페이지와 최근 연구 내용을 살펴보면서 ${personalAnchor} 경험과 연결해 생각해 본`,
    )
    .replace(
      "연구가 제가 관심 있는 방향과 밀접하게 맞닿아 있다고 생각합니다.",
      `${researchAnchor} 연구가 제가 해 온 경험과 어떻게 이어질 수 있을지 더 알아보고 싶었습니다.`,
    )
    .replace("진심으로 희망합니다.", "관심을 갖고 준비하고 있습니다.");
}

// Mock spellcheck corrections applied to the initial draft.
function makeCorrections(_body: string) {
  if (!/[가-힣]/.test(_body)) {
    return [
      {
        id: "e1",
        original: "I am writing to ask whether you might be available",
        suggestion: "I would appreciate the opportunity to ask whether you may be available",
        reason: "This keeps the request courteous without sounding formulaic.",
      },
      {
        id: "e2",
        original: "connects closely with the questions I hope to explore",
        suggestion: "aligns with the research questions I hope to investigate",
        reason: "The revision is more specific and academically focused.",
      },
    ];
  }
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

  const [lang, setLang] = useState<Lang>("en");
  const [tone, setTone] = useState<Tone>("polite");
  const [length, setLength] = useState<Length>("normal");
  const [purpose, setPurpose] = useState<Purpose>("apply");
  const [naturalStyle, setNaturalStyle] = useState(true);

  const [subject, setSubject] = useState(
    `Prospective Graduate Student Inquiry — ${profile.name} · ${lab.name}`,
  );
  const [body, setBody] = useState(() =>
    applyNaturalStyle(makeDraft(lab, profile, { tone, length, purpose, lang }), lab, profile),
  );
  const historyRef = useRef<{ stack: string[]; index: number }>({ stack: [body], index: 0 });
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

  const regenerateFromApi = async () => {
    setRegenLoading(true);
    try {
      const response = await apiFetch("/email/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          labId: API_LAB_IDS[lab.id] ?? lab.id,
          language: lang,
          tone: tone === "passionate" ? "enthusiastic" : tone,
          length: length === "normal" ? "standard" : length,
          purpose:
            purpose === "apply"
              ? "graduate_application"
              : purpose === "intern"
                ? "internship"
                : "meeting",
        }),
      });
      if (!response.ok) {
        throw new Error(`Email API returned ${response.status}`);
      }
      const draft = (await response.json()) as EmailDraftApiResponse;
      updateBody(draft.body);
      setSubject(draft.subject);
      setCorrections([]);
      setAiRan(false);
      toast.success(
        draft.generationMode === "ai"
          ? "AI draft generated from your profile and lab data"
          : "DB-backed demo draft generated",
      );
    } catch {
      regenerate();
      toast.error("Backend unavailable — showing a local fallback draft");
    } finally {
      setRegenLoading(false);
    }
  };

  const regenerate = () => {
    setRegenLoading(true);
    setTimeout(() => {
      const generated = makeDraft(lab, profile, { tone, length, purpose, lang });
      const next = naturalStyle ? applyNaturalStyle(generated, lab, profile) : generated;
      updateBody(next);
      setSubject(
        lang === "ko"
          ? `[대학원 지원 문의] ${profile.name} — ${lab.name} 컨택드립니다`
          : `Prospective Graduate Student Inquiry — ${profile.name} · ${lab.name}`,
      );
      setRegenLoading(false);
      setCorrections([]);
      setAiRan(false);
      toast.success("Draft regenerated");
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
    toast.success("Suggestion applied");
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
      toast.success(`${corrections.length} suggestions applied`);
    }
    setCorrections([]);
  };
  const openDiff = () => {
    if (corrections.length === 0) return;
    let after = body;
    corrections.forEach((c) => {
      if (after.includes(c.original)) after = after.replace(c.original, c.suggestion);
    });
    setDiffOpen({ before: body, after, label: "Grammar and wording" });
  };

  // Toolbar helpers: wrap selection in textarea
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wrapSelection = (l: string, r = l) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const s = ta.selectionStart;
    const e = ta.selectionEnd;
    const sel = body.slice(s, e) || "text";
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
        title="Write Outreach Email"
        description={`${lab.name} · ${lab.professor}`}
        actions={
          <span className="hidden items-center gap-2 text-xs text-muted-foreground lg:flex">
            <span className="grid h-5 w-5 place-items-center rounded-full bg-[color:var(--success)]/15 text-[color:var(--success)]">
              <Check className="h-3 w-3" />
            </span>
            Autosaved · just now
          </span>
        }
      >
        {/* Breadcrumb */}
        <nav
          aria-label="breadcrumb"
          className="mb-4 flex items-center gap-1.5 text-xs text-muted-foreground"
        >
          <Link to="/" className="hover:text-[color:var(--deep)]">
            Explore Labs
          </Link>
          <ChevronRight className="h-3 w-3" />
          <Link to="/lab/$id" params={{ id: lab.id }} className="hover:text-[color:var(--deep)]">
            {lab.name}
          </Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-[color:var(--navy)]">Write Outreach Email</span>
        </nav>

        {/* Send-safety notice — always visible at top */}
        <section className="rounded-2xl border-2 border-[color:var(--warning)]/50 bg-[color:var(--warning)]/10 p-4">
          <div className="flex items-start gap-3">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[color:var(--warning)]/25 text-[color:oklch(0.42_0.09_75)]">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[color:oklch(0.36_0.09_75)]">
                Ddaksaeu helps you draft and review emails, but never sends them to professors.
              </p>
              <p className="mt-1 text-xs leading-relaxed text-[color:oklch(0.42_0.09_75)]">
                Complete the final review and send the message from your own email app, such as
                Gmail or Outlook. Verify names, affiliations, paper references, and all other facts
                before sending.
              </p>
            </div>
          </div>
        </section>

        <p className="mt-3 flex items-center gap-2 px-1 text-sm text-muted-foreground">
          <Info className="h-4 w-4 shrink-0 text-[color:var(--deep)]" />
          Draft from your profile and lab data, edit it in your own voice, and review every fact
          before sending.
        </p>

        <section
          className="mt-3 rounded-2xl border border-border bg-white p-4"
          aria-label="Email settings"
        >
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <SettingRow label="Email language">
              <SegSelect
                value={lang}
                onChange={(v) => setLang(v as Lang)}
                options={[
                  { v: "ko", l: "Korean" },
                  { v: "en", l: "English" },
                ]}
              />
            </SettingRow>
            <SettingRow label="Tone">
              <SegSelect
                value={tone}
                onChange={(v) => setTone(v as Tone)}
                options={[
                  { v: "polite", l: "Polite" },
                  { v: "concise", l: "Concise" },
                  { v: "passionate", l: "Enthusiastic" },
                ]}
              />
            </SettingRow>
            <SettingRow label="Length">
              <SegSelect
                value={length}
                onChange={(v) => setLength(v as Length)}
                options={[
                  { v: "short", l: "Short" },
                  { v: "normal", l: "Standard" },
                  { v: "detailed", l: "Detailed" },
                ]}
              />
            </SettingRow>
            <SettingRow label="Purpose">
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
          </div>
          <label className="mt-3 flex cursor-pointer items-center gap-2 border-t border-border pt-3">
            <Checkbox
              checked={naturalStyle}
              onCheckedChange={(checked) => setNaturalStyle(checked === true)}
            />
            <span className="text-sm font-medium text-[color:var(--navy)]">
              Natural, personal style
            </span>
            <Badge className="rounded-full bg-[color:var(--point)]/10 px-1.5 py-0 text-[10px] font-medium text-[color:var(--deep)] hover:bg-[color:var(--point)]/10">
              Recommended
            </Badge>
          </label>
        </section>

        <section
          className="mt-3 rounded-2xl border border-border bg-white px-4 py-3"
          aria-label="Attachments"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 flex items-center gap-1.5 text-xs font-semibold text-[color:var(--navy)]">
              <Paperclip className="h-3.5 w-3.5" /> Attachments
            </span>
            {attachments.map((a) => (
              <span
                key={a.id}
                className="inline-flex h-8 items-center gap-2 rounded-lg border border-border bg-[color:var(--surface)] px-2.5 text-xs"
              >
                <Checkbox
                  checked={a.checked}
                  onCheckedChange={(v) =>
                    setAttachments((s) =>
                      s.map((x) => (x.id === a.id ? { ...x, checked: v === true } : x)),
                    )
                  }
                />
                <span className="max-w-52 truncate font-medium text-[color:var(--navy)]">
                  {a.name}
                </span>
                <button
                  type="button"
                  onClick={() => setAttachments((s) => s.filter((x) => x.id !== a.id))}
                  aria-label={`Remove ${a.name}`}
                  className="text-muted-foreground hover:text-[color:var(--navy)]"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            ))}
            <label className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-lg border border-dashed border-[color:var(--point)]/50 px-3 text-xs font-medium text-[color:var(--deep)] hover:bg-[color:var(--point)]/5">
              <Plus className="h-3.5 w-3.5" /> Add CV or portfolio
              <input
                type="file"
                accept=".pdf"
                multiple
                className="sr-only"
                onChange={(event) => {
                  const files = Array.from(event.target.files ?? []);
                  if (files.length === 0) return;
                  setAttachments((current) => [
                    ...current,
                    ...files.map((file, index) => ({
                      id: `upload-${Date.now()}-${index}`,
                      name: file.name,
                      checked: true,
                      size: `${Math.max(1, Math.round(file.size / 1024))} KB`,
                    })),
                  ]);
                  event.target.value = "";
                  toast.success(`${files.length} file${files.length > 1 ? "s" : ""} added`);
                }}
              />
            </label>
            <span className="ml-auto text-[11px] text-muted-foreground">
              PDF only · Review before export
            </span>
          </div>
        </section>

        <section className="hidden" aria-label="AI email tools">
          <button
            type="button"
            onClick={() => openAssistant("settings")}
            className="rounded-2xl border border-border bg-white p-4 text-left transition hover:border-[color:var(--point)]/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--point)]"
          >
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-[color:var(--point)]/10 text-[color:var(--deep)]">
              <Sparkles className="h-4 w-4" />
            </span>
            <strong className="mt-3 block text-sm text-[color:var(--navy)]">Draft with AI</strong>
            <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
              Combine your CV and lab information into a draft tailored by purpose and tone.
            </span>
            <span className="mt-3 inline-flex text-xs font-medium text-[color:var(--deep)]">
              Open settings →
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
              Check grammar and wording
            </strong>
            <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
              Find typos and awkward phrases, then compare suggested edits side by side.
            </span>
            <span className="mt-3 inline-flex text-xs font-medium text-[color:var(--deep)]">
              Open checker →
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
            <strong className="mt-3 block text-sm text-[color:var(--navy)]">Review with AI</strong>
            <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
              Review politeness, clarity, specificity, and exaggerated wording before sending.
            </span>
            <span className="mt-3 inline-flex text-xs font-medium text-[color:var(--deep)]">
              Open review →
            </span>
          </button>
        </section>

        {/* Main */}
        <div className="mt-5 grid gap-4">
          {/* Editor column */}
          <div className="min-w-0 space-y-5">
            <section className="rounded-2xl border border-border bg-white">
              {/* Header meta */}
              <div className="space-y-3 border-b border-border p-5">
                <div className="grid gap-2">
                  <Label htmlFor="to" className="text-xs text-muted-foreground">
                    To
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
                            toast.success("Email address copied");
                          }}
                          aria-label="Copy email address"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Copy email address</TooltipContent>
                    </Tooltip>
                  </div>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="subject" className="text-xs text-muted-foreground">
                    Subject
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
                <ToolBtn label="Undo" onClick={undo} disabled={historyRef.current.index <= 0}>
                  <Undo2 className="h-4 w-4" />
                </ToolBtn>
                <ToolBtn
                  label="Run again"
                  onClick={redo}
                  disabled={historyRef.current.index >= historyRef.current.stack.length - 1}
                >
                  <Redo2 className="h-4 w-4" />
                </ToolBtn>
                <span className="mx-1 h-4 w-px bg-border" />
                <ToolBtn label="Bold" onClick={() => wrapSelection("**")}>
                  <Bold className="h-4 w-4" />
                </ToolBtn>
                <ToolBtn label="Underline" onClick={() => wrapSelection("__")}>
                  <Underline className="h-4 w-4" />
                </ToolBtn>
                <ToolBtn label="Bulleted list" onClick={() => wrapSelection("\n- ", "")}>
                  <List className="h-4 w-4" />
                </ToolBtn>
                <ToolBtn label="Link" onClick={() => wrapSelection("[", "](https://)")}>
                  <Link2 className="h-4 w-4" />
                </ToolBtn>
                <div className="ml-auto flex items-center gap-1 text-[11px] text-muted-foreground">
                  <span className="hidden sm:inline">Edit message</span>
                </div>
              </div>

              {/* Personalized preview */}
              <details className="border-b border-border" open>
                <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-5 py-2.5 text-xs text-muted-foreground hover:bg-[color:var(--surface)]">
                  <span className="flex items-center gap-1.5">
                    <Eye className="h-3.5 w-3.5" /> Personalization preview · highlighted profile
                    and lab details
                  </span>
                  <span className="text-[11px]">Expand/collapse</span>
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
                  Message body
                </Label>
                <Textarea
                  id="body"
                  ref={textareaRef}
                  value={body}
                  onChange={(e) => updateBody(e.target.value)}
                  className="min-h-[420px] resize-y rounded-lg font-sans text-sm leading-relaxed"
                  aria-label="Email body"
                />
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-[11px] text-muted-foreground">
                  <div className="flex flex-wrap items-center gap-3 tabular-nums">
                    <span>{charCount.toLocaleString()} characters</span>
                    <span className="text-border">·</span>
                    <span>Estimated read: {readMin} min</span>
                    <span className="text-border">·</span>
                    <span>
                      Last edited{" "}
                      {lastEdited.toLocaleTimeString("en-US", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                </div>
              </div>

              <div className="hidden" aria-label="AI email tools">
                <span className="mr-1 text-xs font-medium text-muted-foreground">AI tools</span>
                <Button
                  type="button"
                  size="sm"
                  className="h-8 gap-1.5 rounded-lg bg-[color:var(--deep)] text-xs hover:bg-[color:var(--navy)]"
                  onClick={regenerateFromApi}
                  disabled={regenLoading}
                >
                  {regenLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  Draft with AI
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-8 gap-1.5 rounded-lg bg-white text-xs"
                  onClick={() => openAssistant("ai", "spell")}
                >
                  <Check className="h-3.5 w-3.5" /> Check grammar
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-8 gap-1.5 rounded-lg bg-white text-xs"
                  onClick={() => openAssistant("ai", "style")}
                >
                  <ShieldCheck className="h-3.5 w-3.5" /> Review with AI
                </Button>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap items-center justify-end gap-2 border-t border-border p-4">
                <Button
                  variant="ghost"
                  className="gap-2 rounded-lg text-muted-foreground hover:text-[color:var(--navy)]"
                  onClick={() => toast.success("Draft saved")}
                >
                  <Save className="h-4 w-4" /> Save draft
                </Button>
                <Button
                  variant="outline"
                  className="gap-2 rounded-lg"
                  onClick={() => {
                    navigator.clipboard?.writeText(`${subject}\n\n${body}`);
                    toast.success("Copied to clipboard");
                  }}
                >
                  <Copy className="h-4 w-4" /> Copy to clipboard
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
                        <Send className="h-4 w-4" /> Export to email
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!canExport && (
                    <TooltipContent side="top">
                      Complete every review item before exporting ({doneChecks}/{totalChecks})
                    </TooltipContent>
                  )}
                </Tooltip>
              </div>
            </section>

            {/* Review checklist */}
            <section className="hidden">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[color:var(--navy)]">
                    Pre-send checklist
                  </h3>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Review each item before sending.
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
                      <Check className="h-3 w-3" /> Review complete
                    </span>
                  )}
                </div>
              </div>
              <ul className="mt-4 space-y-2">
                {(
                  [
                    ["name", "Professor and lab names are correct"],
                    ["facts", "Paper and research-topic references are accurate"],
                    ["files", "CV and portfolio attachments are ready"],
                    ["schedule", "Meeting availability and contact details are correct"],
                    ["tone", "No unnecessary personal data or exaggerated claims"],
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
            <div className="rounded-2xl border border-border bg-white">
              <Tabs value={helperTab} onValueChange={(v) => setHelperTab(v as typeof helperTab)}>
                <TabsList className="grid w-full grid-cols-2 rounded-none rounded-t-2xl border-b border-border bg-[color:var(--surface)] p-1">
                  <TabsTrigger
                    value="context"
                    className="rounded-lg text-xs data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
                  >
                    Context
                  </TabsTrigger>
                  <TabsTrigger value="settings" className="hidden">
                    Email settings
                  </TabsTrigger>
                  <TabsTrigger value="attach" className="hidden">
                    Attachments
                  </TabsTrigger>
                  <TabsTrigger
                    value="ai"
                    className="rounded-lg text-xs data-[state=active]:bg-white data-[state=active]:text-[color:var(--navy)] data-[state=active]:shadow-sm"
                  >
                    <Wand2 className="mr-1 h-3.5 w-3.5" />
                    Assistant
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="context" className="space-y-4 p-4">
                  <PanelSection title="My CV">
                    <ul className="space-y-1.5 text-sm">
                      {[
                        "Interests: Computer Vision, Multimodal Learning",
                        "Skills: PyTorch, OpenCV",
                        "Projects: Medical image classification, video understanding",
                        "Undergraduate research internship",
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
                      Edit profile <ChevronRight className="h-3 w-3" />
                    </Link>
                  </PanelSection>
                  <PanelSection title="Lab information">
                    <ul className="space-y-1.5 text-sm">
                      <li className="flex items-start gap-2 text-foreground/85">
                        <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--success)]" />
                        <span>
                          {lab.professor} · {lab.name}
                        </span>
                      </li>
                      <li className="flex items-start gap-2 text-foreground/85">
                        <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--success)]" />
                        <span>Keywords: {lab.keywords.slice(0, 4).join(", ")}</span>
                      </li>
                      <li className="flex items-start gap-2 text-foreground/85">
                        <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--success)]" />
                        <span>Recent topic: {lab.recentTopics[0]}</span>
                      </li>
                    </ul>
                    <Link
                      to="/lab/$id"
                      params={{ id: lab.id }}
                      className="mt-2 inline-flex items-center gap-1 text-xs text-[color:var(--deep)] hover:underline"
                    >
                      View lab details <ChevronRight className="h-3 w-3" />
                    </Link>
                  </PanelSection>
                </TabsContent>

                <TabsContent value="settings" className="space-y-4 p-4">
                  <SettingRow label="Email language">
                    <SegSelect
                      value={lang}
                      onChange={(v) => setLang(v as Lang)}
                      options={[
                        { v: "ko", l: "Korean" },
                        { v: "en", l: "English" },
                      ]}
                    />
                  </SettingRow>
                  <SettingRow label="Tone">
                    <SegSelect
                      value={tone}
                      onChange={(v) => setTone(v as Tone)}
                      options={[
                        { v: "polite", l: "Polite" },
                        { v: "concise", l: "Concise" },
                        { v: "passionate", l: "Enthusiastic" },
                      ]}
                    />
                  </SettingRow>
                  <SettingRow label="Length">
                    <SegSelect
                      value={length}
                      onChange={(v) => setLength(v as Length)}
                      options={[
                        { v: "short", l: "Short" },
                        { v: "normal", l: "Standard" },
                        { v: "detailed", l: "Detailed" },
                      ]}
                    />
                  </SettingRow>
                  <SettingRow label="Purpose">
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
                  <div className="rounded-xl border border-[color:var(--point)]/30 bg-[color:var(--point)]/5 p-3">
                    <label className="flex cursor-pointer items-start gap-3">
                      <Checkbox
                        checked={naturalStyle}
                        onCheckedChange={(checked) => setNaturalStyle(checked === true)}
                        className="mt-0.5"
                      />
                      <span>
                        <span className="flex items-center gap-1.5 text-sm font-medium text-[color:var(--navy)]">
                          Natural, personal style
                          <Badge className="rounded-full bg-[color:var(--point)]/10 px-1.5 py-0 text-[10px] font-medium text-[color:var(--deep)] hover:bg-[color:var(--point)]/10">
                            On by default
                          </Badge>
                        </span>
                        <span className="mt-1 block text-[11px] leading-relaxed text-muted-foreground">
                          Use specific projects and research interests while reducing repetitive
                          greetings, exaggerated wording, and formulaic sentences.
                        </span>
                      </span>
                    </label>
                  </div>
                  <Button
                    className="w-full gap-2 rounded-lg bg-[color:var(--deep)] hover:bg-[color:var(--navy)]"
                    onClick={regenerateFromApi}
                    disabled={regenLoading}
                  >
                    {regenLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4" />
                    )}
                    Regenerate draft
                  </Button>
                  <p className="text-[11px] leading-relaxed text-muted-foreground">
                    Regenerating replaces your current edits with a new draft. You can restore them
                    with Undo.
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
                        aria-label="Remove attachment"
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
                          name: `Portfolio_${s.length}.pdf`,
                          checked: true,
                          size: "1.2 MB",
                        },
                      ]);
                      toast.success("Portfolio added");
                    }}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border px-3 py-3 text-sm text-muted-foreground transition-colors hover:border-[color:var(--point)]/40 hover:bg-[color:var(--point)]/5 hover:text-[color:var(--deep)]"
                  >
                    <Plus className="h-4 w-4" /> Add portfolio
                  </button>
                  <p className="text-[11px] text-muted-foreground">
                    In this prototype, uploaded files are shown only in the local UI.
                  </p>
                </TabsContent>

                <TabsContent value="ai" className="p-4">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[color:var(--point)]/25 bg-[color:var(--point)]/5 p-3">
                    <div>
                      <p className="text-sm font-medium text-[color:var(--navy)]">
                        Generate a new draft
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        Uses the settings and attachments shown above.
                      </p>
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      className="h-8 gap-1.5 rounded-lg bg-[color:var(--deep)] text-xs hover:bg-[color:var(--navy)]"
                      onClick={regenerateFromApi}
                      disabled={regenLoading}
                    >
                      {regenLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                      )}
                      Draft with AI
                    </Button>
                  </div>
                  <div className="mb-3 flex flex-wrap gap-1">
                    {(
                      [
                        ["spell", "Grammar check"],
                        ["polish", "Polish writing"],
                        ["duplicate", "Repetition"],
                        ["style", "Tone review"],
                        ["shorten", "Shorten"],
                        ["translate", "Translate to English"],
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
                    Run
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
                            ? "All suggestions have been resolved."
                            : "No issues found."
                        }
                        onRetry={runAi}
                      />
                    )}

                    {!aiLoading && aiTool === "spell" && corrections.length > 0 && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-muted-foreground">
                            {corrections.length} suggestions
                          </span>
                          <div className="flex gap-1">
                            <button
                              onClick={openDiff}
                              className="rounded-md px-2 py-1 text-[11px] text-[color:var(--deep)] hover:bg-[color:var(--point)]/10"
                            >
                              Preview changes
                            </button>
                            <button
                              onClick={applyAll}
                              className="rounded-md bg-[color:var(--deep)] px-2 py-1 text-[11px] font-medium text-white hover:bg-[color:var(--navy)]"
                            >
                              Apply all
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
                                Dismiss
                              </button>
                              <button
                                onClick={() => applyCorrection(c.id)}
                                className="rounded-md bg-[color:var(--point)] px-2 py-1 text-[11px] font-medium text-white hover:bg-[color:var(--deep)]"
                              >
                                Apply
                              </button>
                            </div>
                          </div>
                        ))}
                      </>
                    )}

                    {!aiLoading && aiTool === "polish" && polishResult && (
                      <div className="rounded-lg border border-border p-3">
                        <div className="text-[11px] uppercase tracking-widest text-muted-foreground">
                          Original
                        </div>
                        <p className="mt-1 text-xs text-foreground/80">{polishResult.before}</p>
                        <div className="mt-3 text-[11px] uppercase tracking-widest text-muted-foreground">
                          Suggestion
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
                                label: "Polish writing",
                              })
                            }
                            className="rounded-md px-2 py-1 text-[11px] text-[color:var(--deep)] hover:bg-[color:var(--point)]/10"
                          >
                            Preview changes
                          </button>
                          <button
                            onClick={() => {
                              updateBody(body.replace(polishResult.before, polishResult.after));
                              setPolishResult(null);
                              toast.success("Polished sentence applied");
                            }}
                            className="rounded-md bg-[color:var(--point)] px-2 py-1 text-[11px] font-medium text-white hover:bg-[color:var(--deep)]"
                          >
                            Apply
                          </button>
                        </div>
                      </div>
                    )}

                    {!aiLoading && aiTool === "duplicate" && aiRan && (
                      <div className="rounded-lg border border-border p-3 text-xs text-foreground/80">
                        <p className="font-medium text-[color:var(--navy)]">2 repeated phrases</p>
                        <ul className="mt-2 space-y-1.5 text-muted-foreground">
                          <li>
                            · "The word "interest" appears several times. Consider varying the
                            wording.
                          </li>
                          <li>· "A similar request phrase appears twice.</li>
                        </ul>
                      </div>
                    )}

                    {!aiLoading && aiTool === "style" && aiRan && (
                      <div className="space-y-3 rounded-lg border border-border p-3">
                        {[
                          ["Polite", 88],
                          ["Clarity", 74],
                          ["Specificity", 62],
                        ].map(([l, v]) => (
                          <div key={l as string}>
                            <div className="mb-1 flex items-center justify-between text-xs">
                              <span className="text-foreground/80">{l}</span>
                              <span className="tabular-nums text-muted-foreground">{v}</span>
                            </div>
                            <Progress value={v as number} className="h-1.5" />
                          </div>
                        ))}
                        <p className="text-[11px] text-muted-foreground">
                          Mention a specific paper or topic to make the message more concrete.
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
                          setDiffOpen({ before: body, after: short, label: "Shorten" });
                        }}
                        className="w-full rounded-lg border border-border p-3 text-left text-xs hover:bg-[color:var(--surface)]"
                      >
                        <p className="font-medium text-[color:var(--navy)]">
                          A draft about 30% shorter is ready
                        </p>
                        <p className="mt-1 text-muted-foreground">Select to preview the changes</p>
                      </button>
                    )}

                    {!aiLoading && aiTool === "translate" && aiRan && (
                      <button
                        onClick={() => {
                          const en = `Dear Prof. ${lab.professor.replace(" 교수", "")},\n\nI hope this email finds you well. I am ${profile.name}, interested in ${lab.field}. I was drawn to your work on ${lab.recentTopics[0]} and would appreciate the chance to discuss potential graduate study in your lab.\n\nBest regards,\n${profile.name}`;
                          setDiffOpen({ before: body, after: en, label: "Translate to English" });
                        }}
                        className="w-full rounded-lg border border-border p-3 text-left text-xs hover:bg-[color:var(--surface)]"
                      >
                        <p className="font-medium text-[color:var(--navy)]">English draft ready</p>
                        <p className="mt-1 text-muted-foreground">Select to preview the changes</p>
                      </button>
                    )}

                    {!aiRan && !aiLoading && (
                      <p className="rounded-lg border border-dashed border-border p-4 text-center text-xs text-muted-foreground">
                        Choose a tool, then select Run.
                      </p>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </aside>
        </div>

        <section className="mt-4 rounded-2xl border border-border bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-[color:var(--navy)]">
                Final review before sending
              </h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Complete this checklist after writing and AI review.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Progress value={(doneChecks / totalChecks) * 100} className="h-2 w-28" />
              <span className="text-xs tabular-nums text-muted-foreground">
                {doneChecks}/{totalChecks}
              </span>
            </div>
          </div>
          <ul className="mt-4 grid gap-2 md:grid-cols-2">
            {(
              [
                ["name", "Professor and lab names are correct"],
                ["facts", "Paper and research-topic references are accurate"],
                ["files", "CV and portfolio attachments are ready"],
                ["schedule", "Meeting availability and contact details are correct"],
                ["tone", "No unnecessary personal data or exaggerated claims"],
              ] as const
            ).map(([key, label]) => (
              <li
                key={key}
                className="flex items-start gap-2 rounded-lg bg-[color:var(--surface)]/60 px-3 py-2.5"
              >
                <Checkbox
                  id={`final-${key}`}
                  checked={checks[key]}
                  onCheckedChange={(v) => setChecks((s) => ({ ...s, [key]: v === true }))}
                  className="mt-0.5"
                />
                <Label
                  htmlFor={`final-${key}`}
                  className="cursor-pointer text-sm leading-relaxed text-foreground/85"
                >
                  {label}
                </Label>
              </li>
            ))}
          </ul>
        </section>

        {/* Export confirmation */}
        <Dialog open={exportOpen} onOpenChange={setExportOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Move to my email app</DialogTitle>
              <DialogDescription>
                Ddaksaeu does not send email for you. Review the summary, then send it yourself from
                your email app.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 rounded-xl border border-border bg-[color:var(--surface)] p-3 text-sm">
              <SummaryRow k="To" v={`${lab.professor} <${lab.email}>`} />
              <SummaryRow k="Subject" v={subject} />
              <SummaryRow
                k="Attachments"
                v={
                  attachments
                    .filter((a) => a.checked)
                    .map((a) => a.name)
                    .join(", ") || "No attachments"
                }
              />
            </div>
            <div className="flex items-start gap-2 rounded-lg border border-[color:var(--warning)]/40 bg-[color:var(--warning)]/10 px-3 py-2 text-[11px] text-[color:oklch(0.42_0.09_75)]">
              <Info className="mt-0.5 h-3 w-3 shrink-0" />
              <p>
                You are responsible for the final message. Double-check the recipient and
                attachments before sending.
              </p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setExportOpen(false)} className="rounded-lg">
                Cancel
              </Button>
              <Button
                className="gap-2 rounded-lg bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
                onClick={() => {
                  setExportOpen(false);
                  toast.success("Marked as opened in an email app", {
                    description: "The prototype does not open an external app.",
                    action: {
                      label: "Go to calendar",
                      onClick: () => navigate({ to: "/calendar" }),
                    },
                  });
                }}
              >
                <Send className="h-4 w-4" /> Open in email app
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Diff preview */}
        <Dialog open={!!diffOpen} onOpenChange={(o) => !o && setDiffOpen(null)}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>{diffOpen?.label} · Preview changes</DialogTitle>
              <DialogDescription>
                Compare the original and revised versions before applying the change.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border bg-[color:var(--surface)] p-3">
                <div className="mb-2 text-[11px] uppercase tracking-widest text-muted-foreground">
                  Before
                </div>
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-[12px] leading-relaxed text-foreground/85">
                  {diffOpen?.before}
                </pre>
              </div>
              <div className="rounded-lg border border-[color:var(--point)]/30 bg-[color:var(--point)]/5 p-3">
                <div className="mb-2 text-[11px] uppercase tracking-widest text-[color:var(--deep)]">
                  After
                </div>
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-[12px] leading-relaxed text-[color:var(--navy)]">
                  {diffOpen?.after}
                </pre>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDiffOpen(null)} className="rounded-lg">
                Cancel
              </Button>
              <Button
                className="rounded-lg bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
                onClick={() => {
                  if (diffOpen) {
                    updateBody(diffOpen.after);
                    toast.success("Changes applied");
                  }
                  setDiffOpen(null);
                }}
              >
                Apply
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
        Run again
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
