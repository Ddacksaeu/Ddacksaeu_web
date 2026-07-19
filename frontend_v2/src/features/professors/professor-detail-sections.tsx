import type { LabCatalogEntry } from "../../server/catalog/schema";
import type { DemoProfessorDetail } from "./demo-professor-detail";
import { ProfessorProfileAlignment } from "./professor-profile-alignment";
import styles from "./professor-explorer.module.css";

type ProfessorDetailSectionsProperties = Readonly<{
  detail: DemoProfessorDetail;
  professor: LabCatalogEntry;
}>;

const PROFESSOR_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  dateStyle: "long",
  timeZone: "Asia/Seoul",
});

export function ProfessorDetailSections({ detail, professor }: ProfessorDetailSectionsProperties) {
  const checkedDate = PROFESSOR_DATE_FORMATTER.format(new Date(professor.verifiedAt));

  return (
    <>
      <section className={styles["section"]}>
        <div className={styles["sectionHeading"]}><span>Demo summary</span><h2>Lab overview</h2></div>
        <p>{detail.overview}</p>
        <dl className={styles["detailFacts"]}>
          <div><dt>Affiliation</dt><dd>{detail.department}</dd></div>
          <div><dt>Location</dt><dd>{detail.location}</dd></div>
          <div><dt>Data status</dt><dd>Crawler not connected · Verify source</dd></div>
        </dl>
      </section>

      <section className={styles["section"]}>
        <div className={styles["sectionHeading"]}><span>RESEARCH THEMES</span><h2>Research focus</h2></div>
        <div className={styles["focusList"]}>
          {detail.researchFocus.map((focus, focusIndex) => (
            <article key={`${focus.title}-${focusIndex}`}><h3>{focus.title}</h3><p>{focus.description}</p><ul>{[...new Set(focus.keywords)].map((keyword) => <li key={`${focus.title}-${keyword}`}>{keyword}</li>)}</ul></article>
          ))}
        </div>
      </section>

      <section className={styles["section"]}>
        <div className={styles["sectionHeading"]}><span>WORKFLOW</span><h2>Methods and tools</h2></div>
        <ul className={styles["checkList"]}>{[...new Set(detail.methods)].map((method) => <li key={method}>{method}</li>)}</ul>
      </section>

      <section className={styles["section"]}>
        <div className={styles["sectionHeading"]}><span>DEMO PROJECTS</span><h2>Project examples</h2></div>
        <ol className={styles["projectList"]}>{[...new Set(detail.projects)].map((project, index) => <li key={project}><span>{String(index + 1).padStart(2, "0")}</span><strong>{project}</strong></li>)}</ol>
        <p className={styles["caption"]}>These examples demonstrate the detail layout and are not real projects.</p>
      </section>

      <section className={styles["section"] + " " + styles["fullSection"]}>
        <div className={styles["sectionHeading"]}><span>DEMO PAPER METADATA</span><h2>Recent research and paper preview</h2></div>
        <ol className={styles["papers"]}>{detail.papers.map((paper, index) => <li key={`${paper.title}-${paper.year}-${index}`}><div><span>{paper.year}</span><strong>{paper.title}</strong></div><p>{paper.summary}</p></li>)}</ol>
        <p className={styles["caption"]}>Titles, years, and summaries are fictional metadata. Live paper lists will link to original sources after crawler integration.</p>
      </section>

      <section className={styles["section"]}>
        <div className={styles["sectionHeading"]}><span>FIT EVIDENCE</span><h2>Review profile alignment</h2></div>
        <ProfessorProfileAlignment topics={professor.topics} variant="evidence" />
        <ul className={styles["checkList"]}><li>Review overlapping research keywords</li><li>Compare CV projects and methods</li><li>Identify background gaps and questions to prepare</li></ul>
        <p className={styles["caption"]}>Alignment is not an admission probability.</p>
      </section>

      <section className={styles["section"]}>
        <div className={styles["sectionHeading"]}><span>RECRUITMENT CHECK</span><h2>Recruitment and application details</h2></div>
        <div className={styles["degreeRow"]}>{[...new Set(detail.degreePrograms)].map((degree) => <span key={degree}>{degree}</span>)}</div>
        <p>{detail.recruitmentNote}</p>
        <a href={professor.labUrl} rel="noreferrer" target="_blank">Check the registered lab link</a>
      </section>

      <section className={styles["section"] + " " + styles["fullSection"]}>
        <div className={styles["sectionHeading"]}><span>SOURCE & FRESHNESS</span><h2>Sources and freshness</h2></div>
        <p>{detail.sourceNote}</p>
        <div className={styles["sourceLinks"]}><a href={professor.labUrl} rel="noreferrer" target="_blank">Registered department and lab link</a><a href={professor.officialSourceUrl} rel="noreferrer" target="_blank">Official university website</a><span>Checked {checkedDate}</span></div>
      </section>
    </>
  );
}
