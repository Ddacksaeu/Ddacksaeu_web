import { documentAnalysisSchema, type DocumentAnalysis } from "./document-analysis";

export const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set(["pdf", "docx", "txt"]);

export class DocumentApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = "DocumentApiError";
  }
}

function extensionOf(file: File): string {
  return file.name.split(".").pop()?.toLowerCase() ?? "";
}

export function validateDocumentFile(file: File): string | null {
  if (!ALLOWED_EXTENSIONS.has(extensionOf(file))) return "Only PDF, DOCX, and TXT files can be uploaded.";
  if (file.size === 0) return "The selected file is empty.";
  if (file.size > MAX_DOCUMENT_BYTES) return "The selected file exceeds the 10 MB upload limit.";
  return null;
}

function userMessage(status: number, code?: string): string {
  if (status === 0 || code === "backend_unavailable") return "Could not connect to the server. Check that the backend is running.";
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You do not have permission to access this CV.";
  if (status === 404) return "The requested CV analysis could not be found.";
  if (status === 413 || code === "file_too_large") return "The selected file exceeds the 10 MB limit.";
  if (status === 415 || code === "invalid_file_type") return "Please upload a PDF, DOCX, or TXT file.";
  if (code === "empty_file") return "The selected file is empty.";
  if (code === "pdf_text_extraction_failed" || code === "insufficient_text") return "Text could not be extracted from this PDF. OCR is not available; please use a text-based PDF, DOCX, or TXT file.";
  if (status === 422) return "The CV request is invalid. Please check the selected file and try again.";
  if (status >= 500) return "The server could not process this request.";
  return "The CV could not be analyzed. Please check the file and try again.";
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`/api/backend/documents${path}`, { ...init, cache: "no-store" });
  } catch {
    throw new DocumentApiError(0, userMessage(0));
  }
}

async function throwForError(response: Response): Promise<never> {
  let code: string | undefined;
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "error" in body) {
      const error = body.error;
      if (typeof error === "object" && error !== null && "code" in error && typeof error.code === "string") code = error.code;
    }
  } catch { /* Preserve a safe, user-facing error below. */ }
  throw new DocumentApiError(response.status, userMessage(response.status, code));
}

async function parseAnalysis(response: Response): Promise<DocumentAnalysis> {
  if (!response.ok) return throwForError(response);
  return documentAnalysisSchema.parse(await response.json());
}

export async function analyzeDocument(file: File): Promise<DocumentAnalysis> {
  const body = new FormData();
  body.set("file", file);
  return parseAnalysis(await request("/analyze", { method: "POST", body }));
}

export async function getLatestDocumentAnalysis(): Promise<DocumentAnalysis | null> {
  const response = await request("/latest");
  if (response.status === 404) return null;
  return parseAnalysis(response);
}

export async function getDocumentHistory(): Promise<readonly DocumentAnalysis[]> {
  const response = await request("");
  if (!response.ok) return throwForError(response);
  return documentAnalysisSchema.array().parse(await response.json());
}
