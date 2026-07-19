import { AppHeader } from "../../src/components/app-header";
import { ContactWorkspace } from "../../src/features/contact/contact-workspace";
import styles from "../../src/styles/workspace.module.css";

type ContactPageProperties = Readonly<{ searchParams: Promise<Readonly<Record<string, string | readonly string[] | undefined>>> }>;

export default async function ContactPage({ searchParams }: ContactPageProperties) {
  const value = (await searchParams)["professor"];
  const professor = typeof value === "string" ? value : "Professor 02";
  return <div className="site-shell"><AppHeader current="contact" /><main className={styles["page"]}><header className={styles["hero"]}><p className={styles["eyebrow"]}>OUTREACH</p><h1>Outreach email draft</h1><p>Connect your CV experience with the professor’s recent work, then edit the draft yourself.</p></header><ContactWorkspace initialProfessor={professor} /></main></div>;
}
