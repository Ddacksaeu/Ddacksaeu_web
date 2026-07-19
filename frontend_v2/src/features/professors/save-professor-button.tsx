"use client";

import ky, { HTTPError } from "ky";
import { useEffect, useState } from "react";
import { ProfessorSaveIcon } from "./professor-save-icon";

type SaveProfessorButtonProperties = Readonly<{ labId: string }>;

export function SaveProfessorButton({ labId }: SaveProfessorButtonProperties) {
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [ready, setReady] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void ky.get(`/api/backend/labs/${labId}`).json<{ isFavorite: boolean }>().then((value) => {
      setSaved(value.isFavorite);
      setReady(true);
    }).catch(() => { setStatus("Could not load saved state."); setReady(true); });
  }, [labId]);

  async function toggle(): Promise<void> {
    setSaving(true);
    try {
      await (saved ? ky.delete(`/api/backend/me/favorites/${labId}`) : ky.put(`/api/backend/me/favorites/${labId}`));
      setSaved(!saved);
      setStatus(saved ? "Removed this professor from saved items." : "Saved this professor.");
    } catch (error) {
      if (error instanceof HTTPError && error.response.status === 401) window.location.assign("/login");
      else setStatus("Could not update saved state.");
    } finally {
      setSaving(false);
    }
  }

  const buttonLabel = !ready
    ? "Checking saved state"
    : saving
      ? saved ? "Removing saved professor" : "Saving professor"
      : saved ? "Remove saved professor" : "Save professor";

  return (
    <div className="detail-save-control">
      <button aria-busy={saving} aria-label={buttonLabel} aria-pressed={saved} disabled={!ready || saving} onClick={() => void toggle()} title={buttonLabel} type="button">
        <ProfessorSaveIcon saved={saved} />
      </button>
      <span aria-live="polite">{status}</span>
    </div>
  );
}
