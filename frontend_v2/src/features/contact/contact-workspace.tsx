"use client";

import { useEffect, useState } from "react";

import styles from "../../styles/workspace.module.css";
import {
  createEmailDraft,
  getLab,
  type EmailReview,
  type Lab,
  reviewEmailDraft,
  WorkspaceApiError,
} from "../workspace/api";
import { getContactDraftSnapshot, parseContactDraft, saveContactDraft } from "./contact-draft-store";

type ContactWorkspaceProperties = Readonly<{ initialProfessor: string }>;

export function ContactWorkspace({ initialProfessor }: ContactWorkspaceProperties) {
  const [lab, setLab] = useState<Lab | null>(null);
  const [professor, setProfessor] = useState("");
  const [subject, setSubject] = useState("");
  const [draft, setDraft] = useState("");
  const [review, setReview] = useState<EmailReview | null>(null);
  const [personalizationNotes, setPersonalizationNotes] = useState<readonly string[]>([]);
  const [status, setStatus] = useState("Open this page from a professor detail to create a backend-generated draft.");
  const [busy, setBusy] = useState<"draft" | "review" | null>(null);

  useEffect(() => {
    if (!initialProfessor) return;
    let active = true;
    void getLab(initialProfessor).then((value) => {
      if (!active) return;
      setLab(value);
      setProfessor(value.professorName);
      const saved = parseContactDraft(getContactDraftSnapshot());
      if (saved?.labId === value.id) {
        setSubject(saved.subject);
        setDraft(saved.body);
        setStatus("Restored your saved draft. Edit it, then run the local review.");
      } else {
        setStatus("Ready to create a draft using this professor and your analyzed CV.");
      }
    }).catch(() => {
      if (active) setStatus("Could not load the selected professor. Return to Professor search and try again.");
    });
    return () => { active = false; };
  }, [initialProfessor]);

  async function regenerateDraft(): Promise<void> {
    if (lab === null) return;
    setBusy("draft"); setReview(null);
    setStatus("Creating a local draft from your backend profile and CV...");
    try {
      const next = await createEmailDraft(lab.id);
      setSubject(next.subject); setDraft(next.body);
      setPersonalizationNotes(next.personalizationNotes);
      setStatus("Created a local draft. Review and edit it before use.");
    } catch (error) {
      const apiError = error as WorkspaceApiError;
      setStatus(apiError.status === 401
        ? "Your session has expired. Please log in again."
        : apiError.status === 404
          ? "A saved profile and analyzed CV are required before drafting."
          : "Could not generate a draft.");
    } finally { setBusy(null); }
  }

  async function runReview(): Promise<void> {
    if (lab === null || !subject.trim() || !draft.trim()) return;
    setBusy("review");
    try {
      const result = await reviewEmailDraft(lab.id, subject, draft);
      setReview(result);
      setStatus("Local review completed. No external AI API was used.");
    } catch (error) {
      const apiError = error as WorkspaceApiError;
      setStatus(apiError.status === 401
        ? "Your session has expired. Please log in again."
        : "Could not review the current draft.");
    } finally { setBusy(null); }
  }

  function applyMechanicalFixes(): void {
    if (review === null) return;
    setSubject(review.reviewedSubject); setDraft(review.reviewedBody);
    setStatus("Applied spelling and spacing fixes. Review the content suggestions yourself.");
  }

  async function copyDraft(): Promise<void> {
    await navigator.clipboard.writeText(subject ? `${subject}\n\n${draft}` : draft);
    setStatus("Copied the email draft to your clipboard.");
  }

  function saveDraft(): void {
    if (lab === null) return;
    saveContactDraft({ labId: lab.id, professor, subject, body: draft });
    setStatus("Saved the draft to this browser for your Profile.");
  }

  const details = lab === null
    ? "Select a professor from search or recommendations."
    : [lab.field, ...lab.keywords].filter(Boolean).join(", ");

  return (
    <div className={styles["grid"]}>
      <section className={styles["card"]}>
        <h2>Draft settings and review</h2>
        <label className={styles["field"]}>Professor<input value={professor} placeholder="Select a professor" readOnly /></label>
        <label className={styles["field"]}>Verified lab topics<textarea value={details} readOnly /></label>
        <button className={styles["primary"] + " " + styles["regenerate"]} disabled={lab === null || busy !== null} type="button" onClick={() => void regenerateDraft()}>
          {busy === "draft" ? "Creating..." : draft ? "Regenerate draft" : "Generate draft"}
        </button>
        <button className={styles["secondary"] + " " + styles["regenerate"]} disabled={lab === null || !subject.trim() || !draft.trim() || busy !== null} type="button" onClick={() => void runReview()}>
          {busy === "review" ? "Reviewing..." : "Review my edited draft"}
        </button>
        {personalizationNotes.length > 0 && <div className={styles["analysis"]}>
          <article><h3>Sources used for personalization</h3><ul>{personalizationNotes.map((note) => <li key={note}>{note}</li>)}</ul></article>
        </div>}
        {review && <div className={styles["analysis"]} aria-live="polite">
          <article><h3>Review score: {review.score}/100</h3><p>{review.summary}</p></article>
          {review.issues.length === 0
            ? <article><h3>No major issues found</h3><p>Verify every factual claim before sending.</p></article>
            : review.issues.map((issue) => <article key={`${issue.category}-${issue.message}-${issue.suggestion}`}><h3>{issue.category.replace("_", " ")} · {issue.severity}</h3><p>{issue.message}</p><p><strong>Suggestion:</strong> {issue.suggestion}</p></article>)}
          {(review.reviewedSubject !== subject || review.reviewedBody !== draft) && <button className={styles["secondary"]} type="button" onClick={applyMechanicalFixes}>Apply spelling and spacing fixes</button>}
        </div>}
      </section>
      <section className={styles["card"]}>
        <h2>Edit email</h2>
        <label className={styles["field"]}>Subject<input value={subject} onChange={(event) => { setSubject(event.target.value); setReview(null); }} /></label>
        <label className={styles["field"]}>Email body<textarea value={draft} onChange={(event) => { setDraft(event.target.value); setReview(null); }} /></label>
        <div className={styles["buttonRow"]}>
          <button className={styles["primary"]} disabled={!draft} type="button" onClick={() => void copyDraft()}>Copy</button>
          <button className={styles["secondary"]} disabled={!draft} type="button" onClick={saveDraft}>Save</button>
        </div>
        <p className={styles["status"]} aria-live="polite">{status}</p>
        <p>This page creates and reviews drafts only. It never sends email.</p>
      </section>
    </div>
  );
}
