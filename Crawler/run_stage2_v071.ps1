param(
    [string]$DataDir = ".\data",
    [switch]$WithLabHomepages,
    [switch]$BrowserFallback
)

$ErrorActionPreference = "Stop"

python -c "import postech_stage2_enricher as m; print('Version:', m.ENRICHER_VERSION)"
python .\test_postech_stage2_enricher.py

python .\postech_stage2_enricher.py `
  --data-dir $DataDir `
  --clean-only

$arguments = @(
  ".\postech_stage2_enricher.py",
  "--data-dir", $DataDir,
  "--force",
  "--max-pages", "16",
  "--max-depth", "3"
)

if (-not $WithLabHomepages) {
  $arguments += "--skip-lab-homepages"
}
if ($BrowserFallback) {
  $arguments += "--browser-fallback"
}

python @arguments
