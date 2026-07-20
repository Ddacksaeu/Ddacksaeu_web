"use client";

import ky from "ky";
import Link from "next/link";
import { useEffect, useState } from "react";
import { analyzeDocument } from "./documents-api";
import type { ProfileSubmission, ProfileWorkspaceData } from "./profile-client-contract";
import { ProfileDashboard } from "./profile-dashboard";
import { ProfileEditor } from "./profile-editor";
import {
  getEvents, getFavorites, getLab, getLatestAnalysis, getProfile,
  saveProfile as saveBackendProfile,
  type DocumentAnalysis, type Lab, type UserProfile, WorkspaceApiError,
} from "../workspace/api";

type LoadState = "loading" | "ready" | "unauthorized" | "error";

function toWorkspace(profile: UserProfile, favorites: readonly string[], eventCount: number, analysis: DocumentAnalysis | null): ProfileWorkspaceData {
  return {
    profile: {
      displayName: profile.name,
      researchInterests: profile.interests,
      preferredUniversity: profile.affiliation,
      applicationTerm: profile.status,
      degreeProgram: profile.program,
      consentedAt: profile.updatedAt,
    },
    cvAssets: analysis === null ? [] : [{
      id: analysis.original_filename ?? "latest-analysis",
      fileName: analysis.original_filename ?? "Analyzed CV",
      contentType: "application/octet-stream",
      byteLength: 0,
    }],
    targetLabIds: favorites,
    summary: { savedProfessors: favorites.length, contactDrafts: 0, schedules: eventCount },
  };
}

export function ProfileWorkspace() {
  const [data, setData] = useState<ProfileWorkspaceData | null>(null);
  const [savedLabs, setSavedLabs] = useState<readonly Lab[]>([]);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingTargetId, setSavingTargetId] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [loadState, setLoadState] = useState<LoadState>("loading");

  async function loadWorkspace(): Promise<void> {
    try {
      const [profile, favorites, events, analysis] = await Promise.all([
        getProfile(), getFavorites(), getEvents(),
        getLatestAnalysis().catch((error: unknown) => {
          if (error instanceof WorkspaceApiError && error.status === 404) return null;
          throw error;
        }),
      ]);
      const labs = await Promise.all(favorites.map((id) => getLab(id).catch(() => null)));
      setData(toWorkspace(profile, favorites, events.length, analysis));
      setSavedLabs(labs.filter((lab): lab is Lab => lab !== null));
      setLoadState("ready");
    } catch (error) {
      setLoadState(error instanceof WorkspaceApiError && error.status === 401 ? "unauthorized" : "error");
    }
  }

  useEffect(() => { void Promise.resolve().then(loadWorkspace); }, []);

  async function saveProfile(submission: ProfileSubmission): Promise<void> {
    setSaving(true); setStatus("Saving your profile.");
    try {
      await saveBackendProfile({
        name: submission.displayName,
        affiliation: submission.preferredUniversity,
        status: submission.applicationTerm,
        program: submission.degreeProgram,
        interests: [...submission.researchInterests],
      });
      if (submission.cvFile !== null) await analyzeDocument(submission.cvFile);
      await loadWorkspace();
      setEditing(false); setStatus("Changes saved.");
    } catch {
      setStatus("Could not save. Check your login and file format.");
    } finally { setSaving(false); }
  }

  async function toggleTarget(labId: string, saved: boolean): Promise<void> {
    if (data === null) return;
    setSavingTargetId(labId);
    try {
      await (saved ? ky.put(`/api/backend/me/favorites/${labId}`) : ky.delete(`/api/backend/me/favorites/${labId}`));
      let nextLabs = savedLabs.filter((lab) => lab.id !== labId);
      if (saved) nextLabs = [...nextLabs, await getLab(labId)];
      setSavedLabs(nextLabs);
      setData({
        ...data,
        targetLabIds: saved ? [...data.targetLabIds.filter((id) => id !== labId), labId] : data.targetLabIds.filter((id) => id !== labId),
        summary: { ...data.summary, savedProfessors: saved ? data.summary.savedProfessors + 1 : Math.max(0, data.summary.savedProfessors - 1) },
      });
      setStatus(saved ? "Saved this professor." : "Removed this professor from saved items.");
    } catch { setStatus("Could not update saved professors."); }
    finally { setSavingTargetId(null); }
  }

  if (loadState === "loading" || data === null && loadState === "ready") {
    return <div className="profile-loading" role="status"><strong>Loading Profile</strong><span>Checking your saved profile and professors.</span></div>;
  }
  if (loadState === "unauthorized") {
    return <div className="profile-layout"><section className="profile-intro"><p className="kicker">MY RESEARCH PROFILE</p><h1>Log in to view your profile</h1><p>Your backend session has expired.</p><Link className="primary-button" href="/login">Log in</Link></section></div>;
  }
  if (loadState === "error" || data === null) {
    return <div className="profile-layout"><section className="profile-intro"><p className="kicker">MY RESEARCH PROFILE</p><h1>Profile unavailable</h1><p>Could not load profile data from the backend.</p><button className="secondary-button" onClick={() => void loadWorkspace()} type="button">Try again</button></section></div>;
  }
  if (data.profile !== null && !editing) {
    return <ProfileDashboard data={{ ...data, profile: data.profile }} onEdit={() => setEditing(true)} onToggleTarget={toggleTarget} savedLabs={savedLabs} savingTargetId={savingTargetId} status={status} />;
  }
  return (
    <div className="profile-layout">
      <section className="profile-intro" aria-labelledby="profile-title">
        <p className="kicker">MY RESEARCH PROFILE</p><h1 id="profile-title">Edit research profile</h1>
        <p>Update your backend profile, add a CV, or manage your saved application details.</p>
        <div className="privacy-note"><span aria-hidden="true">OK</span><div><strong>Your data is connected to your account</strong><p>Profile, CV analysis, favorites, and calendar data come from the backend.</p></div></div>
      </section>
      <ProfileEditor assets={data.cvAssets} initialProfile={data.profile} onCancel={() => setEditing(false)} onReset={null} onSave={saveProfile} saving={saving} status={status} />
    </div>
  );
}
