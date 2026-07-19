import { AppHeader } from "../../src/components/app-header";
import { CvAnalysisWorkspace } from "../../src/features/cv/cv-analysis-workspace";
import { CvAnalysisPanel } from "../../src/features/profile/cv-analysis-panel";
import styles from "../../src/styles/workspace.module.css";

export default function CvAnalysisPage() {
  return <div className="site-shell"><AppHeader current="cv" /><main className={styles["page"]}><header className={styles["hero"]}><p className={styles["eyebrow"]}>CV ANALYSIS</p><h1>CV and portfolio analysis</h1><p>Upload a CV for local rule-based analysis, then organize the resulting research experience, strengths, and gaps.</p></header><CvAnalysisPanel /><div className={styles["planningWorkspace"]}><CvAnalysisWorkspace /></div></main></div>;
}
