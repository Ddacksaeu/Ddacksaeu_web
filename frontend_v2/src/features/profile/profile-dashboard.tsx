import Link from "next/link";

import type { Lab } from "../workspace/api";
import { SavedContactDraft } from "../contact/saved-contact-draft";
import { CvAnalysisPanel } from "./cv-analysis-panel";
import type { ProfileWorkspaceData } from "./profile-client-contract";

type ProfileDashboardProperties = Readonly<{
  data: ProfileWorkspaceData & { readonly profile: NonNullable<ProfileWorkspaceData["profile"]> };
  savingTargetId: string | null;
  savedLabs: readonly Lab[];
  status: string;
  onEdit: () => void;
  onToggleTarget: (labId: string, saved: boolean) => Promise<void>;
}>;

const PROFILE_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeZone: "Asia/Seoul",
});

export function ProfileDashboard({
  data,
  savingTargetId,
  savedLabs,
  status,
  onEdit,
  onToggleTarget,
}: ProfileDashboardProperties) {
  const profile = data.profile;
  const savedDate = PROFILE_DATE_FORMATTER.format(new Date(profile.consentedAt));

  return (
    <div className="profile-dashboard">
      <header className="profile-dashboard-hero">
        <div>
          <p className="kicker">MY RESEARCH PROFILE</p>
          <h1>{profile.displayName}’s Profile</h1>
          <p>Review your research profile, saved professors, and CV, then <span className="keep-phrase">continue your next task.</span></p>
        </div>
        <button className="profile-edit-button" onClick={onEdit} type="button">Edit profile</button>
      </header>

      <section className="profile-summary-panel" aria-labelledby="profile-summary-title">
        <div className="profile-section-heading">
          <div><p>My profile</p><h2 id="profile-summary-title">Research preparation</h2></div>
          <span>Last saved {savedDate}</span>
        </div>
        <div className="profile-stat-grid">
          <div><strong>{profile.researchInterests.length}</strong><span>research keywords</span></div>
          <div><strong>{data.cvAssets.length}</strong><span>Saved CVs</span></div>
          <div><strong>{data.summary.savedProfessors}</strong><span>Saved professors</span></div>
          <div><strong>{data.summary.schedules}</strong><span>My schedule</span></div>
        </div>
        <div className="profile-keyword-row" aria-label="Saved research keywords">
          {profile.researchInterests.length > 0
            ? profile.researchInterests.map((keyword) => <span key={keyword}>{keyword}</span>)
            : <p>No research keywords yet. Edit your profile to add them.</p>}
        </div>
        <dl className="profile-preference-row" aria-label="Saved application preferences">
          <div><dt>Affiliation</dt><dd>{profile.preferredUniversity || "Not set"}</dd></div>
          <div><dt>Status</dt><dd>{profile.applicationTerm || "Not set"}</dd></div>
          <div><dt>Program</dt><dd>{profile.degreeProgram || "Not set"}</dd></div>
        </dl>
        <nav className="profile-quick-actions" aria-label="Profile shortcuts">
          <button onClick={onEdit} type="button">Manage CV and profile</button>
          <Link href="/professors">New professor search</Link>
          <Link href="/calendar">View application dates</Link>
        </nav>
      </section>

      <div className="profile-dashboard-grid">
        <section className="profile-saved-panel" aria-labelledby="saved-professors-title">
          <div className="profile-section-heading">
            <div><p>Saved list</p><h2 id="saved-professors-title">Saved professors</h2></div>
            <Link href="/professors">Find more professors</Link>
          </div>
          {savedLabs.length === 0 ? (
            <div className="profile-dashboard-empty"><strong>No saved professors</strong><p>Save professors from Professor search to compare them here.</p><Link href="/professors">Search professors</Link></div>
          ) : (
            <ul className="profile-saved-list">
              {savedLabs.map((lab) => (
                <li key={lab.id}>
                  <div><span>{lab.department}</span><h3>{lab.professorName}</h3><p>{lab.name}</p><small>{lab.keywords.join(" · ")}</small></div>
                  <div><Link href={"/professors/" + lab.id}>View details</Link><button disabled={savingTargetId === lab.id} onClick={() => void onToggleTarget(lab.id, false)} type="button">{savingTargetId === lab.id ? "Processing" : "Remove"}</button></div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="profile-cv-panel" aria-labelledby="saved-cv-title">
          <div className="profile-section-heading"><div><p>Application materials</p><h2 id="saved-cv-title">CV management</h2></div></div>
          {data.cvAssets.length === 0 ? <div className="profile-dashboard-empty"><strong>No saved CVs</strong><p>Add a PDF or TXT file in Edit profile.</p></div> : (
            <ul className="profile-cv-list">{data.cvAssets.map((asset) => <li key={asset.id}><span aria-hidden="true">CV</span><div><strong>{asset.fileName}</strong><small>{Math.max(1, Math.ceil(asset.byteLength / 1024))} KB · Saved</small></div></li>)}</ul>
          )}
          <button className="profile-inline-button" onClick={onEdit} type="button">Add or replace CV</button>
        </aside>
      </div>
      <CvAnalysisPanel />
      <SavedContactDraft />
      <p className="profile-dashboard-status" aria-live="polite">{status}</p>
    </div>
  );
}
