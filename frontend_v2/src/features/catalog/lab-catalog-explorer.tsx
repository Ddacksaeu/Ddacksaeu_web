"use client";

import ky from "ky";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { profileWorkspaceSchema } from "../profile/profile-client-contract";
import type { LabCatalogEntry } from "../../server/catalog/schema";
import { filterCatalog, type CatalogFilters } from "./catalog-filter";

const EMPTY_FILTERS: CatalogFilters = { institution: "", topic: "", query: "" };
const CATALOG_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeZone: "Asia/Seoul",
});

type LabCatalogExplorerProperties = Readonly<{
  labs: readonly LabCatalogEntry[];
  mode: "search" | "list";
  initialQuery?: string;
}>;

type LabCardProperties = Readonly<{
  lab: LabCatalogEntry;
  saved: boolean;
  saving: boolean;
  ready: boolean;
  onToggleSaved: (labId: string, saved: boolean) => Promise<void>;
}>;

function LabCard({ lab, saved, saving, ready, onToggleSaved }: LabCardProperties) {
  const checkedDate = CATALOG_DATE_FORMATTER.format(new Date(lab.verifiedAt));

  return (
    <article className="catalog-card">
      <div className="catalog-card-heading">
        <div>
          <div className="catalog-card-meta"><span>{lab.institution}</span><span className="demo-badge">Demo data</span></div>
          <h2>{lab.labName.replace(" (Demo)", "\u00a0(Demo)")}</h2><p>{lab.professor}</p>
        </div>
        <div className="catalog-card-actions">
          <Link className="catalog-detail-link" href={"/professors/" + lab.id}>View details</Link>
          <button className={"catalog-save-button" + (saved ? " is-saved" : "")} disabled={saving || !ready} onClick={() => void onToggleSaved(lab.id, !saved)} type="button">{!ready ? "Checking saved state" : saving ? "Saving" : saved ? "Saved" : "Save professor"}</button>
          <a className="catalog-lab-link" href={lab.labUrl} rel="noreferrer" target="_blank">Registered lab link<span className="catalog-visually-hidden">, new tab</span></a>
        </div>
      </div>
      <ul aria-label={lab.labName + " research keywords"} className="catalog-topic-list">{lab.topics.map((topic) => <li key={topic}>{topic}</li>)}</ul>
      <div className="catalog-source-row">
        <span>This is fictional professor data for product testing.</span>
        <div className="catalog-source-action"><a href={lab.officialSourceUrl} rel="noreferrer" target="_blank">Official institution website<span className="catalog-visually-hidden">, new tab</span></a><span className="catalog-source-date">Checked {checkedDate}</span></div>
      </div>
    </article>
  );
}

export function LabCatalogExplorer({ labs, mode, initialQuery = "" }: LabCatalogExplorerProperties) {
  const [filters, setFilters] = useState<CatalogFilters>({ ...EMPTY_FILTERS, query: initialQuery });
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [savedIds, setSavedIds] = useState<readonly string[]>([]);
  const profileExists = useRef(false);
  const [profileReady, setProfileReady] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState("");
  const institutions = useMemo(() => [...new Set(labs.map((lab) => lab.institution))].sort((a, b) => a.localeCompare(b, "en")), [labs]);
  const topics = useMemo(() => [...new Set(labs.flatMap((lab) => lab.topics))].sort((a, b) => a.localeCompare(b, "en")), [labs]);
  const results = useMemo(() => filterCatalog(labs, filters), [filters, labs]);
  const savedIdSet = useMemo(() => new Set(savedIds), [savedIds]);
  const hasFilters = Object.values(filters).some((value) => value.length > 0);

  useEffect(() => {
    void ky.get("/api/profile").json().then((value) => {
      const workspace = profileWorkspaceSchema.parse(value);
      profileExists.current = workspace.profile !== null;
      setSavedIds(workspace.targetLabIds);
      setProfileReady(true);
    }).catch(() => { setSaveStatus("Could not load saved professors."); setProfileReady(true); });
  }, []);

  async function toggleSaved(labId: string, saved: boolean): Promise<void> {
    if (!profileExists.current) {
      window.location.assign("/profile");
      return;
    }
    setSavingId(labId);
    try {
      await ky.patch("/api/profile", { json: { labId, saved } });
      setSavedIds((current) => saved ? [...current.filter((id) => id !== labId), labId] : current.filter((id) => id !== labId));
      setSaveStatus(saved ? "Saved this professor." : "Removed this professor from saved items.");
    } catch {
      setSaveStatus("Could not update saved professors.");
    } finally {
      setSavingId(null);
    }
  }

  const heading = mode === "search" ? "Find professors aligned with your research" : "All professors";
  const description = mode === "search" ? "Combine university, research topic, and keywords to narrow your candidates." : "Compare all demo professor candidates and review their official institutional sources.";

  return (
    <main className="catalog-page">
      <header className="catalog-hero"><p className="catalog-kicker">PROFESSOR DISCOVERY</p><h1>{heading}</h1><p>{description}</p></header>
      <div className="catalog-workspace">
        <button aria-controls="professor-filter-panel" aria-expanded={filtersOpen} aria-label={filtersOpen ? "Close professor search filters" : "Open professor search filters"} className="catalog-filter-trigger" onClick={() => setFiltersOpen((current) => !current)} type="button">
          <span>Search filters</span><strong>{filtersOpen ? "Close" : hasFilters ? "Applied · Open" : "Open"}</strong>
        </button>
        <section aria-label="Professor search filters" className={"catalog-filter-panel" + (filtersOpen ? " is-open" : "")} id="professor-filter-panel">
          <label className="catalog-search-field"><span>Search professors, labs, or keywords</span><input onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value }))} placeholder="e.g. Computer Vision, Databases" type="search" value={filters.query} /></label>
          <label className="catalog-select-field"><span>University</span><select onChange={(event) => setFilters((current) => ({ ...current, institution: event.target.value }))} value={filters.institution}><option value="">All universities</option>{institutions.map((institution) => <option key={institution}>{institution}</option>)}</select></label>
          <label className="catalog-select-field"><span>Research topic</span><select onChange={(event) => setFilters((current) => ({ ...current, topic: event.target.value }))} value={filters.topic}><option value="">All topics</option>{topics.map((topic) => <option key={topic}>{topic}</option>)}</select></label>
          <button className="catalog-clear-button" disabled={!hasFilters} onClick={() => setFilters(EMPTY_FILTERS)} type="button">Reset filters</button>
        </section>
        <div className="catalog-results-area">
          <div className="catalog-result-toolbar"><p aria-live="polite"><strong>{results.length}</strong> professors found</p><span>20 fictional profiles · Not real recruitment information</span></div>
          <p className="catalog-save-status" aria-live="polite">{saveStatus}</p>
          {results.length > 0 ? <section aria-label="Professor search results" className="catalog-grid">{results.map((lab) => <LabCard key={lab.id} lab={lab} onToggleSaved={toggleSaved} ready={profileReady} saved={savedIdSet.has(lab.id)} saving={savingId === lab.id} />)}</section> : <section className="catalog-empty" role="status"><h2>No professors match these filters</h2><p>Shorten your query or reset the university and research topic filters.</p><button onClick={() => setFilters(EMPTY_FILTERS)} type="button">View all professors</button></section>}
        </div>
      </div>
    </main>
  );
}
