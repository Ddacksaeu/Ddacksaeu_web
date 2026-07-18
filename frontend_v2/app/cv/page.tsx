import { AppHeader } from "../../src/components/app-header";
import { CvAnalysisWorkspace } from "../../src/features/cv/cv-analysis-workspace";
import styles from "../../src/styles/workspace.module.css";

export default function CvAnalysisPage() {
  return <div className="site-shell"><AppHeader current="cv" /><main className={styles["page"]}><header className={styles["hero"]}><p className={styles["eyebrow"]}>CV ANALYSIS</p><h1>CV and portfolio analysis</h1><p>Organize your research experience, strengths, and gaps, then extract keywords to compare with professors.</p></header><CvAnalysisWorkspace /></main></div>;
}
