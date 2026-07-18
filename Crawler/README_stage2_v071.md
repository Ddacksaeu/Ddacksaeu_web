# POSTECH Stage 2 Enricher 0.7.1-data-audit

## Files

- `postech_stage2_enricher.py`
- `test_postech_stage2_enricher.py`
- `site_overrides_v071.example.json`
- `requirements_stage2_v071.txt`
- `run_stage2_v071.ps1`

## Changes

- Empty placeholder lab names are restored when the professor name exists.
- Missing professor names can be recovered conservatively from a personal/lab homepage.
- Recruitment-only and publication-announcement text is removed from `research_summary`.
- The same portrait assigned to different professors is removed.
- `enrichment_source_urls` is limited to identity-relevant provenance URLs, maximum 8.
- News, recruiting, alumni, and unrelated discovery URLs are removed from provenance.
- English homepage lab names are additionally stored in `lab_name_eng`.
- Version updated to `0.7.1-data-audit`.

## Setup

Rename input files:

```text
departments(8).csv      -> data/departments.csv
labs(8).csv             -> data/labs.csv
research_outputs(8).csv -> data/research_outputs.csv
```

Install:

```powershell
pip install -r .\requirements_stage2_v071.txt
Copy-Item .\site_overrides_v071.example.json .\data\site_overrides.json
```

Do not overwrite an existing `site_overrides.json`; merge its entries instead.

## Verify

```powershell
python -c "import postech_stage2_enricher as m; print(m.ENRICHER_VERSION)"
python .\test_postech_stage2_enricher.py
```

Expected version:

```text
0.7.1-data-audit
```

## Run

Preview cleaning:

```powershell
python .\postech_stage2_enricher.py --data-dir .\data --clean-only --dry-run
```

Apply cleaning:

```powershell
python .\postech_stage2_enricher.py --data-dir .\data --clean-only
```

Re-crawl faculty pages:

```powershell
python .\postech_stage2_enricher.py `
  --data-dir .\data `
  --force `
  --max-pages 16 `
  --max-depth 3 `
  --skip-lab-homepages
```

Then verify lab homepages:

```powershell
python .\postech_stage2_enricher.py `
  --data-dir .\data `
  --force `
  --max-pages 16 `
  --max-depth 3
```
