"use client";

import { useMemo, useState } from "react";

type LabDetailWorkspaceProperties = {
  readonly professor: string;
  readonly topics: readonly string[];
};

export function LabDetailWorkspace({ professor, topics }: LabDetailWorkspaceProperties) {
  const initialDraft = useMemo(() =>
    `${professor}\n\nHello,\nI am interested in ${topics.join(", ")}.\nI am preparing for graduate study and would like to learn more about your lab's research.\n\nThank you for your consideration.`,
  [professor, topics]);
  const [draft, setDraft] = useState(initialDraft);
  const [copied, setCopied] = useState(false);

  async function copyDraft(): Promise<void> {
    await navigator.clipboard.writeText(draft);
    setCopied(true);
  }

  return (
    <div className="lab-detail-grid">
      <div className="detail-main-column">
        <section className="detail-section">
          <p className="section-kicker">LAB SNAPSHOT</p>
          <h2>Lab site and research keyword analysis</h2>
          <div className="analysis-callout"><strong>Research analysis</strong><p>This summary uses available public keywords and will refresh after crawler integration.</p></div>
          <div className="keyword-cloud">{topics.map((topic) => <span key={topic}>{topic}</span>)}</div>
          <ul className="evidence-list">
            <li><span>Research alignment</span><strong>{topics.length > 1 ? "Two or more keywords available" : "More keywords needed"}</strong></li>
            <li><span>Evidence status</span><strong>Institution link found · Details unverified</strong></li>
            <li><span>Uncertainty</span><strong>Check the official notice for recruitment status</strong></li>
          </ul>
        </section>

        <section className="detail-section">
          <p className="section-kicker">PAPER PREVIEW</p>
          <h2>Paper analysis preview</h2>
          <div className="paper-preview"><span>PREVIEW</span><div><strong>{topics[0]} research trend summary</strong><p>Preview shown before public paper data is connected.</p></div></div>
          <div className="paper-preview"><span>PREVIEW</span><div><strong>{topics[1] ?? topics[0]} method keywords</strong><p>Preview of title, abstract, and source.</p></div></div>
        </section>

        <section className="detail-section">
          <p className="section-kicker">CONTACT DRAFT</p>
          <h2>Outreach email draft</h2>
          <label className="draft-label">Email body<textarea value={draft} onChange={(event) => { setDraft(event.target.value); setCopied(false); }} /></label>
          <button className="primary-button compact-button" onClick={copyDraft} type="button">{copied ? "Copied" : "Copy draft"}</button>
          <p className="draft-warning">This email is not sent automatically. Verify the facts and recipient before use.</p>
        </section>
      </div>

      <aside className="community-panel">
        <p className="section-kicker">COMMUNITY</p>
        <h2>Community</h2>
        <p>The first version does not publish unverified reviews of professors or labs.</p>
        <article><span>Application tip</span><strong>Review research keywords and recent notices before your first email.</strong><small>Operations guide</small></article>
        <article><span>CV checklist</span><strong>Summarize your project outcome and personal contribution in one sentence.</strong><small>Community guide</small></article>
      </aside>
    </div>
  );
}
