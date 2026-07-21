"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  getAdmissions, getEvents, getFavorites, getLatestAnalysis, getProfile, getRecommendations,
  type Admission, type CalendarEvent, type Recommendation, type UserProfile, WorkspaceApiError,
} from "../workspace/api";
import styles from "./dashboard.module.css";

type DashboardState = "loading" | "ready" | "unauthorized" | "error";
type TimelineItem = Readonly<{ title: string; date: string; type: string }>;
type ReadinessItem = Readonly<{ label: string; complete: boolean; href: string; action: string }>;
const DATE_FORMATTER = new Intl.DateTimeFormat("en", { day: "2-digit", month: "short", timeZone: "Asia/Seoul" });

function formatDate(value: string): string {
  const date = new Date(value.length === 10 ? `${value}T12:00:00+09:00` : value);
  return Number.isNaN(date.valueOf()) ? "--" : DATE_FORMATTER.format(date);
}

export function DashboardHome() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [recommendations, setRecommendations] = useState<readonly Recommendation[]>([]);
  const [events, setEvents] = useState<readonly CalendarEvent[]>([]);
  const [admissions, setAdmissions] = useState<readonly Admission[]>([]);
  const [hasCv, setHasCv] = useState(false);
  const [savedCount, setSavedCount] = useState(0);
  const [state, setState] = useState<DashboardState>("loading");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    let partialFailure = false;
    async function optional<T>(request: Promise<T>, fallback: T): Promise<T> {
      try { return await request; }
      catch (error) {
        if (error instanceof WorkspaceApiError && (error.status === 404 || error.status === 409)) return fallback;
        partialFailure = true;
        return fallback;
      }
    }
    void Promise.all([
      getProfile(),
      optional(getRecommendations(), [] as readonly Recommendation[]),
      optional(getEvents(), [] as readonly CalendarEvent[]),
      optional(getAdmissions(), [] as readonly Admission[]),
      optional(getLatestAnalysis().then(() => true), false),
      optional(getFavorites(), [] as readonly string[]),
    ]).then(([me, matches, personal, official, cvAvailable, favorites]) => {
      if (!active) return;
      setProfile(me); setRecommendations(matches); setEvents(personal); setAdmissions(official);
      setHasCv(cvAvailable); setSavedCount(favorites.length);
      setNotice(partialFailure ? "Some live data could not be refreshed. Available information is shown." : "");
      setState("ready");
    }).catch((error: unknown) => {
      if (active) setState(error instanceof WorkspaceApiError && error.status === 401 ? "unauthorized" : "error");
    });
    return () => { active = false; };
  }, []);

  if (state === "loading") return <main className={styles["page"]}><p role="status">Loading your dashboard...</p></main>;
  if (state === "unauthorized") return <main className={styles["page"]}><p>Your session has expired.</p><Link href="/login">Log in</Link></main>;
  if (state === "error" || profile === null) return <main className={styles["page"]}><p role="alert">Could not load dashboard data.</p><Link href="/profile">Open Profile</Link></main>;

  const readinessItems: readonly ReadinessItem[] = [
    { label: "Basic profile", complete: Boolean(profile.name.trim() && profile.affiliation.trim()), href: "/profile", action: "Complete profile" },
    { label: "Research interests", complete: profile.interests.length > 0, href: "/profile", action: "Add research interests" },
    { label: "CV or portfolio", complete: hasCv, href: "/cv", action: "Upload CV" },
    { label: "Saved professors", complete: savedCount > 0, href: "/professors", action: "Save a professor" },
    { label: "Application dates", complete: events.length + admissions.filter((item) => !item.isEnded).length > 0, href: "/calendar", action: "Add an application date" },
  ];
  const readiness = readinessItems.filter((item) => item.complete).length * 20;
  const nextReadinessItem = readinessItems.find((item) => !item.complete);
  const readinessMessage = nextReadinessItem ? `Next: ${nextReadinessItem.action.toLowerCase()}` : "Your application setup is complete";
  const admissionTimeline: TimelineItem[] = [];
  for (const event of admissions) {
    if (!event.isEnded) admissionTimeline.push({ title: event.title, date: event.startAt, type: "Admissions" });
  }
  const upcoming: readonly TimelineItem[] = [
    ...events.map((event) => ({ title: event.title, date: event.date, type: "Personal" })),
    ...admissionTimeline,
  ].sort((a, b) => a.date.localeCompare(b.date)).slice(0, 4);

  return (
    <main className={styles["page"]}>
      <header className={styles["pageHeader"]}>
        <div><h1>Home</h1><p>Review professor matches, saved work, and application dates.</p></div>
        <nav aria-label="Dashboard shortcuts" className={styles["headerLinks"]}>
          <Link href="/professors">Find professors</Link><Link href="/cv">Analyze CV</Link><Link href="/calendar">Open calendar</Link>
        </nav>
      </header>
      <section aria-label="Application setup" className={styles["statusStrip"]}>
        <Link aria-label={`Application setup: ${readiness}% ready. ${readinessMessage}`} className={styles["statusLink"]} href={nextReadinessItem?.href ?? "/profile"}>
          <div className={styles["statusCopy"]}><span>Application setup</span><strong>{readinessMessage}</strong></div>
          <div aria-label={`Application readiness: ${readiness}%`} aria-valuemax={100} aria-valuemin={0} aria-valuenow={readiness} className={styles["progressTrack"]} role="progressbar"><i style={{ width: `${readiness}%` }} /></div>
          <span className={styles["readinessValue"]}>{readiness}% ready</span>
        </Link>
      </section>
      {notice && <p aria-live="polite">{notice}</p>}

      <div className={styles["workspaceGrid"]}>
        <div className={styles["mainColumn"]}>
          <section aria-label="Professor recommendations" className={`${styles["feedSection"]} ${styles["recommendationSection"]}`}>
            <div className={styles["sectionHeader"]}>
              <div><h2>Professors close to your interests</h2><p>Generated from your latest CV analysis and current indexed lab data.</p></div>
              <Link className={styles["sectionAction"]} href="/professors">View all</Link>
            </div>
            {recommendations.length ? (
              <ol className={styles["professorList"]}>
                {recommendations.slice(0, 4).map((item) => (
                  <li key={item.labId}>
                    <Link aria-label={`View ${item.professorName} at ${item.labName}`} className={styles["professorRow"]} href={`/professors/${item.labId}`}>
                      <div className={styles["professorInfo"]}>
                        <div className={styles["professorTopline"]}><h3>{item.professorName}</h3><span>{item.totalScore.toFixed(1)} match</span></div>
                        <p>{item.labName}</p>
                        <div aria-label={`Matching topics for ${item.professorName}`} className={styles["topicRow"]}>{item.matchedKeywords.slice(0, 4).map((topic) => <span key={topic}>{topic}</span>)}</div>
                      </div>
                      <div className={styles["rowAction"]}><strong>{item.shortReason}</strong><span aria-hidden="true">View profile -&gt;</span></div>
                    </Link>
                  </li>
                ))}
              </ol>
            ) : <div className={styles["professorList"]}><p>No recommendations yet. Analyze a CV to create personalized matches.</p></div>}
          </section>

          <section aria-labelledby="next-tasks-title" className={`${styles["feedSection"]} ${styles["recruitmentSection"]}`}>
            <div className={styles["sectionHeader"]}>
              <div><h2 id="next-tasks-title">Application tasks to verify</h2><p>Review saved reminders and official admissions dates before acting.</p></div>
              <Link className={styles["sectionAction"]} href="/calendar">Open calendar</Link>
            </div>
            {upcoming.length ? (
              <ul className={styles["recruitmentList"]}>{upcoming.slice(0, 3).map((item) => (
                <li key={`${item.type}-${item.title}-${item.date}`}><Link href={`/calendar?date=${item.date.slice(0, 10)}`}><div><strong>{item.title}</strong><span>{formatDate(item.date)} - {item.type}</span></div><small>View date →</small></Link></li>
              ))}</ul>
            ) : <p>No upcoming tasks yet.</p>}
          </section>
        </div>

        <aside aria-label="Application overview" className={styles["overview"]}>
          <section className={`${styles["overviewSection"]} ${styles["profileOverview"]}`}>
            <div className={styles["overviewHeading"]}><Link aria-label="Manage profile readiness" href="/profile"><h2>Profile readiness</h2><strong>{readiness}%</strong></Link></div>
            <ul className={styles["checklist"]}>
              {readinessItems.map((item) => <li data-complete={item.complete} key={item.label}><Link href={item.href}><span>{item.label}</span><strong>{item.complete ? "Done" : item.action}</strong></Link></li>)}
            </ul>
            <Link className={styles["railAction"]} href={nextReadinessItem?.href ?? "/profile"}>{nextReadinessItem?.action ?? "Review profile"}</Link>
          </section>
          <section className={`${styles["overviewSection"]} ${styles["datesOverview"]}`}>
            <div className={styles["overviewHeading"]}><h2>Upcoming dates</h2><Link href="/calendar">View all</Link></div>
            {upcoming.length ? <ol className={styles["deadlineList"]}>{upcoming.slice(0, 3).map((item) => (
              <li key={`rail-${item.type}-${item.title}-${item.date}`}><Link href={`/calendar?date=${item.date.slice(0, 10)}`}><time dateTime={item.date}>{formatDate(item.date)}</time><div><strong>{item.title}</strong><span>{item.type}</span></div></Link></li>
            ))}</ol> : <p>No upcoming dates.</p>}
            <p className={styles["demoNote"]}>Verify official dates on the source site.</p>
          </section>
          <section className={`${styles["overviewSection"]} ${styles["savedOverview"]}`}>
            <div className={styles["overviewHeading"]}><h2>Saved work</h2></div>
            <dl className={styles["savedStats"]}><div><dt>Professors</dt><dd>{savedCount}</dd></div><div><dt>CV files</dt><dd>{hasCv ? 1 : 0}</dd></div></dl>
          </section>
        </aside>
      </div>
    </main>
  );
}
