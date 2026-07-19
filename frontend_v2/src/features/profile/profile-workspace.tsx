"use client";

import ky from "ky";
import { useEffect, useState } from "react";

import {
  cvSummarySchema,
  profileWorkspaceSchema,
  type ProfileSubmission,
  type ProfileWorkspaceData,
} from "./profile-client-contract";
import { ProfileDashboard } from "./profile-dashboard";
import { ProfileEditor } from "./profile-editor";

const EMPTY_WORKSPACE: ProfileWorkspaceData = {
  profile: null,
  cvAssets: [],
  targetLabIds: [],
  summary: { savedProfessors: 0, contactDrafts: 0, schedules: 0 },
};

export function ProfileWorkspace() {
  const [data, setData] = useState<ProfileWorkspaceData | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingTargetId, setSavingTargetId] = useState<string | null>(null);
  const [status, setStatus] = useState("");

  async function loadWorkspace(): Promise<void> {
    const value = await ky.get("/api/profile").json();
    setData(profileWorkspaceSchema.parse(value));
  }

  useEffect(() => {
    let active = true;
    void ky.get("/api/profile").json().then((value) => {
      if (active) setData(profileWorkspaceSchema.parse(value));
    }).catch(() => {
      if (active) {
        setData(EMPTY_WORKSPACE);
        setStatus("Could not load saved information. Try again shortly.");
      }
    });
    return () => { active = false; };
  }, []);

  async function saveProfile(submission: ProfileSubmission): Promise<void> {
    setSaving(true);
    setStatus("Saving your profile.");
    try {
      await ky.put("/api/profile", {
        json: {
          consentToStorage: submission.consentToStorage,
          displayName: submission.displayName,
          researchInterests: submission.researchInterests,
          preferredUniversity: submission.preferredUniversity,
          applicationTerm: submission.applicationTerm,
          degreeProgram: submission.degreeProgram,
        },
      });
      if (submission.cvFile !== null) {
        const body = new FormData();
        body.set("cv", submission.cvFile);
        const response = await ky.post("/api/profile", { body }).json<{ readonly cvAsset: unknown }>();
        cvSummarySchema.parse(response.cvAsset);
      }
      await loadWorkspace();
      setEditing(false);
      setStatus("Changes saved.");
    } catch {
      setStatus("Could not save. Check consent and file format.");
    } finally {
      setSaving(false);
    }
  }

  async function resetProfile(): Promise<void> {
    setSaving(true);
    try {
      await ky.delete("/api/profile");
      setData(EMPTY_WORKSPACE);
      setEditing(false);
      setStatus("Deleted the saved profile, CVs, and professors.");
    } catch {
      setStatus("Could not delete your data. Try again shortly.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleTarget(labId: string, saved: boolean): Promise<void> {
    if (data === null) return;
    setSavingTargetId(labId);
    try {
      await ky.patch("/api/profile", { json: { labId, saved } });
      setData({
        ...data,
        targetLabIds: saved
          ? [...data.targetLabIds.filter((id) => id !== labId), labId]
          : data.targetLabIds.filter((id) => id !== labId),
        summary: {
          ...data.summary,
          savedProfessors: saved
            ? data.targetLabIds.includes(labId) ? data.summary.savedProfessors : data.summary.savedProfessors + 1
            : Math.max(0, data.summary.savedProfessors - 1),
        },
      });
      setStatus(saved ? "Saved this professor." : "Removed this professor from saved items.");
    } catch {
      setStatus("Could not update saved professors.");
    } finally {
      setSavingTargetId(null);
    }
  }

  if (data === null) {
    return <div className="profile-loading" role="status"><strong>Loading Profile</strong><span>Checking your saved profile and professors.</span></div>;
  }

  if (data.profile !== null && !editing) {
    return (
      <ProfileDashboard
        data={{ ...data, profile: data.profile }}
        onEdit={() => setEditing(true)}
        onToggleTarget={toggleTarget}
        savingTargetId={savingTargetId}
        status={status}
      />
    );
  }

  return (
    <div className="profile-layout">
      <section className="profile-intro" aria-labelledby="profile-title">
        <p className="kicker">MY RESEARCH PROFILE</p>
        <h1 id="profile-title">{data.profile === null ? "Create research profile" : "Edit research profile"}</h1>
        <p>{data.profile === null ? "Save your name and interests to start personalized professor recommendations and a saved list." : "Update saved information, add a CV, or manage your data."}</p>
        <div className="privacy-note"><span aria-hidden="true">✓</span><div><strong>Your data is private to this session</strong><p>Data is isolated in an anonymous session and can be deleted anytime.</p></div></div>
      </section>
      <ProfileEditor
        assets={data.cvAssets}
        initialProfile={data.profile}
        onCancel={data.profile === null ? null : () => setEditing(false)}
        onReset={resetProfile}
        onSave={saveProfile}
        saving={saving}
        status={status}
      />
    </div>
  );
}
