"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { LabCatalogEntry } from "../../server/catalog/schema";
import { filterCatalog, type CatalogFilters } from "../catalog/catalog-filter";
import styles from "./professor-explorer.module.css";

const EMPTY_FILTERS: CatalogFilters = { institution: "", topic: "", query: "" };

type ProfessorExplorerProperties = Readonly<{ professors: readonly LabCatalogEntry[] }>;

export function ProfessorExplorer({ professors }: ProfessorExplorerProperties) {
  const [filters, setFilters] = useState<CatalogFilters>(EMPTY_FILTERS);
  const [saved, setSaved] = useState<readonly string[]>([]);
  const institutions = useMemo(() => [...new Set(professors.map((item) => item.institution))], [professors]);
  const topics = useMemo(() => [...new Set(professors.flatMap((item) => item.topics))], [professors]);
  const results = useMemo(() => filterCatalog(professors, filters), [filters, professors]);
  const savedIdSet = useMemo(() => new Set(saved), [saved]);

  function toggleSaved(id: string): void {
    setSaved((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  return (
    <main className={styles["page"]}>
      <header className={styles["hero"]}>
        <div><p className={styles["eyebrow"]}>PROFESSOR DISCOVERY</p><h1>Find professors aligned with your research</h1><p>Combine university, research area, and keywords to compare candidates and recent work.</p></div>
        <span className={styles["demo"]}>20 demo professor profiles</span>
      </header>
      <div className={styles["searchLayout"]}>
        <section className={styles["filters"]} aria-label="Professor search filters">
          <label className={styles["field"]}>Search professors, labs, or keywords<input type="search" value={filters.query} placeholder="e.g. Computer Vision, HCI" onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value }))} /></label>
          <label className={styles["field"]}>University<select value={filters.institution} onChange={(event) => setFilters((current) => ({ ...current, institution: event.target.value }))}><option value="">All universities</option>{institutions.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className={styles["field"]}>Research area<select value={filters.topic} onChange={(event) => setFilters((current) => ({ ...current, topic: event.target.value }))}><option value="">All research areas</option>{topics.map((item) => <option key={item}>{item}</option>)}</select></label>
          <button className={styles["reset"]} type="button" onClick={() => setFilters(EMPTY_FILTERS)}>Reset filters</button>
        </section>
        <section aria-label="Professor search results">
          <div className={styles["resultsHeader"]}><p aria-live="polite"><strong>{results.length}</strong> professors found</p><span>Demo data shown before crawler integration</span></div>
          {results.length === 0 ? <div className={styles["empty"]}><h2>No professors match these filters</h2><p>Shorten your keywords or reset the search filters.</p></div> : (
            <ol className={styles["list"]}>{results.map((professor) => {
              const isSaved = savedIdSet.has(professor.id);
              return <li className={styles["card"]} key={professor.id}><div><div className={styles["meta"]}><span>{professor.institution}</span><span>Recruitment status unverified</span></div><h2>{professor.professor}</h2><p>{professor.labName}</p><ul className={styles["topics"]}>{professor.topics.map((topic) => <li key={topic}>{topic}</li>)}</ul></div><div className={styles["actions"]}><Link className={styles["detail"]} href={"/professors/" + professor.id}>View professor details</Link><button className={styles["save"] + (isSaved ? " " + styles["saveActive"] : "")} type="button" onClick={() => toggleSaved(professor.id)}>{isSaved ? "Saved" : "Save professor"}</button></div></li>;
            })}</ol>
          )}
        </section>
      </div>
    </main>
  );
}
