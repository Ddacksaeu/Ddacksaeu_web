"use client";

import ky from "ky";
import { useEffect, useRef, useState } from "react";

import { profileWorkspaceSchema } from "../profile/profile-client-contract";
import { ProfessorSaveIcon } from "./professor-save-icon";

type SaveProfessorButtonProperties = Readonly<{ labId: string }>;

export function SaveProfessorButton({ labId }: SaveProfessorButtonProperties) {
  const profileExists = useRef(false);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [ready, setReady] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void ky.get("/api/profile").json().then((value) => {
      const workspace = profileWorkspaceSchema.parse(value);
      profileExists.current = workspace.profile !== null;
      setSaved(workspace.targetLabIds.includes(labId));
      setReady(true);
    }).catch(() => { setStatus("Could not load saved state."); setReady(true); });
  }, [labId]);

  async function toggle(): Promise<void> {
    if (!profileExists.current) {
      window.location.assign("/profile");
      return;
    }
    setSaving(true);
    try {
      await ky.patch("/api/profile", { json: { labId, saved: !saved } });
      setSaved(!saved);
      setStatus(saved ? "Removed this professor from saved items." : "Saved this professor.");
    } catch {
      setStatus("Could not update saved state.");
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
