"use client";

import { useEffect, useRef, useState } from "react";

import { CvRecommendations } from "../recommendations/cv-recommendations";
import type { DocumentAnalysis } from "./document-analysis";
import { analyzeDocument, DocumentApiError, getDocumentHistory, getLatestDocumentAnalysis, validateDocumentFile } from "./documents-api";
import { CvAnalysisResult } from "./cv-analysis-result";

function formatSize(size: number): string { return `${Math.max(1, Math.ceil(size / 1024))} KB`; }

export function CvAnalysisPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [history, setHistory] = useState<readonly DocumentAnalysis[]>([]);
  const [state, setState] = useState<"loading" | "idle" | "uploading" | "error" | "unauthenticated">("loading");
  const [message, setMessage] = useState("");
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    void Promise.all([getLatestDocumentAnalysis(), getDocumentHistory()]).then(([latest, items]) => {
      if (!active) return;
      setAnalysis(latest); setHistory(items); setState("idle");
    }).catch((error: unknown) => {
      if (!active) return;
      const apiError = error instanceof DocumentApiError ? error : new DocumentApiError(0, "Could not connect to the server. Check that the backend is running.");
      setState(apiError.status === 401 || apiError.status === 403 ? "unauthenticated" : "error");
      setMessage(apiError.message);
    });
    return () => { active = false; };
  }, []);

  function select(next: File | null): void {
    setFile(next);
    setMessage(next === null ? "" : validateDocumentFile(next) ?? "");
    if (state === "error") setState("idle");
  }

  async function upload(): Promise<void> {
    if (file === null) return;
    const validation = validateDocumentFile(file);
    if (validation) { setMessage(validation); return; }
    setState("uploading"); setMessage("Uploading and analyzing your CV…");
    try {
      const result = await analyzeDocument(file);
      setAnalysis(result); setHistory((items) => [result, ...items.filter((item) => item.analysis_id !== result.analysis_id)]);
      setMessage("CV uploaded and analyzed successfully."); setFile(null);
      if (input.current !== null) input.current.value = "";
      setState("idle");
    } catch (error) {
      const apiError = error instanceof DocumentApiError ? error : new DocumentApiError(0, "Could not connect to the server. Check that the backend is running.");
      setState(apiError.status === 401 || apiError.status === 403 ? "unauthenticated" : "error"); setMessage(apiError.message);
    }
  }

  return <section className="cv-analysis-panel" aria-labelledby="cv-upload-title">
    <div className="profile-section-heading"><div><p>Application materials</p><h2 id="cv-upload-title">CV analysis</h2></div><span>PDF, DOCX, TXT · up to 10 MB</span></div>
    <label className="cv-upload-control"><input aria-label="Select CV file" ref={input} type="file" accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain" disabled={state === "uploading"} onChange={(event) => select(event.target.files?.item(0) ?? null)} /><span>{file === null ? "Choose a CV file" : "Replace CV file"}</span></label>
    {file !== null && <div className="cv-selected-file"><strong>{file.name}</strong><small>{formatSize(file.size)}</small><button type="button" onClick={() => select(null)} disabled={state === "uploading"}>Remove</button></div>}
    <button className="primary-button" type="button" disabled={file === null || state === "uploading" || message.length > 0 && validateDocumentFile(file ?? new File([], "")) !== null} onClick={() => void upload()}>{state === "uploading" ? "Analyzing…" : "Upload and analyze"}</button>
    {state === "loading" && <p className="form-status" role="status">Loading your latest CV analysis…</p>}
    {state === "unauthenticated" && <p className="form-status is-error" role="alert">{message}</p>}
    {state === "error" && <div className="form-status is-error" role="alert"><p>{message}</p><button className="secondary-button" type="button" onClick={() => window.location.reload()}>Try again</button></div>}
    {state === "idle" && message && <p className="form-status" aria-live="polite">{message}</p>}
    {analysis === null && state === "idle" && <div className="profile-dashboard-empty"><strong>No analyzed CV yet</strong><p>Upload a CV to view its local rule-based analysis.</p></div>}
    {analysis !== null && <><CvAnalysisResult analysis={analysis} /><CvRecommendations analysisId={analysis.analysis_id} /></>}
    {history.length > 1 && <section className="cv-history" aria-labelledby="cv-history-title"><h3 id="cv-history-title">Recent analyses</h3><ul>{history.map((item) => <li key={item.analysis_id}><button aria-pressed={item.analysis_id === analysis?.analysis_id} onClick={() => setAnalysis(item)} type="button"><strong>{item.original_filename ?? "Untitled CV"}</strong><span>{item.file_type ?? "Unknown format"} · {item.analyzer_origin}</span></button></li>)}</ul></section>}
  </section>;
}
