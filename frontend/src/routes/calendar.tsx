import { createFileRoute } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight, Plus, Trash2, Filter } from "lucide-react";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  EVENT_KIND_COLOR,
  EVENT_KIND_DOT,
  EVENT_KIND_LABEL,
  LABS,
  type EventKind,
} from "@/lib/mock-data";
import { useAppState } from "@/lib/app-state";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/calendar")({
  component: CalendarPage,
  head: () => ({
    meta: [
      { title: "지원 캘린더 · 딱새우" },
      {
        name: "description",
        content: "대학원 원서, 컨택, 서류 준비, 면접 일정을 한눈에 관리하세요.",
      },
    ],
  }),
});

function pad(n: number) {
  return String(n).padStart(2, "0");
}
function iso(y: number, m: number, d: number) {
  return `${y}-${pad(m + 1)}-${pad(d)}`;
}

function CalendarPage() {
  const { events, addEvent, removeEvent, favorites } = useAppState();
  const [cursor, setCursor] = useState(() => new Date(2026, 6, 1));
  const [showFavOnly, setShowFavOnly] = useState(false);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<{
    title: string;
    kind: EventKind;
    date: string;
    labId: string;
    memo: string;
  }>({
    title: "",
    kind: "apply",
    date: iso(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()),
    labId: "none",
    memo: "",
  });

  const filteredEvents = useMemo(
    () => (showFavOnly ? events.filter((e) => e.labId && favorites.includes(e.labId)) : events),
    [events, showFavOnly, favorites],
  );

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const first = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < first; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const eventsByDay = useMemo(() => {
    const map = new Map<string, typeof events>();
    filteredEvents.forEach((e) => {
      const arr = map.get(e.date) ?? [];
      arr.push(e);
      map.set(e.date, arr);
    });
    return map;
  }, [filteredEvents]);

  const upcoming = [...filteredEvents].sort((a, b) => a.date.localeCompare(b.date)).slice(0, 8);

  const submit = () => {
    if (!form.title.trim()) {
      toast.error("일정 제목을 입력해주세요");
      return;
    }
    addEvent({
      title: form.title,
      kind: form.kind,
      date: form.date,
      labId: form.labId === "none" ? undefined : form.labId,
      memo: form.memo || undefined,
    });
    toast.success("일정이 추가되었어요");
    setOpen(false);
    setForm({ ...form, title: "", memo: "" });
  };

  return (
    <AppShell
      title="지원 캘린더"
      description="원서 접수, 컨택, 서류 준비, 면접 일정을 한곳에서 관리해요."
      actions={
        <Button
          onClick={() => setOpen(true)}
          className="gap-2 rounded-full bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
        >
          <Plus className="h-4 w-4" /> 일정 추가
        </Button>
      }
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Calendar */}
        <section className="rounded-2xl border border-border bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                className="h-9 w-9 rounded-full"
                onClick={() => setCursor(new Date(year, month - 1, 1))}
                aria-label="이전 달"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="min-w-[140px] text-center text-base font-semibold text-[color:var(--navy)]">
                {year}년 {month + 1}월
              </div>
              <Button
                variant="outline"
                size="icon"
                className="h-9 w-9 rounded-full"
                onClick={() => setCursor(new Date(year, month + 1, 1))}
                aria-label="다음 달"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="ml-1 rounded-full text-muted-foreground"
                onClick={() => setCursor(new Date())}
              >
                오늘
              </Button>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs">
                <Filter className="h-3.5 w-3.5 text-muted-foreground" />
                <Label htmlFor="fav-only" className="text-xs text-muted-foreground">
                  저장한 연구실만 보기
                </Label>
                <Switch id="fav-only" checked={showFavOnly} onCheckedChange={setShowFavOnly} />
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-7 text-center text-[11px] uppercase tracking-widest text-muted-foreground">
            {["일", "월", "화", "수", "목", "금", "토"].map((d) => (
              <div key={d} className="py-2">
                {d}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {cells.map((d, i) => {
              if (d === null)
                return <div key={i} className="h-24 rounded-lg bg-[color:var(--surface)]/40" />;
              const key = iso(year, month, d);
              const dayEvents = eventsByDay.get(key) ?? [];
              const today = new Date();
              const isToday =
                today.getFullYear() === year && today.getMonth() === month && today.getDate() === d;
              return (
                <div
                  key={i}
                  className={cn(
                    "h-24 rounded-lg border border-border bg-white p-1.5 text-left transition-colors",
                    isToday && "border-[color:var(--point)] ring-2 ring-[color:var(--point)]/20",
                  )}
                >
                  <div
                    className={cn(
                      "text-xs font-medium tabular-nums",
                      isToday ? "text-[color:var(--point)]" : "text-[color:var(--navy)]",
                    )}
                  >
                    {d}
                  </div>
                  <div className="mt-1 space-y-1 overflow-hidden">
                    {dayEvents.slice(0, 2).map((e) => (
                      <div
                        key={e.id}
                        className={cn(
                          "truncate rounded border px-1.5 py-0.5 text-[10px]",
                          EVENT_KIND_COLOR[e.kind],
                        )}
                      >
                        {e.title}
                      </div>
                    ))}
                    {dayEvents.length > 2 && (
                      <div className="text-[10px] text-muted-foreground">
                        +{dayEvents.length - 2}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 flex flex-wrap gap-3 border-t border-border pt-4 text-xs">
            {(Object.keys(EVENT_KIND_LABEL) as EventKind[]).map((k) => (
              <div key={k} className="flex items-center gap-1.5 text-muted-foreground">
                <span className={cn("h-2 w-2 rounded-full", EVENT_KIND_DOT[k])} />
                {EVENT_KIND_LABEL[k]}
              </div>
            ))}
          </div>
        </section>

        {/* Upcoming */}
        <aside className="rounded-2xl border border-border bg-white p-5">
          <h3 className="text-sm font-semibold text-[color:var(--navy)]">다가오는 일정</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">가까운 순서로 8개까지 표시</p>
          <ul className="mt-4 space-y-3">
            {upcoming.length === 0 && (
              <li className="rounded-xl border border-dashed border-border p-4 text-center text-xs text-muted-foreground">
                예정된 일정이 없어요
              </li>
            )}
            {upcoming.map((e) => {
              const lab = e.labId ? LABS.find((l) => l.id === e.labId) : null;
              return (
                <li
                  key={e.id}
                  className="group rounded-xl border border-border bg-[color:var(--surface)] p-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className={cn("h-2 w-2 rounded-full", EVENT_KIND_DOT[e.kind])} />
                        <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
                          {EVENT_KIND_LABEL[e.kind]}
                        </span>
                      </div>
                      <div className="mt-1 truncate text-sm font-medium text-[color:var(--navy)]">
                        {e.title}
                      </div>
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {e.date}
                        {lab && ` · ${lab.name}`}
                      </div>
                      {e.memo && <div className="mt-1 text-xs text-foreground/70">{e.memo}</div>}
                    </div>
                    <button
                      onClick={() => {
                        removeEvent(e.id);
                        toast("일정을 삭제했어요");
                      }}
                      className="opacity-0 transition-opacity group-hover:opacity-100"
                      aria-label="일정 삭제"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </aside>
      </div>

      {/* Add event modal */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>새 일정 추가</DialogTitle>
            <DialogDescription>지원 관련 일정을 캘린더에 등록합니다.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="ev-title">제목</Label>
              <Input
                id="ev-title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="예: VisLab 컨택 메일 보내기"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>유형</Label>
                <Select
                  value={form.kind}
                  onValueChange={(v) => setForm({ ...form, kind: v as EventKind })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(EVENT_KIND_LABEL) as EventKind[]).map((k) => (
                      <SelectItem key={k} value={k}>
                        {EVENT_KIND_LABEL[k]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ev-date">날짜</Label>
                <Input
                  id="ev-date"
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>관련 연구실 (선택)</Label>
              <Select value={form.labId} onValueChange={(v) => setForm({ ...form, labId: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">선택 안 함</SelectItem>
                  {LABS.map((l) => (
                    <SelectItem key={l.id} value={l.id}>
                      {l.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ev-memo">메모</Label>
              <Textarea
                id="ev-memo"
                value={form.memo}
                onChange={(e) => setForm({ ...form, memo: e.target.value })}
                placeholder="추가 메모"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              취소
            </Button>
            <Button
              onClick={submit}
              className="bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
            >
              저장
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
