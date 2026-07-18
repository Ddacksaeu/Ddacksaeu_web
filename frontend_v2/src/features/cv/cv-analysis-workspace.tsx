"use client";

import { useState } from "react";

import styles from "../../styles/workspace.module.css";

export function CvAnalysisWorkspace() {
  const [fileName, setFileName] = useState("");
  const [analyzed, setAnalyzed] = useState(false);

  return (
    <div className={styles["grid"]}>
      <section className={styles["card"]}>
        <h2>Files to analyze</h2>
        <label className={styles["field"]}>CV / portfolio<span className={styles["filePicker"]}><input aria-describedby="cv-analysis-file-help" className={styles["fileInput"]} accept="application/pdf,text/plain" type="file" onChange={(event) => { setFileName(event.target.files?.item(0)?.name ?? ""); setAnalyzed(false); }} /><span className={styles["fileButton"]}>Choose file</span><span className={styles["fileName"]}>{fileName || "No file selected"}</span></span><small className={styles["fileHelp"]} id="cv-analysis-file-help">PDF or TXT · Up to 5 MB</small></label>
        <label className={styles["field"]}>Application goal<select defaultValue="Master's in Computer Vision"><option value="Master's in Computer Vision">Master’s in Computer Vision</option><option value="Master's in HCI">Master’s in HCI</option><option>PhD in Machine Learning</option></select></label>
        <button className={styles["primary"]} disabled={fileName.length === 0} type="button" onClick={() => setAnalyzed(true)}>Start analysis</button>
        <p className={styles["status"]} aria-live="polite">{fileName.length === 0 ? "Select a PDF or TXT file." : analyzed ? fileName + " analysis is complete." : fileName + " is ready to analyze."}</p>
      </section>
      <section className={styles["card"]} aria-labelledby="analysis-title">
        <h2 id="analysis-title">Analysis results</h2>
        <div className={styles["analysis"]}>
          <article><h3>Extracted research experience</h3><p>{analyzed ? "Found two Computer Vision projects, one undergraduate research role, and Python model development experience." : "Upload a file to structure your work and research experience."}</p></article>
          <article><h3>Strengths</h3><p>{analyzed ? "Your experimental design and reproducibility work are clear, with projects tied directly to professor research keywords." : "Summarize project outcomes and research skills."}</p>{analyzed && <div className={styles["chips"]}><span>Computer Vision</span><span>PyTorch</span><span>Reproduction studies</span></div>}</article>
          <article><h3>Areas to improve</h3><p>{analyzed ? "Quantify your research question and contribution, then connect them to a recent paper by your target professor." : "Get suggestions to strengthen your application."}</p></article>
        </div>
      </section>
    </div>
  );
}
