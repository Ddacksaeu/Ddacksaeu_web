"use client";

import ky, { HTTPError } from "ky";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { LabSummary } from "../../server/backend/labs";
import { ProfessorSaveIcon } from "../professors/professor-save-icon";
import { getRecommendations, type Recommendation } from "../recommendations/recommendations-api";
import { RecommendationResults } from "../recommendations/recommendation-results";

type Props = Readonly<{ initialLabs: readonly LabSummary[]; initialTotal: number; initialQuery?: string; initialError?: boolean }>;
const formatter = new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeZone: "Asia/Seoul" });
const RESULTS_PAGE_SIZE = 12;

async function apiLabs(query: string): Promise<{ items: LabSummary[]; total: number }> {
  const params = new URLSearchParams({ page: "1", page_size: "100" });
  if (query.trim()) params.set("q", query.trim());
  return ky.get(`/api/backend/labs?${params}`).json();
}

function LabCard({ lab, saved, saving, onToggle }: Readonly<{
  lab: LabSummary;
  saved: boolean;
  saving: boolean;
  onToggle: (id: string, next: boolean) => Promise<void>;
}>) {
  const saveLabel = saving ? (saved ? "Removing saved lab" : "Saving lab") : saved ? "Remove saved lab" : "Save lab";
  return (
    <article className="catalog-card">
      <div className="catalog-card-heading">
        <div>
          <div className="catalog-card-meta"><span>{lab.university}</span><span>{lab.department}</span></div>
          <h2>{lab.name}</h2><p>{lab.professorName} - {lab.field}</p>
        </div>
        <div className="catalog-card-actions">
          <Link className="catalog-detail-link" href={`/professors/${lab.id}`}>View details</Link>
          {lab.homepageUrl && <a className="catalog-lab-link" href={lab.homepageUrl} rel="noreferrer" target="_blank">Lab website</a>}
          <button aria-busy={saving} aria-label={saveLabel} aria-pressed={saved} className={"catalog-save-button" + (saved ? " is-saved" : "")} disabled={saving} onClick={() => void onToggle(lab.id, !saved)} title={saveLabel} type="button"><ProfessorSaveIcon saved={saved} /></button>
        </div>
      </div>
      {lab.summary && <p>{lab.summary}</p>}
      <ul aria-label={`${lab.name} research keywords`} className="catalog-topic-list">{lab.keywords.map((keyword) => <li key={keyword}>{keyword}</li>)}</ul>
      <div className="catalog-source-row"><span>POSTECH catalogue data</span><span className="catalog-source-date">Updated {formatter.format(new Date(lab.updatedAt))}</span></div>
    </article>
  );
}

export function LabCatalogExplorer({ initialLabs, initialTotal, initialQuery = "", initialError = false }: Props) {
  const [query, setQuery] = useState(initialQuery);
  const [university, setUniversity] = useState("");
  const [topic, setTopic] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const searchTimer = useRef<number | null>(null);
  const [labs, setLabs] = useState(initialLabs);
  const [total, setTotal] = useState(initialTotal);
  const [status, setStatus] = useState<"idle" | "loading" | "error">(initialError ? "error" : "idle");
  const [savedIds, setSavedIds] = useState<readonly string[]>([]);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState("");
  const [recommendations, setRecommendations] = useState<readonly Recommendation[] | null>(null);
  const [recommendationStatus, setRecommendationStatus] = useState<"idle" | "loading" | "error" | "missing-cv" | "unauthorized">("idle");
  const [visibleCount, setVisibleCount] = useState(RESULTS_PAGE_SIZE);

  const savedIdSet = useMemo(() => new Set(savedIds), [savedIds]);
  const universities = useMemo(() => [...new Set(labs.map((lab) => lab.university))].sort(), [labs]);
  const topics = useMemo(() => [...new Set(labs.flatMap((lab) => lab.keywords))].sort(), [labs]);
  const results = useMemo(() => labs.filter((lab) =>
    (!university || lab.university === university)
    && (!topic || lab.keywords.includes(topic))
  ), [labs, topic, university]);
  const visibleResults = results.slice(0, visibleCount);
  const hasFilters = Boolean(query || university || topic);

  const loadFavorites = useCallback(async () => {
    try {
      const result = await ky.get("/api/backend/me/favorites").json<{ labIds: string[] }>();
      setSavedIds(result.labIds);
    } catch (error) {
      setSaveStatus(error instanceof HTTPError && error.response.status === 401 ? "Log in to manage saved labs." : "Could not load saved labs.");
    }
  }, []);

  useEffect(() => { void Promise.resolve().then(loadFavorites); }, [loadFavorites]);
  useEffect(() => () => { if (searchTimer.current !== null) window.clearTimeout(searchTimer.current); }, []);

  function search(next: string): void {
    setQuery(next);
    setVisibleCount(RESULTS_PAGE_SIZE);
    if (searchTimer.current !== null) window.clearTimeout(searchTimer.current);
    searchTimer.current = window.setTimeout(() => {
      setStatus("loading");
      void apiLabs(next).then((result) => {
        setLabs(result.items); setTotal(result.total); setStatus("idle");
      }).catch(() => setStatus("error"));
    }, 250);
  }

  async function toggle(id: string, next: boolean): Promise<void> {
    setSavingId(id);
    try {
      await (next ? ky.put(`/api/backend/me/favorites/${id}`) : ky.delete(`/api/backend/me/favorites/${id}`));
      setSavedIds((current) => next ? [...new Set([...current, id])] : current.filter((item) => item !== id));
      setSaveStatus(next ? "Saved lab." : "Removed saved lab.");
    } catch (error) {
      if (error instanceof HTTPError && error.response.status === 401) window.location.assign("/login");
      else setSaveStatus("Could not update saved labs. Your previous state was kept.");
    } finally { setSavingId(null); }
  }

  async function loadRecommendations(): Promise<void> {
    setRecommendationStatus("loading");
    try {
      setRecommendations(await getRecommendations());
      setRecommendationStatus("idle");
    } catch (error) {
      setRecommendationStatus(error instanceof HTTPError && error.response.status === 409
        ? "missing-cv"
        : error instanceof HTTPError && error.response.status === 401 ? "unauthorized" : "error");
    }
  }

  function resetFilters(): void {
    search(""); setUniversity(""); setTopic(""); setVisibleCount(RESULTS_PAGE_SIZE);
  }

  const resultCount = university || topic ? results.length : total;

  return (
    <main className="catalog-page">
      <header className="catalog-hero">
        <p className="catalog-kicker">PROFESSOR DISCOVERY</p>
        <h1>Find professors aligned with your research</h1>
        <p>Combine research topics and keywords to narrow POSTECH professor candidates.</p>
      </header>
      <div className="catalog-workspace">
        <button aria-controls="professor-filter-panel" aria-expanded={filtersOpen} aria-label={filtersOpen ? "Close professor search filters" : "Open professor search filters"} className="catalog-filter-trigger" onClick={() => setFiltersOpen((current) => !current)} type="button">
          <span>Search filters</span><strong>{filtersOpen ? "Close" : hasFilters ? "Applied - Open" : "Open"}</strong>
        </button>
        <section aria-label="Professor search filters" className={"catalog-filter-panel" + (filtersOpen ? " is-open" : "")} id="professor-filter-panel">
          <label className="catalog-search-field"><span>Search professors, labs, or keywords</span><input onChange={(event) => search(event.target.value)} placeholder="e.g. vision, robotics, AI" type="search" value={query} /></label>
          <label className="catalog-select-field"><span>University</span><select onChange={(event) => { setUniversity(event.target.value); setVisibleCount(RESULTS_PAGE_SIZE); }} value={university}><option value="">All universities</option>{universities.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="catalog-select-field"><span>Research topic</span><select onChange={(event) => { setTopic(event.target.value); setVisibleCount(RESULTS_PAGE_SIZE); }} value={topic}><option value="">All topics</option>{topics.map((item) => <option key={item}>{item}</option>)}</select></label>
          <button className="catalog-clear-button" disabled={recommendationStatus === "loading"} onClick={() => void loadRecommendations()} type="button">{recommendationStatus === "loading" ? "Matching CV..." : "Match with my CV"}</button>
          <button className="catalog-clear-button" disabled={!hasFilters} onClick={resetFilters} type="button">Reset filters</button>
        </section>

        <div className="catalog-results-area">
          {recommendationStatus === "missing-cv" && <section className="catalog-empty"><h2>Analyze your CV first</h2><Link href="/cv">Go to CV analysis</Link></section>}
          {recommendationStatus === "unauthorized" && <section className="catalog-empty"><h2>Your session has expired</h2><Link href="/login">Log in</Link></section>}
          {recommendationStatus === "error" && <section className="catalog-empty" role="alert"><h2>Could not load recommendations</h2><button onClick={() => void loadRecommendations()} type="button">Try again</button></section>}
          {recommendations && <RecommendationResults items={recommendations} />}
          <div className="catalog-result-toolbar"><p aria-live="polite"><strong>{status === "loading" ? "Loading" : resultCount}</strong> {status === "loading" ? "professors..." : "professors found"}</p><span>Verify details with official sources</span></div>
          <p className="catalog-save-status" aria-live="polite">{saveStatus}</p>
          {status === "error" ? (
            <section className="catalog-empty" role="alert"><h2>Could not load professors</h2><button onClick={() => search(`${query} `)} type="button">Try again</button></section>
          ) : results.length ? (
            <><section aria-label="Professor search results" className="catalog-grid">{visibleResults.map((lab) => <LabCard key={lab.id} lab={lab} saved={savedIdSet.has(lab.id)} saving={savingId === lab.id} onToggle={toggle} />)}</section>{visibleResults.length < results.length && <button className="catalog-load-more" onClick={() => setVisibleCount((count) => count + RESULTS_PAGE_SIZE)} type="button">Show more professors</button>}</>
          ) : status === "idle" ? (
            <section className="catalog-empty"><h2>No professors match these filters</h2><p>Shorten your query or reset the topic filter.</p><button onClick={resetFilters} type="button">View all professors</button></section>
          ) : null}
        </div>
      </div>
    </main>
  );
}
