# POSTECH crawler known failures (2026-07-19)

Source: `Crawler/data/stage2_crawl_log.jsonl`, last authoritative attempt at
2026-07-19T13:17:12+09:00. It selected 29 departments and aborted its source-of-
truth commit after recording 26 successes (the configured threshold was 29).
The log does not emit a terminal per-department record for all three failures, so
the following are the evidence-backed unresolved targets rather than guesses.

| Target | Evidence | Classification | Import behavior |
| --- | --- | --- | --- |
| Biology (`DEPT_72FA8A502789`) | `departments.csv` has `enrichment_status=no_match`: no safe faculty-card/existing-professor match | data matching failure | Existing catalogue rows may import when structurally valid; no affiliation is fabricated. |
| Chemistry (`DEPT_8540E8D01A3B`) | Five candidate faculty URLs redirected to `http://html.dsso.kr/404.html` and were scope-rejected | URL redirect / external 404 | Fallback-derived source URLs remain subject to importer URL validation; crawler candidate URLs are not repaired here. |
| Synthetic Biology program (`DEPT_EFAF183ABB57`) | Five attempted faculty paths returned HTTP 404 before `/faculty` fallback matched records | stale URL / HTML route change | The fallback results are retained; failed candidate URLs are not inserted as lab sources. |

The latter two targets do have fallback match lines in the same log, which explains
why current `departments.csv` can show a later success state while the authoritative
attempt still reports only 26/29. The crawler should add terminal department status
records before the next crawl; this DB importer intentionally treats the CSV as
immutable input and records row-level validation failures in its batch report.
