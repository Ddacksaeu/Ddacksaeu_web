import Link from "next/link";
import { notFound } from "next/navigation";

import { AppHeader } from "../../../src/components/app-header";
import { ContactWorkspace } from "../../../src/features/contact/contact-workspace";
import { createDemoProfessorDetail } from "../../../src/features/professors/demo-professor-detail";
import { ProfessorDetailSections } from "../../../src/features/professors/professor-detail-sections";
import { ProfessorProfileAlignment } from "../../../src/features/professors/professor-profile-alignment";
import { SaveProfessorButton } from "../../../src/features/professors/save-professor-button";
import styles from "../../../src/features/professors/professor-explorer.module.css";
import { LAB_CATALOG_FIXTURES } from "../../../src/fixtures/catalog";

type ProfessorDetailPageProperties = Readonly<{
  params: Promise<{ readonly id: string }>;
}>;

export default async function ProfessorDetailPage({ params }: ProfessorDetailPageProperties) {
  const { id } = await params;
  const professor = LAB_CATALOG_FIXTURES.find((item) => item.id === id);
  if (professor === undefined) notFound();
  const detail = createDemoProfessorDetail(professor);

  return (
    <div className="site-shell">
      <AppHeader current="professors" />
      <main className={styles["page"]}>
        <Link className={styles["link"]} href="/professors">Back to professor search</Link>
        <section className={styles["detailHero"]}>
          <div>
            <div className={styles["meta"]}><span>{professor.institution}</span><span>Demo profile · Source verification required</span></div>
            <h1>{professor.labName.replace(" (Demo)", "\u00a0(Demo)")}</h1><p>{professor.professor}</p>
            <ul className={styles["topics"]}>{professor.topics.map((topic) => <li key={topic}>{topic}</li>)}</ul>
          </div>
          <aside className={styles["sideCard"]}>
            <span>PROFILE MATCH</span><ProfessorProfileAlignment topics={professor.topics} variant="summary" />
            <SaveProfessorButton labId={professor.id} />
            <a href="#contact-draft">Create outreach email draft</a>
          </aside>
        </section>
        <div className={styles["detailGrid"]}>
          <ProfessorDetailSections detail={detail} professor={professor} />
          <section className={styles["section"] + " " + styles["fullSection"]} id="contact-draft">
            <div className={styles["sectionHeading"]}><span>CONTACT WORKSPACE</span><h2>Outreach email draft</h2></div>
            <p>Use the professor’s research and your profile when available, then edit the draft yourself.</p>
            <ContactWorkspace initialProfessor={professor.professor} />
          </section>
        </div>
      </main>
    </div>
  );
}
