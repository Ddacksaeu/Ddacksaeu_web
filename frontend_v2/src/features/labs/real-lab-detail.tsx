import Link from "next/link";

import type { LabDetail, LabSummary } from "../../server/backend/labs";
import { ProfessorProfileAlignment } from "../professors/professor-profile-alignment";
import { SaveProfessorButton } from "../professors/save-professor-button";
import contextStyles from "./real-lab-detail-context.module.css";
import styles from "./real-lab-detail.module.css";

type Props = Readonly<{ lab: LabDetail; similar: readonly LabSummary[] | null }>;

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeZone: "Asia/Seoul",
});
const SHORT_KEYWORD_MAX_LENGTH = 32;

function factValue(fact: LabDetail["facts"][number]): string {
  return fact.valueText ?? (fact.valueNumber === null ? "Unavailable" : String(fact.valueNumber));
}

export function RealLabDetail({ lab, similar }: Props) {
  const sourceStatusDate = lab.sourceCheckedAt ?? lab.updatedAt;
  const sourceStatusLabel = lab.sourceCheckedAt ? "Official source checked" : "Profile updated";
  const contextLine = lab.field === "Unclassified"
    ? `${lab.professorName} · ${lab.department}`
    : `${lab.professorName} · ${lab.department} · ${lab.field}`;
  const hasResearchContent = lab.summary !== null || lab.papers.length > 0 || lab.facts.length > 0;
  const publicationHeading = lab.papers.length === 1 ? "Recent publication" : "Recent publications";
  const compactKeywords = lab.keywords.filter((keyword) => keyword.length <= SHORT_KEYWORD_MAX_LENGTH);
  const researchStatements = lab.keywords.filter((keyword) => keyword.length > SHORT_KEYWORD_MAX_LENGTH);

  return (
    <main className={styles["shell"]}>
      <Link className={styles["backLink"]} href="/professors">Back to professor search</Link>

      <header className={styles["hero"]}>
        <p className={styles["eyebrow"]}>POSTECH research lab</p>
        <h1>{lab.name}</h1>
        <p className={styles["contextLine"]}>{contextLine}</p>
        {compactKeywords.length > 0 ? (
          <ul aria-label="Indexed research keywords" className={styles["keywordList"]}>
            {compactKeywords.map((keyword) => <li key={keyword}>{keyword}</li>)}
          </ul>
        ) : null}
        {researchStatements.length > 0 ? (
          <p aria-label="Research focus from source" className={styles["dataNote"]} role="note">
            <strong>Research focus:</strong> {researchStatements.join(" ")}
          </p>
        ) : null}
        {lab.keywords.length === 0 ? (
          <p className={styles["dataNote"]}>Research keywords have not been indexed for this lab yet.</p>
        ) : null}
        <div className={styles["sourceStatus"]}>
          <span>{sourceStatusLabel} {dateFormatter.format(new Date(sourceStatusDate))}</span>
          {lab.sourceUrl
            ? <a href={lab.sourceUrl} rel="noreferrer" target="_blank">View source</a>
            : null}
        </div>
      </header>

      <div className={styles["layout"]}>
        <article aria-label="Professor research profile" className={styles["profile"]}>
          {lab.summary !== null ? (
            <section className={styles["section"]}>
              <p className={styles["sectionLabel"]}>Research profile</p>
              <h2>Lab overview</h2>
              <p className={styles["summary"]}>{lab.summary}</p>
            </section>
          ) : null}

          {lab.papers.length > 0 ? (
            <section className={styles["section"]}>
              <p className={styles["sectionLabel"]}>Published work</p>
              <h2>{publicationHeading}</h2>
              <div className={styles["paperList"]}>
                {lab.papers.map((paper) => (
                  <article className={styles["paperItem"]} data-testid="paper-preview" key={paper.id}>
                    <div className={styles["paperMeta"]}>
                      <span>{paper.publishedYear}</span>
                      <span>{paper.venue}</span>
                    </div>
                    <h3>{paper.title}</h3>
                    {paper.summary ?? paper.abstract
                      ? <p>{paper.summary ?? paper.abstract}</p>
                      : null}
                    {paper.paperUrl
                      ? <a href={paper.paperUrl} rel="noreferrer" target="_blank">Read publication</a>
                      : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {!hasResearchContent ? (
            <section className={`${styles["section"]} ${styles["availability"]}`}>
              <p className={styles["sectionLabel"]}>Research profile</p>
              <h2>Research details are still being indexed</h2>
              <p>Use the official source and contact information while this profile is completed.</p>
            </section>
          ) : null}

          {lab.facts.length > 0 ? (
            <section className={styles["section"]}>
              <p className={styles["sectionLabel"]}>Verified details</p>
              <h2>Lab facts</h2>
              <dl className={styles["factList"]}>
                {lab.facts.map((fact) => (
                  <div key={`${fact.factType}-${fact.valueText ?? fact.valueNumber ?? "unavailable"}-${fact.sourceUrl ?? "no-source"}`}>
                    <dt>{fact.factType}</dt>
                    <dd>
                      <span>{factValue(fact)}</span>
                      {fact.sourceUrl
                        ? <a href={fact.sourceUrl} rel="noreferrer" target="_blank">Source</a>
                        : null}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          <section className={styles["section"]}>
            <p className={styles["sectionLabel"]}>Continue exploring</p>
            <h2>Similar labs</h2>
            {similar === null ? (
              <p className={styles["secondaryText"]}>Similar labs could not be loaded right now.</p>
            ) : similar.length > 0 ? (
              <ul className={styles["similarList"]}>
                {similar.map((item) => (
                  <li key={item.id}>
                    <Link href={`/professors/${item.id}`}>{item.name}</Link>
                    <span>{item.professorName} · {item.department}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles["secondaryText"]}>No closely related labs were found.</p>
            )}
          </section>
        </article>

        <aside aria-label="Application context" className={contextStyles["context"]}>
          <section className={contextStyles["contextSection"]}>
            <p className={contextStyles["sectionLabel"]}>Profile fit</p>
            <h2>Compare your research</h2>
            <div className={contextStyles["alignment"]}>
              <ProfessorProfileAlignment topics={lab.keywords} variant="summary" />
            </div>
          </section>

          {lab.contactEmail || lab.location ? (
            <section className={contextStyles["contextSection"]}>
              <p className={contextStyles["sectionLabel"]}>Contact</p>
              <h2>Reach the lab</h2>
              <dl className={contextStyles["contactList"]}>
                {lab.contactEmail ? (
                  <div><dt>Email</dt><dd><a href={`mailto:${lab.contactEmail}`}>{lab.contactEmail}</a></dd></div>
                ) : null}
                {lab.location ? <div><dt>Location</dt><dd>{lab.location}</dd></div> : null}
              </dl>
            </section>
          ) : null}

          <section className={contextStyles["contextSection"]}>
            <p className={contextStyles["sectionLabel"]}>Application check</p>
            <h2>Recruitment status</h2>
            <p className={contextStyles["guidance"]}>
              <strong>Not verified</strong>
              <span>Check the official lab source and graduate admissions notice for current openings.</span>
            </p>
          </section>

          {lab.homepageUrl || lab.sourceUrl ? (
            <section className={contextStyles["contextSection"]}>
              <p className={contextStyles["sectionLabel"]}>Official links</p>
              <h2>Check the source</h2>
              <div className={contextStyles["sourceLinks"]}>
                {lab.homepageUrl
                  ? <a href={lab.homepageUrl} rel="noreferrer" target="_blank">Visit lab homepage</a>
                  : null}
                {lab.sourceUrl
                  ? <a href={lab.sourceUrl} rel="noreferrer" target="_blank">Open POSTECH profile</a>
                  : null}
              </div>
            </section>
          ) : null}

          <div className={contextStyles["actions"]}>
            <div className={contextStyles["saveRow"]}>
              <span>Save professor</span>
              <SaveProfessorButton labId={lab.id} />
            </div>
            <Link className={`primary-button contact-draft-link ${contextStyles["draftLink"]}`} href={`/contact?professor=${encodeURIComponent(lab.id)}`}>
              Create outreach email draft
            </Link>
            <p>Review the official source before contacting the lab.</p>
          </div>
        </aside>
      </div>
    </main>
  );
}
