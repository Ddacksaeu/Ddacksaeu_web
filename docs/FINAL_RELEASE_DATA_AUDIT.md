# Final release data audit (2026-07-19)

## Admissions

The repository has no human-reviewed official admission-date file. The real admission-event count therefore remains **0**; fixture rows are development-only and explicitly carry `origin=fixture`. `backend/data/admissions.example.json` is intentionally empty. `python -m scripts.import_admissions FILE --dry-run` accepts only human-reviewed JSON with a source URL, checked timestamp, timezone-aware start date, valid type, and university identity. Invalid rows are skipped with a reason; stable event IDs make re-imports upserts. ICS exports every event selected by the same optional `start_at`, `end_at`, university, department, and type filters as `GET /admissions`.

## POSTECH keywords

The importer derives lab keywords only from semicolon-delimited `labs.csv:keywords`. It does not promote paper terms into the normalized `keywords` table; paper metadata remains in `papers.keywords_json`. The current source has 158 non-empty keyword occurrences, 137 exact distinct terms, and 137 distinct normalized terms. Twenty-one occurrences repeat an existing normalized term. Thus the observed **137** is a normal deduplicated count, not a dropped-keyword regression. The earlier **491** cannot be reproduced from the current lab-keyword field and was a broader/raw reporting basis (for example paper/output terms), not the count inserted into `keywords`.

Of the 286 validated labs, 233 have no source keyword value. The recommendation service still includes `lab.field` in its keyword comparison and uses summary/paper text for separate fixed-weight components; it does not fabricate missing lab tags. Its `matched_keywords` is empty whenever the user's normalized CV terms do not overlap the lab's keyword-or-field terms. This must be measured against a particular CV population, so no misleading global percentage is recorded.

The current CSV has 290 structurally mapped rows; four duplicate professor/lab pairs are excluded, leaving 286 labs and 286 distinct professor IDs. A database showing 287 professors after that import contains one previously imported professor: the catalogue importer is an upsert and deliberately does not delete records absent from a later source snapshot. Use a new isolated DB for a snapshot-exact count.

## Playwright legacy suite

The existing visual-demo specs still assert the pre-BFF local-storage screens, arbitrary demo credentials, and demo routes. They are retained unchanged as legacy visual coverage and are not release API smoke. `release-smoke.spec.ts` is the short separate supported-flow suite; it requires an isolated, prepared backend DB rather than repeatedly starting servers per test.
