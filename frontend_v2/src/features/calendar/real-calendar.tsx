"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { z } from "zod";
import {
  createEvent, deleteEvent, getAdmissions, getEvents, updateEvent,
  type Admission, type CalendarEvent, WorkspaceApiError,
} from "../workspace/api";

const inputSchema = z.object({
  title: z.string().trim().min(1),
  date: z.iso.date(),
  kind: z.enum(["apply", "contact", "docs", "interview"]),
});
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;
const MONTH_FORMATTER = new Intl.DateTimeFormat("en-US", { month: "long", timeZone: "UTC" });
const SHORT_MONTH_FORMATTER = new Intl.DateTimeFormat("en-US", { month: "short", timeZone: "Asia/Seoul" });
const LONG_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", weekday: "short", timeZone: "Asia/Seoul" });
type ViewFilter = "all" | "official" | "personal";
type CalendarState = "loading" | "ready" | "unauthorized" | "error";
type DisplayEvent = Readonly<{
  id: string;
  title: string;
  date: string;
  source: "Official" | "Personal";
  detail: string;
  sourceUrl: string | null;
  personalId: string | null;
  kind: string;
}>;

function dateKey(value: string): string { return value.slice(0, 10); }
function eventDate(value: string): Date { return new Date(value.length === 10 ? `${value}T12:00:00+09:00` : value); }
function formattedDate(value: string): string { return LONG_DATE_FORMATTER.format(eventDate(value)); }
function seoulDateKey(date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}
function shiftMonth(key: string, delta: number): string {
  const [year = 2026, month = 1] = key.split("-").map(Number);
  const next = new Date(Date.UTC(year, month - 1 + delta, 1));
  return `${next.getUTCFullYear()}-${String(next.getUTCMonth() + 1).padStart(2, "0")}`;
}

export function RealCalendar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requestedDate = searchParams.get("date");
  const today = seoulDateKey();
  const [personal, setPersonal] = useState<readonly CalendarEvent[]>([]);
  const [admissions, setAdmissions] = useState<readonly Admission[]>([]);
  const [state, setState] = useState<CalendarState>("loading");
  const [message, setMessage] = useState("");
  const [view, setView] = useState<ViewFilter>("all");
  const [monthKey, setMonthKey] = useState(() => (requestedDate && /^\d{4}-\d{2}-\d{2}$/.test(requestedDate) ? requestedDate.slice(0, 7) : today.slice(0, 7)));
  const [selectedDate, setSelectedDate] = useState(() => (requestedDate && /^\d{4}-\d{2}-\d{2}$/.test(requestedDate) ? requestedDate : today));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<CalendarEvent | null>(null);

  const selectDate = useCallback((date: string, openDialog = true) => {
    setSelectedDate(date); setMonthKey(date.slice(0, 7));
    const params = new URLSearchParams(searchParams.toString()); params.set("date", date);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    if (openDialog) setDialogOpen(true);
  }, [pathname, router, searchParams]);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") { setDialogOpen(false); setEditing(null); }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  const load = useCallback(() => {
    setState("loading");
    void Promise.all([getEvents(), getAdmissions()]).then(([events, official]) => {
      setPersonal(events); setAdmissions(official); setState("ready");
    }).catch((error: unknown) => {
      if (error instanceof WorkspaceApiError) {
        setState(error.status === 401 ? "unauthorized" : "error");
        setMessage(error.status === 401 ? "Your session has expired. Please log in again." : "Could not load calendar data.");
      }
    });
  }, []);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const displayEvents = useMemo<readonly DisplayEvent[]>(() => {
    const items: DisplayEvent[] = [
      ...personal.map((event) => ({
        id: `personal-${event.id}`, title: event.title, date: event.date, source: "Personal" as const,
        detail: event.memo || event.kind, sourceUrl: null, personalId: event.id, kind: event.kind,
      })),
      ...admissions.map((event) => ({
        id: `official-${event.id}`, title: event.title, date: event.startAt, source: "Official" as const,
        detail: event.description || event.eventType, sourceUrl: event.sourceUrl, personalId: null, kind: event.eventType,
      })),
    ];
    return items
      .filter((event) => view === "all" || view === "official" && event.source === "Official" || view === "personal" && event.source === "Personal")
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [admissions, personal, view]);

  const [yearText = "2026", monthText = "08"] = monthKey.split("-");
  const year = Number(yearText);
  const month = Number(monthText);
  const firstWeekday = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
  const calendarDays = Array.from({ length: 42 }, (_, index) => {
    const cellDate = new Date(Date.UTC(year, month - 1, index - firstWeekday + 1));
    return `${cellDate.getUTCFullYear()}-${String(cellDate.getUTCMonth() + 1).padStart(2, "0")}-${String(cellDate.getUTCDate()).padStart(2, "0")}`;
  });
  const monthEvents = displayEvents.filter((event) => dateKey(event.date).startsWith(monthKey));

  async function saveEvent(data: FormData): Promise<void> {
    const parsed = inputSchema.safeParse({ title: data.get("title"), date: data.get("date"), kind: data.get("kind") });
    if (!parsed.success) { setMessage("A title and date are required."); return; }
    setMessage("Saving...");
    try {
      const event = editing
        ? await updateEvent(editing.id, parsed.data)
        : await createEvent({ ...parsed.data, labId: null, memo: null });
      setPersonal((items) => (editing ? items.map((item) => item.id === event.id ? event : item) : [...items, event]).sort((a, b) => a.date.localeCompare(b.date)));
      setMonthKey(event.date.slice(0, 7));
      setSelectedDate(event.date); setEditing(null); setDialogOpen(false); setMessage(editing ? "Event updated." : "Event added.");
    } catch (error) {
      setMessage(error instanceof WorkspaceApiError && error.status === 401 ? "Your session has expired. Please log in again." : "Could not save the event.");
    }
  }

  async function remove(id: string): Promise<void> {
    if (!window.confirm("Delete this reminder? This cannot be undone.")) return;
    try {
      await deleteEvent(id);
      setPersonal((items) => items.filter((item) => item.id !== id));
      setMessage("Event deleted.");
    } catch { setMessage("Could not delete the event. It remains in your calendar."); }
  }

  async function download(): Promise<void> {
    try {
      const response = await fetch("/api/backend/admissions/export.ics");
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url; link.download = "admissions-calendar.ics"; link.click();
      URL.revokeObjectURL(url);
    } catch { setMessage("Could not export the ICS calendar."); }
  }

  if (state === "unauthorized") {
    return <main className="calendar-layout"><p>{message}</p><Link href="/login">Log in</Link></main>;
  }

  return (
    <main className="calendar-layout">
      <header className="calendar-heading">
        <div>
          <p className="calendar-kicker">ADMISSIONS CALENDAR</p>
          <h1><span>See admissions deadlines</span><span>at a glance</span></h1>
          <p><span>Track official dates and your own application reminders.</span><span>Confirm every deadline on the official admissions site.</span></p>
        </div>
        <div className="calendar-demo-notice" role="note">
          <strong>Source check required</strong>
          <span>Official dates come from the backend. Confirm each source before applying.</span>
        </div>
      </header>

      <div className="calendar-filter">
        <label htmlFor="calendar-view">Schedule</label>
        <div>
          <select id="calendar-view" value={view} onChange={(event) => setView(event.target.value as ViewFilter)}>
            <option value="all">All dates</option><option value="official">Official admissions</option><option value="personal">My reminders</option>
          </select>
          <button type="button" onClick={() => void download()}>Export calendar</button>
        </div>
      </div>

      {state === "error" && <p className="calendar-status is-error" role="alert">{message} <button onClick={load} type="button">Try again</button></p>}

      <section aria-label={`Application schedule for ${monthKey}`} className="calendar-content">
        <div className="calendar-month-panel">
          <div className="calendar-month-heading">
            <div><span>{year}</span><h2>{MONTH_FORMATTER.format(new Date(Date.UTC(year, month - 1, 1)))}</h2></div>
            <div className="calendar-month-actions"><button aria-label="Previous month" onClick={() => setMonthKey(shiftMonth(monthKey, -1))} type="button">←</button><button onClick={() => { setMonthKey(today.slice(0, 7)); selectDate(today, false); }} type="button">Today</button><button aria-label="Next month" onClick={() => setMonthKey(shiftMonth(monthKey, 1))} type="button">→</button></div><span>{monthEvents.length} {monthEvents.length === 1 ? "date" : "dates"}</span>
          </div>
          <div aria-hidden="true" className="calendar-weekdays">{WEEKDAYS.map((weekday) => <span key={weekday}>{weekday}</span>)}</div>
          <div className="calendar-grid">
            {calendarDays.map((date) => {
              const isCurrentMonth = date.startsWith(monthKey);
              const dayEvents = displayEvents.filter((event) => dateKey(event.date) === date);
              return (
                <button aria-label={`${date}${dayEvents.length ? `, ${dayEvents.length} events` : ""}`} className={`calendar-day${isCurrentMonth ? "" : " calendar-day-outside"}${date === selectedDate ? " is-selected" : ""}${date === today ? " is-today" : ""}`} key={date} onClick={() => selectDate(date)} type="button">
                  <span className="calendar-day-number">{date.slice(-2).replace(/^0/, "")}</span>
                  {dayEvents.slice(0, 2).map((event) => (
                    <div className="calendar-day-event" key={event.id}><strong>{event.title}</strong><span>{event.source}</span><small>{event.source === "Official" ? "Verify date" : "My reminder"}</small></div>
                  ))}
                  {dayEvents.length > 2 && <small className="calendar-more-events">+{dayEvents.length - 2} more</small>}
                </button>
              );
            })}
          </div>
        </div>

        <aside aria-labelledby="upcoming-title" className="calendar-upcoming">
          <div className="calendar-upcoming-heading"><p>UPCOMING AGENDA</p><h2 id="upcoming-title">Upcoming dates</h2></div>
          <form action={(data) => void saveEvent(data)} className="calendar-quick-add">
            <label>Reminder<input name="title" placeholder="Event title" required /></label>
            <div><label>Date<input defaultValue={selectedDate} name="date" required type="date" /></label><label>Type<select name="kind" defaultValue="apply"><option value="apply">Application</option><option value="contact">Contact</option><option value="docs">Documents</option><option value="interview">Interview</option></select></label></div>
            <button type="submit">Add reminder</button>
          </form>
          {state === "loading" ? <p className="calendar-empty-message" role="status">Loading calendar...</p> : displayEvents.length ? (
            <ol className="calendar-agenda">
              {displayEvents.slice(0, 8).map((event) => (
                <li key={event.id}>
                  <div className="calendar-date-block"><strong>{dateKey(event.date).slice(-2)}</strong><span>{SHORT_MONTH_FORMATTER.format(eventDate(event.date))}</span></div>
                  <div className="calendar-event-copy">
                    <div className="calendar-badges"><span>{event.source}</span><span>{event.source === "Official" ? "Verify date" : "User-entered"}</span></div>
                    <h3>{event.title}</h3><p>{formattedDate(event.date)} - Asia/Seoul</p><small>{event.detail}</small>
                    {event.sourceUrl && <a href={event.sourceUrl} rel="noreferrer" target="_blank">Official source <span aria-hidden="true">-&gt;</span></a>}
                    {event.personalId && <button className="calendar-delete-button" onClick={() => void remove(event.personalId!)} type="button">Delete reminder</button>}
                  </div>
                </li>
              ))}
            </ol>
          ) : <p className="calendar-empty-message">No dates are available yet.</p>}
        </aside>
      </section>
      {dialogOpen && <div className="calendar-dialog-backdrop" onMouseDown={() => { setDialogOpen(false); setEditing(null); }} role="presentation"><section aria-labelledby="calendar-dialog-title" aria-modal="true" className="calendar-dialog" onMouseDown={(event) => event.stopPropagation()} role="dialog"><button aria-label="Close date details" className="calendar-dialog-close" onClick={() => { setDialogOpen(false); setEditing(null); }} type="button">×</button><p>{formattedDate(selectedDate)}</p><h2 id="calendar-dialog-title">Events on this date</h2>{displayEvents.filter((event) => dateKey(event.date) === selectedDate).length ? <ul className="calendar-dialog-events">{displayEvents.filter((event) => dateKey(event.date) === selectedDate).map((event) => <li key={event.id}><strong>{event.title}</strong><span>{event.source} · {event.kind}</span><p>{event.detail}</p>{event.personalId && <div><button onClick={() => { const found = personal.find((item) => item.id === event.personalId); if (found) setEditing(found); }} type="button">Edit</button><button onClick={() => void remove(event.personalId!)} type="button">Delete</button></div>}</li>)}</ul> : <p>No events on this date.</p>}<form action={(data) => void saveEvent(data)} className="calendar-dialog-form"><h3>{editing ? "Edit reminder" : "Add reminder"}</h3><label>Reminder<input defaultValue={editing?.title ?? ""} name="title" required /></label><label>Date<input defaultValue={editing?.date ?? selectedDate} name="date" required type="date" /></label><label>Type<select defaultValue={editing?.kind ?? "apply"} name="kind"><option value="apply">Application</option><option value="contact">Contact</option><option value="docs">Documents</option><option value="interview">Interview</option></select></label><button type="submit">{editing ? "Save changes" : "Add reminder"}</button></form></section></div>}
      <p className="calendar-status" aria-live="polite">{message}</p>
    </main>
  );
}
