"use client";

import ky from "ky";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ADMISSION_SCHEDULES } from "../../fixtures/admissions";
import { LAB_CATALOG_FIXTURES } from "../../fixtures/catalog";
import { profileWorkspaceSchema, type ProfileWorkspaceData } from "../profile/profile-client-contract";
import { matchLabsByTopics } from "../recommendations/match-labs";
import styles from "./dashboard.module.css";

const RECOMMENDED_IDS = ["snu-demo-02", "kaist-demo-01", "postech-demo-01"] as const;
const OPENING_IDS = ["kaist-demo-02", "yonsei-demo-02", "postech-demo-03"] as const;
const RECOMMENDED_ID_SET: ReadonlySet<string> = new Set(RECOMMENDED_IDS);
const OPENING_ID_SET: ReadonlySet<string> = new Set(OPENING_IDS);
const DASHBOARD_DATE_FORMATTER = new Intl.DateTimeFormat("en", {
  day: "2-digit",
  month: "short",
  timeZone: "UTC",
});
type CatalogLab = (typeof LAB_CATALOG_FIXTURES)[number];
const FALLBACK_RECOMMENDATIONS = LAB_CATALOG_FIXTURES.reduce<
  Array<{ readonly lab: CatalogLab; readonly matchingTopics: readonly string[] }>
>((items, lab) => {
  if (RECOMMENDED_ID_SET.has(lab.id)) items.push({ lab, matchingTopics: [] });
  return items;
}, []);

function formatDate(date: string): string {
  return DASHBOARD_DATE_FORMATTER.format(new Date(`${date}T00:00:00Z`));
}

export function DashboardHome() {
  const [workspace, setWorkspace] = useState<ProfileWorkspaceData | null>(null);
  const [workspaceReady, setWorkspaceReady] = useState(false);
  const [workspaceFailed, setWorkspaceFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void ky.get("/api/profile").json().then((value) => {
      if (active) setWorkspace(profileWorkspaceSchema.parse(value));
    }).catch(() => {
      if (active) setWorkspaceFailed(true);
    }).finally(() => {
      if (active) setWorkspaceReady(true);
    });
    return () => {
      active = false;
    };
  }, []);

  const profile = workspace?.profile ?? null;
  const exactRecommendations = profile === null
    ? []
    : matchLabsByTopics(LAB_CATALOG_FIXTURES, profile.researchInterests);
  const recommendations = exactRecommendations.length > 0 ? exactRecommendations : FALLBACK_RECOMMENDATIONS;
  const openings = LAB_CATALOG_FIXTURES.filter((lab) => OPENING_ID_SET.has(lab.id));
  const savedCount = workspace?.summary.savedProfessors ?? 0;
  const cvCount = workspace?.cvAssets.length ?? 0;
  const readiness = (profile === null ? 0 : 35)
    + (profile?.researchInterests.length ? 15 : 0)
    + (cvCount > 0 ? 25 : 0)
    + (savedCount > 0 ? 25 : 0);
  const readinessMessage = !workspaceReady
    ? "Loading saved progress"
    : workspaceFailed
      ? "Saved progress is unavailable · Open Profile to retry"
      : profile === null
        ? "Next: create a research profile"
        : cvCount === 0
          ? "Profile ready · Next: add a CV"
          : savedCount === 0
            ? "Profile and CV ready · Next: save professors"
            : "Profile, CV, and saved professors ready";
  const hasPersonalizedMatches = exactRecommendations.length > 0;
  const progressLabel = workspaceFailed ? "Saved progress unavailable" : `Application readiness: ${readiness}%`;

  return (
    <main className={styles["page"]}>
      <header className={styles["pageHeader"]}>
        <div>
          <h1>Home</h1>
          <p>Review professor matches, saved work, and application dates.</p>
        </div>
        <nav aria-label="Dashboard shortcuts" className={styles["headerLinks"]}>
          <Link href="/professors">Find professors</Link>
          <Link href="/cv">Analyze CV</Link>
          <Link href="/calendar">Open calendar</Link>
        </nav>
      </header>

      <section aria-busy={!workspaceReady} aria-label="Application setup" className={styles["statusStrip"]}>
        <div className={styles["statusCopy"]}>
          <span>Application setup</span>
          <strong>{readinessMessage}</strong>
        </div>
        <div
          aria-label={progressLabel}
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={workspaceFailed ? undefined : readiness}
          aria-valuetext={workspaceFailed ? "Saved progress unavailable" : undefined}
          className={styles["progressTrack"]}
          role="progressbar"
        >
          <i style={{ width: `${readiness}%` }} />
        </div>
        <span className={styles["readinessValue"]}>
          {workspaceFailed ? "Unavailable" : workspaceReady ? `${readiness}% ready` : "Loading"}
        </span>
      </section>

      <div className={styles["workspaceGrid"]}>
        <div className={styles["mainColumn"]}>
          <section
            aria-label="Professor recommendations"
            className={`${styles["feedSection"]} ${styles["recommendationSection"]}`}
          >
            <div className={styles["sectionHeader"]}>
              <div>
                <h2>{hasPersonalizedMatches ? "Professors close to your interests" : "Recommended professors"}</h2>
                <p>
                  {hasPersonalizedMatches
                    ? "Ordered by exact overlap with your saved research topics."
                    : workspaceFailed
                      ? "Starter recommendations from the current catalog. Saved personalization is temporarily unavailable."
                    : "Starter recommendations from the current catalog. Add profile topics to personalize this list."}
                </p>
              </div>
              <Link className={styles["sectionAction"]} href="/professors">View all</Link>
            </div>

            <ol className={styles["professorList"]}>
              {recommendations.map(({ lab, matchingTopics }) => (
                <li key={lab.id}>
                  <Link
                    aria-label={`View ${lab.professor} at ${lab.institution}`}
                    className={styles["professorRow"]}
                    href={`/professors/${lab.id}`}
                  >
                    <div className={styles["professorInfo"]}>
                      <div className={styles["professorTopline"]}>
                        <h3>{lab.professor}</h3>
                        <span>Current catalog</span>
                      </div>
                      <p>{lab.institution} · {lab.labName}</p>
                      <div aria-label={`Research topics for ${lab.professor}`} className={styles["topicRow"]}>
                        {lab.topics.map((topic) => <span key={topic}>{topic}</span>)}
                      </div>
                    </div>
                    <div className={styles["rowAction"]}>
                      <strong>{matchingTopics.length > 0 ? `${matchingTopics.length} shared topic${matchingTopics.length === 1 ? "" : "s"}` : "Starter recommendation"}</strong>
                      <span aria-hidden="true">View profile →</span>
                    </div>
                  </Link>
                </li>
              ))}
            </ol>
          </section>

          <section
            aria-labelledby="recruitment-title"
            className={`${styles["feedSection"]} ${styles["recruitmentSection"]}`}
          >
            <div className={styles["sectionHeader"]}>
              <div>
                <h2 id="recruitment-title">Labs with recruitment to verify</h2>
                <p>Check the lab or university source before contacting a professor.</p>
              </div>
              <Link className={styles["sectionAction"]} href="/professors">Change filters</Link>
            </div>
            <ul className={styles["recruitmentList"]}>
              {openings.map((lab) => (
                <li key={lab.id}>
                  <Link aria-label={`View ${lab.labName}`} href={`/professors/${lab.id}`}>
                    <div>
                      <strong>{lab.labName}</strong>
                      <span>{lab.institution} · {lab.professor}</span>
                    </div>
                    <small>Source check needed</small>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <aside aria-label="Application overview" className={styles["overview"]}>
          <section className={`${styles["overviewSection"]} ${styles["profileOverview"]}`}>
            <div className={styles["overviewHeading"]}>
              <h2>Profile readiness</h2>
              <strong>{workspaceFailed ? "—" : workspaceReady ? `${readiness}%` : "—"}</strong>
            </div>
            <ul className={styles["checklist"]}>
              <li data-complete={profile !== null}>
                <span>Research profile</span>
                <strong>{workspaceFailed ? "Unknown" : profile === null ? "Next" : "Done"}</strong>
              </li>
              <li data-complete={cvCount > 0}>
                <span>CV or portfolio</span>
                <strong>{workspaceFailed ? "Unknown" : cvCount > 0 ? "Done" : "Add"}</strong>
              </li>
              <li data-complete={savedCount > 0}>
                <span>Saved professors</span>
                <strong>{workspaceFailed ? "Unknown" : savedCount > 0 ? "Done" : "Save"}</strong>
              </li>
            </ul>
            <Link className={styles["railAction"]} href="/profile">
              {workspaceFailed ? "Open Profile" : profile === null ? "Create research profile" : "Manage profile"}
            </Link>
          </section>

          <section className={`${styles["overviewSection"]} ${styles["datesOverview"]}`}>
            <div className={styles["overviewHeading"]}>
              <h2>Upcoming dates</h2>
              <Link href="/calendar">View all</Link>
            </div>
            <ol className={styles["deadlineList"]}>
              {ADMISSION_SCHEDULES.slice(0, 3).map((schedule) => (
                <li key={schedule.id}>
                  <time dateTime={schedule.date}>{formatDate(schedule.date)}</time>
                  <div>
                    <strong>{schedule.stage}</strong>
                    <span>{schedule.institution}</span>
                  </div>
                </li>
              ))}
            </ol>
            <p className={styles["demoNote"]}>Verify dates on the official admissions site.</p>
          </section>

          <section className={`${styles["overviewSection"]} ${styles["savedOverview"]}`}>
            <div className={styles["overviewHeading"]}>
              <h2>Saved work</h2>
            </div>
            <dl className={styles["savedStats"]}>
              <div>
                <dt>Professors</dt>
                <dd>{workspaceFailed ? "—" : savedCount}</dd>
              </div>
              <div>
                <dt>CV files</dt>
                <dd>{workspaceFailed ? "—" : cvCount}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </div>
    </main>
  );
}
