"use client";

import ky, { HTTPError } from "ky";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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

type Recommendation = Readonly<{
  lab_id: string;
  total_score: number;
  matched_keywords: readonly string[];
  missing_keywords: readonly string[];
  short_reason: string;
  recommended_action: string;
  warnings: readonly string[];
  evidence: readonly { type: string; text: string }[];
  score_breakdown: Record<string, { score: number; max_score: number; available: boolean }>;
  data_origin: string;
}>;

function RecommendationResults({ items }: Readonly<{ items: readonly Recommendation[] }>) {
  return <section aria-label="CV-based professor recommendations" className="profile-recommendation">
    <div className="profile-recommendation-heading"><div><p>EXPLAINABLE MATCH</p><h2>Recommended for you</h2><span>Scores use local TF-IDF and structured CV data. They are not admission probabilities.</span></div></div>
    <ol className="profile-recommendation-list">{items.map((item) => <li key={item.lab_id}>
      <div className="profile-recommendation-card-topline"><span>Match {item.total_score.toFixed(1)}</span><small>{item.data_origin === "fixture" ? "Fixture data" : "Lab data"}</small></div>
      <p>{item.short_reason}</p>
      <div className="profile-recommendation-match"><strong>Matched</strong><span>{item.matched_keywords.length ? item.matched_keywords.join(" · ") : "No structured keyword match"}</span></div>
      {item.missing_keywords.length > 0 && <p><small>Missing: {item.missing_keywords.join(" · ")}</small></p>}
      <details><summary>Score breakdown</summary><ul>{Object.entries(item.score_breakdown).map(([name, part]) => <li key={name}>{name.replaceAll("_", " ")}: {part.available ? `${part.score} / ${part.max_score}` : "Unavailable"}</li>)}</ul></details>
      {item.evidence.length > 0 && <ul>{item.evidence.map((evidence, index) => <li key={`${evidence.type}-${index}`}>{evidence.text}</li>)}</ul>}
      {item.warnings.length > 0 && <p role="status">{item.warnings.join(" ")}</p>}
      <p>{item.recommended_action}</p>
      <Link href={`/professors/${item.lab_id}`}>View details</Link>
    </li>)}</ol>
  </section>;
}

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
  const [profileReady, setProfileReady] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState("");
  const [recommendations, setRecommendations] = useState<readonly Recommendation[] | null>(null);
  const [recommendationStatus, setRecommendationStatus] = useState<"idle" | "loading" | "error" | "missing-cv">("idle");
  const institutions = useMemo(() => [...new Set(labs.map((lab) => lab.institution))].sort((a, b) => a.localeCompare(b, "en")), [labs]);
  const topics = useMemo(() => [...new Set(labs.flatMap((lab) => lab.topics))].sort((a, b) => a.localeCompare(b, "en")), [labs]);
  const results = useMemo(() => filterCatalog(labs, filters), [filters, labs]);
  const savedIdSet = useMemo(() => new Set(savedIds), [savedIds]);
  const hasFilters = Object.values(filters).some((value) => value.length > 0);

  useEffect(() => {
    void ky.get("/api/backend/me/favorites").json<{ labIds: string[] }>().then((value) => {
      setSavedIds(value.labIds);
      setProfileReady(true);
    }).catch(() => { setSaveStatus("Could not load saved professors."); setProfileReady(true); });
  }, []);

  async function toggleSaved(labId: string, saved: boolean): Promise<void> {
    setSavingId(labId);
    try {
      await (saved ? ky.put(`/api/backend/me/favorites/${labId}`) : ky.delete(`/api/backend/me/favorites/${labId}`));
      setSavedIds((current) => saved ? [...current.filter((id) => id !== labId), labId] : current.filter((id) => id !== labId));
      setSaveStatus(saved ? "Saved this professor." : "Removed this professor from saved items.");
    } catch (error) {
      if (error instanceof HTTPError && error.response.status === 401) window.location.assign("/login");
      else setSaveStatus("Could not update saved professors.");
    } finally {
      setSavingId(null);
    }
  }

  async function loadRecommendations(): Promise<void> {
    setRecommendationStatus("loading");
    try {
      const result = await ky.get("/api/backend/recommendations").json<{ items: Recommendation[] }>();
      setRecommendations(result.items);
      setRecommendationStatus("idle");
    } catch (error) {
      setRecommendationStatus(error instanceof HTTPError && error.response.status === 409 ? "missing-cv" : "error");
    }
  }

  const heading = mode === "search" ? "Find professors aligned with your research" : "All professors";
  const description = mode === "search" ? "Combine university, research topic, and keywords to narrow your candidates." : "Compare all demo professor candidates and review their official institutional sources.";

  return (
    <main className="catalog-page">
      <header className="catalog-hero"><p className="catalog-kicker">PROFESSOR DISCOVERY</p><h1>{heading}</h1><p>{description}</p></header>
      <div className="catalog-workspace">
        <section className="catalog-result-toolbar" aria-label="CV recommendations"><p><strong>Match with my CV</strong> to see an explainable, local score.</p><button className="catalog-clear-button" disabled={recommendationStatus === "loading"} onClick={() => void loadRecommendations()} type="button">{recommendationStatus === "loading" ? "Loading recommendations" : "Match with my CV"}</button></section>
        {recommendationStatus === "missing-cv" && <section className="catalog-empty"><h2>Analyze your CV first</h2><p>Recommendations require your latest local CV analysis.</p><Link href="/cv">Go to CV analysis</Link></section>}
        {recommendationStatus === "error" && <section className="catalog-empty" role="alert"><h2>Could not load recommendations</h2><button onClick={() => void loadRecommendations()} type="button">Try again</button></section>}
        {recommendations !== null && <RecommendationResults items={recommendations} />}
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
