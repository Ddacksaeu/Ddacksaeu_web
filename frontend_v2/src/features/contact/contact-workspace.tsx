"use client";

import { useEffect, useState } from "react";
import { createEmailDraft, getLab, type Lab, WorkspaceApiError } from "../workspace/api";
import styles from "../../styles/workspace.module.css";

type ContactWorkspaceProperties = Readonly<{ initialProfessor: string }>;

export function ContactWorkspace({ initialProfessor }: ContactWorkspaceProperties) {
  const [lab, setLab] = useState<Lab | null>(null); const [subject, setSubject] = useState(""); const [body, setBody] = useState(""); const [status, setStatus] = useState("Select a lab from search or recommendations to generate an editable draft."); const [busy, setBusy] = useState(false);
  useEffect(() => { if (!initialProfessor) return; void getLab(initialProfessor).then(setLab).catch(() => setStatus("Select a valid lab to create a draft.")); }, [initialProfessor]);
  async function generate(): Promise<void> { if (!lab) return; setBusy(true); try { const draft = await createEmailDraft(lab.id); setSubject(draft.subject); setBody(draft.body); setStatus(`Draft generated (${draft.generationMode}). Review it before using it.`); } catch (error) { const apiError = error as WorkspaceApiError; setStatus(apiError.status === 401 ? "Your session has expired. Please log in again." : apiError.status === 404 ? "A profile and analyzed CV are required before drafting." : "Could not generate a draft."); } finally { setBusy(false); } }
  async function copy(): Promise<void> { await navigator.clipboard.writeText(`${subject}\n\n${body}`); setStatus("Copied the email draft to your clipboard."); }
  return <div className={styles["grid"]}><section className={styles["card"]}><h2>Draft settings</h2>{lab ? <><p><strong>{lab.professorName} · {lab.name}</strong></p><p>{lab.contactEmail ? `Contact available: ${lab.contactEmail}` : "No professor email is available; this draft is for your review only."}</p></> : <p>Open this page from a lab detail or recommendation.</p>}<button className={styles["primary"]} disabled={!lab || busy} type="button" onClick={() => void generate()}>{busy ? "Generating…" : "Generate draft"}</button></section><section className={styles["card"]}><h2>Edit email</h2><label className={styles["field"]}>Subject<input value={subject} onChange={(event) => setSubject(event.target.value)} /></label><label className={styles["field"]}>Email body<textarea value={body} onChange={(event) => setBody(event.target.value)} /></label><div className={styles["buttonRow"]}><button className={styles["primary"]} disabled={!body} type="button" onClick={() => void copy()}>Copy</button></div><p className={styles["status"]} aria-live="polite">{status}</p><p>This page creates drafts only. It does not send email.</p></section></div>;
}
