"use client";

import { useState, type FormEvent } from "react";

import { extractResearchKeywords } from "./extract-keywords";
import type {
  CvSummary,
  ProfileSubmission,
  ProfileSummary,
} from "./profile-client-contract";

type AnalysisState =
  | { readonly status: "idle" }
  | { readonly status: "ready"; readonly keywords: readonly string[]; readonly note: string }
  | { readonly status: "invalid"; readonly message: string };

type ProfileEditorProperties = Readonly<{
  assets: readonly CvSummary[];
  initialProfile: ProfileSummary | null;
  saving: boolean;
  status: string;
  onCancel: (() => void) | null;
  onReset: () => Promise<void>;
  onSave: (submission: ProfileSubmission) => Promise<void>;
}>;

export function ProfileEditor({
  assets,
  initialProfile,
  saving,
  status,
  onCancel,
  onReset,
  onSave,
}: ProfileEditorProperties) {
  const [displayName, setDisplayName] = useState(initialProfile?.displayName ?? "");
  const [interests, setInterests] = useState(() => initialProfile?.researchInterests.join(", ") ?? "");
  const [preferredUniversity, setPreferredUniversity] = useState(initialProfile?.preferredUniversity ?? "");
  const [applicationTerm, setApplicationTerm] = useState(initialProfile?.applicationTerm ?? "");
  const [degreeProgram, setDegreeProgram] = useState(initialProfile?.degreeProgram ?? "");
  const [consent, setConsent] = useState(initialProfile !== null);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisState>({ status: "idle" });
  const keywords = interests.split(",").map((value) => value.trim()).filter(Boolean);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await onSave({
      consentToStorage: consent,
      cvFile,
      displayName,
      researchInterests: keywords,
      preferredUniversity,
      applicationTerm,
      degreeProgram,
    });
  }

  async function selectCv(file: File | null): Promise<void> {
    setCvFile(file);
    if (file === null) {
      setAnalysis({ status: "idle" });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setAnalysis({ status: "invalid", message: "Select a PDF or TXT file up to 5 MB." });
      return;
    }
    if (file.type === "text/plain") {
      const extracted = extractResearchKeywords(await file.text());
      setAnalysis({
        status: "ready",
        keywords: extracted,
        note: extracted.length > 0
          ? "Found research keywords in the TXT file."
          : "No recognized keywords found. Add them manually.",
      });
      return;
    }
    if (file.type === "application/pdf") {
      setAnalysis({ status: "ready", keywords: [], note: "PDF format verified. Text extraction will be available after crawler integration." });
      return;
    }
    setAnalysis({ status: "invalid", message: "Unsupported file type." });
  }

  function addKeyword(keyword: string): void {
    if (keywords.some((value) => value.toLocaleLowerCase() === keyword.toLocaleLowerCase())) return;
    setInterests([...keywords, keyword].join(", "));
  }

  return (
    <form className="profile-card" onSubmit={submit}>
      <div className="form-heading">
        <div><p>{initialProfile === null ? "Onboarding" : "Edit profile"}</p><h2>Research profile</h2></div>
        <span>{initialProfile === null ? "Create profile" : "Editing"}</span>
      </div>
      <label className="field">Name<input required value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="e.g. Alex Kim" /></label>
      <label className="field">Research interests<textarea value={interests} onChange={(event) => setInterests(event.target.value)} placeholder="e.g. AI, Computer Vision, HCI" /><small>Separate keywords with commas.</small></label>
      <label className="field">Preferred university<select value={preferredUniversity} onChange={(event) => setPreferredUniversity(event.target.value)}><option value="">Not set</option><option>Seoul National University</option><option>KAIST</option><option>POSTECH</option><option>Yonsei University</option></select></label>
      <label className="field">Application term<select value={applicationTerm} onChange={(event) => setApplicationTerm(event.target.value)}><option value="">Not set</option><option>Spring 2027</option><option>Fall 2027</option></select></label>
      <label className="field">Degree program<select value={degreeProgram} onChange={(event) => setDegreeProgram(event.target.value)}><option value="">Not set</option><option>Master&apos;s</option><option>PhD</option><option>Integrated MS/PhD</option></select></label>
      <label className="field file-field">CV file<span className="file-picker"><input aria-describedby="cv-help" className="file-input" type="file" accept="application/pdf,text/plain" onChange={(event) => void selectCv(event.target.files?.item(0) ?? null)} /><span className="file-button">Choose file</span><span className="file-name">{cvFile?.name ?? "No file selected"}</span></span><span id="cv-help">PDF or TXT · Up to 5 MB</span></label>
      {analysis.status !== "idle" && (
        <div className={"cv-analysis-state" + (analysis.status === "invalid" ? " is-error" : "")} aria-live="polite">
          <strong>{analysis.status === "invalid" ? "Check the file" : "CV Analysis results"}</strong>
          {analysis.status === "invalid" ? <p>{analysis.message}</p> : (
            <><p>{analysis.note}</p>{analysis.keywords.length > 0 && <div>{analysis.keywords.map((keyword) => <button key={keyword} onClick={() => addKeyword(keyword)} type="button">+ {keyword}</button>)}</div>}</>
          )}
        </div>
      )}
      {assets.length > 0 && <ul className="asset-list" aria-label="Saved CVs">{assets.map((asset) => <li key={asset.id}><span aria-hidden="true">CV</span><div><strong>{asset.fileName}</strong><small>{Math.max(1, Math.ceil(asset.byteLength / 1024))} KB · Saved</small></div></li>)}</ul>}
      <label className="consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />I consent to saving this profile data</label>
      <button className="primary-button" disabled={saving} type="submit">{saving ? "Saving..." : initialProfile === null ? "Save profile" : "Save changes"}</button>
      {onCancel !== null && <button className="secondary-button profile-cancel-button" disabled={saving} onClick={onCancel} type="button">Cancel editing</button>}
      {initialProfile !== null && <button className="secondary-button" disabled={saving} onClick={() => void onReset()} type="button">Delete all my data</button>}
      <p className="form-status" aria-live="polite">{status}</p>
    </form>
  );
}
