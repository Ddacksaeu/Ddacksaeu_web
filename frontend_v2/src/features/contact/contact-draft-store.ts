import { z } from "zod";

const CONTACT_DRAFT_KEY = "ddaksaewoo:contact-draft";
const CONTACT_DRAFT_EVENT = "ddaksaewoo:contact-draft-change";

const contactDraftSchema = z.object({
  professor: z.string().trim().min(1),
  draft: z.string().trim().min(1),
});

export type ContactDraft = z.infer<typeof contactDraftSchema>;

export function getContactDraftSnapshot(): string {
  return window.localStorage.getItem(CONTACT_DRAFT_KEY) ?? "";
}

export function getEmptyContactDraftSnapshot(): string {
  return "";
}

export function parseContactDraft(snapshot: string): ContactDraft | null {
  if (snapshot === "") return null;
  try {
    const parsed = contactDraftSchema.safeParse(JSON.parse(snapshot));
    return parsed.success ? parsed.data : null;
  } catch (error) {
    if (error instanceof SyntaxError) return null;
    throw error;
  }
}

export function subscribeToContactDraft(onChange: () => void): () => void {
  function handleStorage(event: StorageEvent): void {
    if (event.key === CONTACT_DRAFT_KEY) onChange();
  }

  window.addEventListener("storage", handleStorage);
  window.addEventListener(CONTACT_DRAFT_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(CONTACT_DRAFT_EVENT, onChange);
  };
}

export function saveContactDraft(contactDraft: ContactDraft): void {
  const parsed = contactDraftSchema.parse(contactDraft);
  window.localStorage.setItem(CONTACT_DRAFT_KEY, JSON.stringify(parsed));
  window.dispatchEvent(new Event(CONTACT_DRAFT_EVENT));
}

export function removeContactDraft(): void {
  window.localStorage.removeItem(CONTACT_DRAFT_KEY);
  window.dispatchEvent(new Event(CONTACT_DRAFT_EVENT));
}
