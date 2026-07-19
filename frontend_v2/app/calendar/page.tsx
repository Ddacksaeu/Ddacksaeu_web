import Link from "next/link";
import { z } from "zod";

import { AppHeader } from "../../src/components/app-header";
import { SchedulerChecklist } from "../../src/features/calendar/scheduler-checklist";
import { ADMISSION_SCHEDULES } from "../../src/fixtures/admissions";

const CalendarFilterSchema = z.enum(["all", "Seoul National University", "KAIST", "POSTECH", "Yonsei University"]);
const CALENDAR_DAYS = Array.from({ length: 42 }, (_, index) =>
  index >= 6 && index <= 36 ? index - 5 : null
);
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;
const CALENDAR_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  month: "long",
  day: "numeric",
  weekday: "short",
  timeZone: "Asia/Seoul",
});

type CalendarPageProperties = Readonly<{
  searchParams: Promise<Readonly<Record<string, string | readonly string[] | undefined>>>;
}>;

function selectedInstitution(value: string | readonly string[] | undefined): z.infer<typeof CalendarFilterSchema> {
  const parsed = CalendarFilterSchema.safeParse(value);
  return parsed.success ? parsed.data : "all";
}

function formattedDate(date: string): string {
  return CALENDAR_DATE_FORMATTER.format(new Date(`${date}T12:00:00+09:00`));
}

export default async function CalendarPage({ searchParams }: CalendarPageProperties) {
  const parameters = await searchParams;
  const institution = selectedInstitution(parameters["institution"]);
  const schedules = institution === "all"
    ? ADMISSION_SCHEDULES
    : ADMISSION_SCHEDULES.filter((schedule) => schedule.institution === institution);

  return (
    <div className="site-shell">
      <AppHeader current="calendar" />
      <main className="calendar-layout">
        <header className="calendar-heading">
          <div>
            <p className="calendar-kicker">ADMISSIONS CALENDAR</p>
            <h1><span>See admissions deadlines</span><span>at a glance</span></h1>
            <p><span>Track application milestones by university and lab.</span><span>Confirm every date on the official admissions site.</span></p>
          </div>
          <div className="calendar-demo-notice" role="note">
            <strong>Source check required</strong>
            <span>Confirm each deadline on the official admissions site before applying.</span>
          </div>
        </header>

        <form action="/calendar" className="calendar-filter">
          <label htmlFor="calendar-institution">University</label>
          <div>
            <select defaultValue={institution} id="calendar-institution" name="institution">
              <option value="all">All universities</option>
              <option value="Seoul National University">Seoul National University</option>
              <option value="KAIST">KAIST</option>
              <option value="POSTECH">POSTECH</option>
              <option value="Yonsei University">Yonsei University</option>
            </select>
            <button type="submit">View schedule</button>
          </div>
        </form>

        <section aria-label="Admissions schedule for August 2026" className="calendar-content">
          <div className="calendar-month-panel">
            <div className="calendar-month-heading">
              <div>
                <span>2026</span>
                <h2>August</h2>
              </div>
              <span>{schedules.length} dates</span>
            </div>
            <div aria-hidden="true" className="calendar-weekdays">
              {WEEKDAYS.map((weekday) => <span key={weekday}>{weekday}</span>)}
            </div>
            <div className="calendar-grid">
              {CALENDAR_DAYS.map((day, index) => {
                const daySchedules = day === null
                  ? []
                  : schedules.filter((schedule) => Number(schedule.date.slice(-2)) === day);
                return (
                  <div className={day === null ? "calendar-day calendar-day-empty" : "calendar-day"} key={`${day ?? "empty"}-${index}`}>
                    {day === null ? null : <span className="calendar-day-number">{day}</span>}
                    {daySchedules.map((schedule) => (
                      <div className="calendar-day-event" key={schedule.id}>
                        <strong>{schedule.stage}</strong>
                        <span>{schedule.institution}</span>
                        <small>Verify date</small>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          </div>

          <aside aria-labelledby="upcoming-title" className="calendar-upcoming">
            <div className="calendar-upcoming-heading">
              <p>UPCOMING AGENDA</p>
              <h2 id="upcoming-title">Upcoming dates</h2>
            </div>
            <SchedulerChecklist />
            <ol className="calendar-agenda">
              {schedules.map((schedule) => (
                <li key={schedule.id}>
                  <div className="calendar-date-block">
                    <strong>{schedule.date.slice(-2)}</strong>
                    <span>August</span>
                  </div>
                  <div className="calendar-event-copy">
                    <div className="calendar-badges">
                      <span>Verify date</span>
                      <span>{schedule.stage}</span>
                    </div>
                    <h3>{schedule.lab}</h3>
                    <p>{schedule.institution} · {formattedDate(schedule.date)}</p>
                    <small>{schedule.scheduleNote} · Asia/Seoul</small>
                    <Link href={schedule.officialSourceUrl} rel="noreferrer" target="_blank">
                      {schedule.sourceLabel}
                      <span className="catalog-visually-hidden"> (opens in a new tab)</span>
                      <span aria-hidden="true">↗</span>
                    </Link>
                  </div>
                </li>
              ))}
            </ol>
          </aside>
        </section>
      </main>
    </div>
  );
}
