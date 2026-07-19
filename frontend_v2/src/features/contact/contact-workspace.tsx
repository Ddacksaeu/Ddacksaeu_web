"use client";

import { useState, useSyncExternalStore } from "react";

import styles from "../../styles/workspace.module.css";
import {
  getContactDraftSnapshot,
  getEmptyContactDraftSnapshot,
  parseContactDraft,
  saveContactDraft,
  subscribeToContactDraft,
} from "./contact-draft-store";

type ContactWorkspaceProperties = Readonly<{ initialProfessor: string }>;

const DEFAULT_DRAFT = "Dear Professor,\n\nI am preparing to apply to graduate programs in Computer Vision. I read your recent work on Multimodal Learning and am reaching out because it aligns with my project experience.\n\nI would appreciate your review of my attached CV. Could you share any upcoming openings and anything else I should prepare?\n\nThank you.";

export function ContactWorkspace({ initialProfessor }: ContactWorkspaceProperties) {
  const savedSnapshot = useSyncExternalStore(
    subscribeToContactDraft,
    getContactDraftSnapshot,
    getEmptyContactDraftSnapshot,
  );
  const savedContactDraft = parseContactDraft(savedSnapshot);
  const [professor, setProfessor] = useState(initialProfessor);
  const [editedDraft, setEditedDraft] = useState<string | null>(null);
  const [status, setStatus] = useState("This draft uses the selected professor and available CV details.");
  const draft = editedDraft ?? (savedContactDraft?.professor === professor ? savedContactDraft.draft : DEFAULT_DRAFT);

  async function copyDraft(): Promise<void> {
    await navigator.clipboard.writeText(draft);
    setStatus("Copied the email draft to your clipboard.");
  }
  function regenerateDraft(): void {
    setEditedDraft(`Dear ${professor},

I am preparing to apply to graduate programs in Computer Vision and am reaching out because your research aligns with my project experience.

I would appreciate your review of my attached CV.

Thank you.`);
    setStatus("Generated a new draft using this professor’s research.");
  }

  function saveDraft(): void {
    saveContactDraft({ professor, draft });
    setStatus("Saved the draft to this browser for your Profile.");
  }


  return (
    <div className={styles["grid"]}>
      <section className={styles["card"]}>
        <h2>Draft settings</h2>
        <label className={styles["field"]}>Professor<input value={professor} onChange={(event) => setProfessor(event.target.value)} /></label>
        <label className={styles["field"]}>Details to include<textarea value="Computer Vision project, PyTorch reproduction study, interest in Multimodal Learning" readOnly /></label>
        <button className={styles["primary"] + " " + styles["regenerate"]} type="button" onClick={regenerateDraft}>Regenerate draft</button>
      </section>
      <section className={styles["card"]}>
        <h2>Edit email</h2>
        <label className={styles["field"]}>Email body<textarea value={draft} onChange={(event) => setEditedDraft(event.target.value)} /></label>
        <div className={styles["buttonRow"]}><button className={styles["primary"]} type="button" onClick={copyDraft}>Copy</button><button className={styles["secondary"]} type="button" onClick={saveDraft}>Save</button></div>
        <p className={styles["status"]} aria-live="polite">{status}</p>
      </section>
    </div>
  );
}
