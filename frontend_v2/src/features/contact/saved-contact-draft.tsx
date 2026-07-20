"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";

import {
  getContactDraftSnapshot,
  getEmptyContactDraftSnapshot,
  parseContactDraft,
  removeContactDraft,
  subscribeToContactDraft,
} from "./contact-draft-store";

export function SavedContactDraft() {
  const snapshot = useSyncExternalStore(
    subscribeToContactDraft,
    getContactDraftSnapshot,
    getEmptyContactDraftSnapshot,
  );
  const contactDraft = parseContactDraft(snapshot);

  if (contactDraft === null) return null;

  return (
    <section className="profile-contact-panel" aria-labelledby="saved-contact-title">
      <div className="profile-section-heading">
        <div><p>Saved work</p><h2 id="saved-contact-title">Outreach draft in progress</h2></div>
        <span>Saved in this browser</span>
      </div>
      <div className="profile-contact-draft">
        <div>
          <strong>{contactDraft.professor} Outreach email</strong>
          <p>{contactDraft.subject ? `${contactDraft.subject}\n\n${contactDraft.body}` : contactDraft.body}</p>
        </div>
        <div>
          <Link href={`/contact?professor=${encodeURIComponent(contactDraft.labId)}`}>Continue editing</Link>
          <button onClick={removeContactDraft} type="button">Delete</button>
        </div>
      </div>
    </section>
  );
}
