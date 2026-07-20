"use client";

import { useEffect, useState } from "react";

import styles from "../../styles/workspace.module.css";
import { getContactDraftSnapshot, parseContactDraft, saveContactDraft } from "./contact-draft-store";
import { createEmailDraft, getLab, type Lab, WorkspaceApiError } from "../workspace/api";

type ContactWorkspaceProperties = Readonly<{ initialProfessor: string }>;

export function ContactWorkspace({ initialProfessor }: ContactWorkspaceProperties) {
  const [lab, setLab] = useState<Lab | null>(null);
  const [professor, setProfessor] = useState("");
  const [subject, setSubject] = useState("");
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("Open this page from a professor detail to create a backend-generated draft.");
  const [busy, setBusy] = useState(false);

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
        setStatus("Restored your saved draft. Review it before copying or saving again.");
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
    setBusy(true);
    setStatus("Generating a draft from your backend profile and CV...");
    try {
      const next = await createEmailDraft(lab.id);
      setSubject(next.subject);
      setDraft(next.body);
      setStatus(`Generated a ${next.generationMode} draft. Review and edit it before use.`);
    } catch (error) {
      const apiError = error as WorkspaceApiError;
      setStatus(apiError.status === 401
        ? "Your session has expired. Please log in again."
        : apiError.status === 404
          ? "A saved profile and analyzed CV are required before drafting."
          : "Could not generate a draft.");
    } finally {
      setBusy(false);
    }
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
        <h2>Draft settings</h2>
        <label className={styles["field"]}>Professor<input value={professor} placeholder="Select a professor" readOnly /></label>
        <label className={styles["field"]}>Details to include<textarea value={details} readOnly /></label>
        <button className={styles["primary"] + " " + styles["regenerate"]} disabled={lab === null || busy} type="button" onClick={() => void regenerateDraft()}>
          {busy ? "Generating..." : draft ? "Regenerate draft" : "Generate draft"}
        </button>
      </section>
      <section className={styles["card"]}>
        <h2>Edit email</h2>
        <label className={styles["field"]}>Subject<input value={subject} onChange={(event) => setSubject(event.target.value)} /></label>
        <label className={styles["field"]}>Email body<textarea value={draft} onChange={(event) => setDraft(event.target.value)} /></label>
        <div className={styles["buttonRow"]}>
          <button className={styles["primary"]} disabled={!draft} type="button" onClick={() => void copyDraft()}>Copy</button>
          <button className={styles["secondary"]} disabled={!draft} type="button" onClick={saveDraft}>Save</button>
        </div>
        <p className={styles["status"]} aria-live="polite">{status}</p>
        <p>This page creates drafts only. It does not send email.</p>
      </section>
    </div>
  );
}
