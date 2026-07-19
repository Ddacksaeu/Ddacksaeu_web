import { AppHeader } from "../../src/components/app-header";
import { CvAnalysisPanel } from "../../src/features/profile/cv-analysis-panel";
import styles from "../../src/styles/workspace.module.css";

export default function CvAnalysisPage() {
  return <div className="site-shell"><AppHeader current="cv" /><main className={styles["page"]}><header className={styles["hero"]}><p className={styles["eyebrow"]}>CV ANALYSIS</p><h1>CV and portfolio analysis</h1><p>Upload a CV for server-side local rule-based analysis, then review your experience and find professors whose current work aligns with it.</p></header><CvAnalysisPanel /></main></div>;
}
